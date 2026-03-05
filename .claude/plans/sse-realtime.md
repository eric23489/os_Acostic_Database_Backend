# Plan: SSE 即時資料推送功能

## Context

目前所有 API 為純 REST，前端無法感知資料變更（其他使用者新增/修改/刪除）。
本計畫在現有架構上新增 SSE 端點，讓前端在資料變更時即時收到通知，以刷新 TanStack Query 快取。

**架構確認：**
- Redis 已部署（Celery broker），可直接做 pub/sub
- Service 層為 sync（無 async/await），本 PR 維持 sync 不遷移
- `get_current_user` 依賴 `Authorization: Bearer` header，SSE 須另行處理 auth
- `create_project`、`update_project`、`restore_project`、`hard_delete_project` 目前無 `changed_by` 參數，需補充
- `delete_project(project_id, user_id)` 已有 `user_id`

**Async 策略：SSE 基礎設施 async-first，現有 service 層保持 sync**
- `event_bus.py` 全面使用 `redis.asyncio`
- `async def publish_event()` 為主要 API（供未來 async service 使用）
- `def publish_event_sync()` 為 sync 橋接（供現有 sync service 層使用）
- `async def subscribe_events()` 供 SSE endpoint 使用
- 未來 service 層遷移 async 時，只需將呼叫從 `publish_event_sync` 換成 `await publish_event`

**代碼探索確認的設計決策：**
- Auth：重用 `app/core/security.py:decode_access_token(token)` + 手動查 `UserInfo`，不依賴 `OAuth2PasswordBearer`
- CORS：前後端同源，不需要 `CORSMiddleware`
- SSE 錯誤處理：靜默斷線（generator 捕捉例外後結束，前端 EventSource 自動重連）
- `changed_by` 範圍：僅 `create_*`、`update_*`、`delete_*`；`restore_*` 和 `hard_delete_*` 不加 changed_by 也不推 event
- `main.py` 無 lifespan：需新增 lifespan context manager 初始化 Redis 連線

## 架構設計

### 系統層次圖

```
┌──────────────────────────────────────────────────────────────┐
│                         瀏覽器                                │
│  ┌─────────────────┐    ┌─────────────────────────────────┐  │
│  │   EventSource   │    │       TanStack Query            │  │
│  │  /events/stream │    │  queryClient.invalidateQueries  │  │
│  └────────┬────────┘    └───────────────┬─────────────────┘  │
│           │ SSE event                   │ refetch             │
└───────────┼─────────────────────────────┼────────────────────┘
            │ text/event-stream     REST API 呼叫
            ▼                             ▼
┌──────────────────────────────────────────────────────────────┐
│                          FastAPI                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  api_events.py                                         │  │
│  │  _verify_token_and_get_user() │ _generate_sse_stream() │  │
│  │  (auth phase, raises AppEx)   │ (stream phase, silent) │  │
│  └────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Services (sync)              event_bus.py             │  │
│  │  *_service.create/update/delete → publish_event_sync() │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬───────────────────────────────┘
                               │ PUBLISH / SUBSCRIBE
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                Redis  channel: "db_events"                    │
│   publish_event_sync (redis.Redis) ←→ subscribe_events       │
│                                         (redis.asyncio)      │
└──────────────────────────────────────────────────────────────┘
```

### 兩階段錯誤處理

```
sse_stream() 被呼叫
       │
       ▼
┌──────────────────────┐
│     AUTH PHASE        │  StreamingResponse 回傳前
│  decode_access_token  │  例外 → AppException handler
│  query UserInfo       │  → JSON 401/400 回應
│  db.close()           │
└──────────┬───────────┘
           │ 成功
           ▼
┌──────────────────────┐
│  StreamingResponse   │  HTTP 200 已送出
│  text/event-stream   │  exception handler 不再介入
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│    STREAM PHASE       │  generator 執行中
│  except Exception:   │  例外 → 只 log
│    logger.warning()  │  靜默結束 → 前端自動重連
└──────────────────────┘
```

### 權限過濾

```
ADMIN_ONLY_RESOURCES = {ResourceType.USER}

event 進入 → resource in ADMIN_ONLY? → Yes → user.role==ADMIN? → Yes → 推送
                                      ↓ No                    ↓ No
                                    推送                      skip
```

### 關鍵設計取捨

| 決策 | 選擇 | 理由 |
|------|------|------|
| Event store | Redis Pub/Sub（非 Stream） | 不需回放，Pub/Sub 更簡單 |
| Publish | sync bridge（非 async bridge） | 避免 threadpool 複雜性 |
| Auth | query param JWT | EventSource 不支援自訂 header |
| 連線錯誤 | 靜默斷線 | stream phase 無法被 handler 捕捉 |
| DB session | 立即關閉 | 避免 session 佔用整個 SSE 連線週期 |
| Heartbeat | asyncio.wait_for timeout | 不需額外 task 管理 |

## 新分支

從 `main` 建立 `feature/sse-realtime`：
```bash
git checkout main
git checkout -b feature/sse-realtime
```

## 實作方案：Redis Pub/Sub

| 比較點 | In-process Queue | Redis Pub/Sub |
|--------|-----------------|---------------|
| 多 worker 支援 | 否 | 是 |
| Celery worker 可 publish | 否 | 是 |
| 依賴新套件 | 否 | 否（redis-py 已有） |
| 複雜度 | 低 | 中 |

**選擇 Redis Pub/Sub**，理由：Celery worker 執行批次上傳時也需發 event，in-process queue 無法跨 process。

## Event 格式

```
SSE wire format:
id: <uuid>
data: {"resource": "project", "action": "created", "id": 42, "changed_by": 1, "timestamp": "..."}

: heartbeat   (每 15 秒，防代理斷線)
```

`action` 值：`created` | `updated` | `deleted`
`resource` 值：`project` | `point` | `deployment` | `audio` | `recorder` | `user`

## 權限過濾

| Role | 可見 resource |
|------|--------------|
| ADMIN | 全部（含 `user`） |
| 一般使用者 | 除 `user` 以外的所有 resource |

## Auth 策略

Browser `EventSource` 不支援自定義 header，JWT 透過 query param 傳遞：
```
GET /api/v1/events/stream?token=<jwt>
```

SSE endpoint 在連線建立時驗證 token、查 DB 取 user info、立即關閉 DB session（不使用 `Depends(get_db)`，避免 session 在長連線期間保持開啟）。

## 檔案清單

### 新增
| 檔案 | 說明 |
|------|------|
| `app/core/event_bus.py` | DataEvent、ResourceType/Action enum、sync publish、async subscribe、Redis 連線管理 |
| `app/api/v1/endpoints/api_events.py` | SSE endpoint（token auth、permission filter、heartbeat） |
| `tests/test_events.py` | SSE auth、permission filter、publish unit test |

### 修改
| 檔案 | 修改內容 |
|------|----------|
| `app/core/config.py` | 新增 `redis_url: str = "redis://redis:6379/0"` |
| `app/main.py` | 新增 lifespan context manager，初始化 Redis 連線 |
| `app/api/v1/api.py` | import `api_events`，加入 `include_router` |
| `app/services/project_service.py` | create/update/delete 後加 `publish_event_sync()`，補 `changed_by` 參數 |
| `app/api/v1/endpoints/api_projects.py` | 對應傳入 `current_user.id` |
| `app/services/point_service.py` | 同 project_service 模式（僅 create/update/delete） |
| `app/api/v1/endpoints/api_points.py` | 同上 |
| `app/services/deployment_service.py` | 同上 |
| `app/api/v1/endpoints/api_deployments.py` | 同上 |
| `app/services/audio_service.py` | 同上 |
| `app/api/v1/endpoints/api_audio.py` | 同上 |
| `app/services/recorder_service.py` | 同上 |
| `app/api/v1/endpoints/api_recorders.py` | 同上 |
| `app/services/user_service.py` | `create_user`、`update_user`、`delete_user` 加 publish |
| `app/api/v1/endpoints/api_users.py` | 同上 |
| `docker-compose.yml` | `fastapi-app` 的 `depends_on` 加入 `redis` |
| `requirements.txt` | 鎖定 `redis>=4.2.0`（確保 `redis.asyncio` 可用） |

## 核心程式碼結構

### `app/core/event_bus.py`

```python
REDIS_CHANNEL = "db_events"

class ResourceType(StrEnum):
    PROJECT = "project"
    POINT = "point"
    DEPLOYMENT = "deployment"
    AUDIO = "audio"
    RECORDER = "recorder"
    USER = "user"

class ResourceAction(StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"

@dataclass
class DataEvent:
    resource: ResourceType
    action: ResourceAction
    resource_id: int
    changed_by: int
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    event_id: str = field(default_factory=lambda: uuid4().hex)

# --- Async-first API（使用 redis.asyncio）---

async def publish_event(resource, action, resource_id, changed_by) -> None:
    """Primary API：供未來 async service/endpoint 呼叫。失敗只 log，不 raise。"""
    try:
        async with aioredis.from_url(settings.redis_url) as r:
            await r.publish(REDIS_CHANNEL, json.dumps(asdict(event)))
    except Exception:
        logger.warning("Failed to publish event", exc_info=True)

async def subscribe_events(last_event_id=None) -> AsyncGenerator[DataEvent, None]:
    """SSE endpoint 使用，per-connection 建立 pubsub，finally 確保 aclose()。"""
    r = await aioredis.from_url(settings.redis_url)
    pubsub = r.pubsub()
    await pubsub.subscribe(REDIS_CHANNEL)
    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            yield DataEvent(**json.loads(message["data"]))
    finally:
        await pubsub.unsubscribe(REDIS_CHANNEL)
        await r.aclose()

# --- Sync 橋接（供現有 sync service 層使用）---

def publish_event_sync(resource, action, resource_id, changed_by) -> None:
    """Sync bridge：使用 redis.Redis（blocking），供 sync service 層呼叫。
    未來 service 遷移 async 後，改用 await publish_event()。"""
    try:
        with redis.from_url(settings.redis_url) as r:
            r.publish(REDIS_CHANNEL, json.dumps(asdict(DataEvent(...))))
    except Exception:
        logger.warning("Failed to publish event (sync)", exc_info=True)
```

### `app/api/v1/endpoints/api_events.py`

**兩階段錯誤處理模型：**

| 階段 | 時機 | 錯誤類型 | 處理方式 |
|------|------|----------|----------|
| Auth（連線前） | `sse_stream()` 函數內、`StreamingResponse` 回傳前 | `AppException` | 直接 raise → 被 `app_exception_handler` 捕捉 → JSON 回應 |
| Stream（連線中） | `_generate_sse_stream()` generator 內 | Redis 連線中斷等 | 靜默結束 generator → 前端 EventSource 自動重連 |

**可重用的既有錯誤常數**（`app/core/exceptions.py`）：
- `AUTH_TOKEN_INVALID`（HTTP 401）：JWT 解碼失敗、payload 無 `sub`、找不到對應 user
- `AUTH_USER_INACTIVE`（HTTP 400）：user.is_active == False

```python
ADMIN_ONLY_RESOURCES = frozenset({ResourceType.USER})
HEARTBEAT_INTERVAL_SECONDS = 15

def _verify_token_and_get_user(token: str) -> UserInfo:
    """Auth phase：StreamingResponse 回傳前執行，raise 可被 exception handler 捕捉。"""
    try:
        payload = decode_access_token(token)  # from app.core.security
        email: str | None = payload.get("sub")
        if not email:
            raise AUTH_TOKEN_INVALID
    except JWTError:
        raise AUTH_TOKEN_INVALID

    db = SessionLocal()
    try:
        user = db.query(UserInfo).filter(UserInfo.email == email).first()
    finally:
        db.close()  # 立即關閉，不持有到 SSE 生命週期

    if not user:
        raise AUTH_TOKEN_INVALID
    if not user.is_active:
        raise AUTH_USER_INACTIVE
    return user

async def _generate_sse_stream(user_role, last_event_id) -> AsyncGenerator[str, None]:
    """Stream phase：例外只 log，靜默結束讓前端重連。"""
    yield "event: connected\ndata: {\"status\": \"ok\"}\n\n"
    try:
        async for event in subscribe_events(last_event_id):
            # asyncio.wait_for(timeout=15) → timeout 時 yield heartbeat
            if not _is_event_visible(event.resource, user_role):
                continue
            yield f"id: {event.event_id}\ndata: {payload}\n\n"
    except Exception:
        logger.warning("SSE stream error, closing connection", exc_info=True)

@router.get("/stream")
async def sse_stream(token: str = Query(...)) -> StreamingResponse:
    current_user = _verify_token_and_get_user(token)
    return StreamingResponse(
        _generate_sse_stream(current_user.role, last_event_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Nginx-Buffering": "no"},
    )
```

### Service 層修改模式

```python
# 修改後（呼叫 sync bridge）
from app.core.event_bus import publish_event_sync, ResourceType, ResourceAction

def create_project(self, project_in: ProjectCreate, changed_by: int) -> ProjectInfo:
    ...
    self.db.commit()
    publish_event_sync(ResourceType.PROJECT, ResourceAction.CREATED, db_obj.id, changed_by)
    return db_obj
```

Router 對應：
```python
return ProjectService(db).create_project(project, changed_by=current_user.id)
```

## 實作順序

| 步驟 | 檔案（≤3 個） | 重點 |
|------|-------------|------|
| 0 | 建立分支 `feature/sse-realtime` from `main` | |
| 1 | `event_bus.py`（新增）+ `config.py` | 核心 event 基礎設施 |
| 2 | `api_events.py`（新增）+ `api.py` | SSE endpoint，重用 `decode_access_token` |
| 3 | `main.py` + `docker-compose.yml` + `requirements.txt` | lifespan、redis depends_on、版本鎖定 |
| 4 | `project_service.py` + `api_projects.py` | create/update/delete 加 publish（模板） |
| 5 | `point_service.py` + `api_points.py` | |
| 6 | `deployment_service.py` + `api_deployments.py` | |
| 7 | `audio_service.py` + `api_audio.py` | |
| 8 | `recorder_service.py` + `user_service.py` + routers | |
| 9 | `tests/test_events.py`（新增） | |

## 前後端溝通流程

### 連線建立

```
前端                              後端 (SSE Endpoint)              Redis
  |                                      |                           |
  |-- GET /api/v1/events/stream          |                           |
  |   ?token=<jwt>  ─────────────────>  |                           |
  |                                      |-- decode JWT              |
  |                                      |-- query UserInfo          |
  |                                      |-- db.close()             |
  |                                      |-- SUBSCRIBE db_events --> |
  |<─ 200 text/event-stream ──────────── |                           |
  |<─ event: connected                   |                           |
  |   data: {"status":"ok"}              |                           |
```

### 資料變更事件流

```
REST API 呼叫              Service 層             Redis          SSE Stream        前端
  |                            |                    |                |               |
  |-- POST /api/v1/projects/-> |                    |                |               |
  |                            |-- db.commit()      |                |               |
  |                            |-- publish_event    |                |               |
  |                            |   _sync()          |                |               |
  |                            |-- PUBLISH ────────>|                |               |
  |<─ 201 ProjectResponse ──── |                    |-- message ────>|               |
  |                            |                    |                |-- data: {...} >|
  |                            |                    |                |               |-- invalidateQueries
  |                            |                    |                |               |-- refetch
```

### 前端 Query Invalidation 對應表

| resource | action | invalidate query key |
|----------|--------|----------------------|
| `project` | any | `['projects']`、`['projects', id]` |
| `point` | any | `['points']`、`['projects', projectId, 'points']` |
| `deployment` | any | `['deployments']`、`['points', pointId, 'deployments']` |
| `audio` | any | `['audios']`、`['deployments', deploymentId, 'audios']` |
| `user` | any（ADMIN 才收到） | `['users']`、`['users', id]` |

### Heartbeat 與重連

```
前端 EventSource                           後端
  |                                           |
  |           (15秒無 event)                  |
  |<─ : heartbeat ────────────────────────── |
  |                                           |
  |   (連線中斷，browser 內建自動重連)         |
  |-- 帶 Last-Event-ID header ──────────────> |  # 不做回放，直接重新訂閱
  |<─ event: connected ───────────────────── |
```

### 前端實作參考（TanStack Query）

```typescript
// hooks/useSSE.ts
function useSSE() {
  const queryClient = useQueryClient()
  const token = useAuthToken()

  useEffect(() => {
    const es = new EventSource(`/api/v1/events/stream?token=${token}`)

    es.onmessage = (e) => {
      const { resource, action, id } = JSON.parse(e.data)
      queryClient.invalidateQueries({ queryKey: [resource + 's'] })
      if (action !== 'created') {
        queryClient.invalidateQueries({ queryKey: [resource + 's', id] })
      }
    }

    return () => es.close()
  }, [token])
}
```

## 驗證方式

```bash
# 1. 啟動服務
docker-compose up -d --build

# 2. 取得 JWT
curl -X POST http://localhost:8000/api/v1/auth/login -d "username=...&password=..."

# 3. 開啟 SSE 連線（另一個終端）
curl -N "http://localhost:8000/api/v1/events/stream?token=<jwt>"

# 4. 在另一個終端建立 project，觀察 SSE 收到 event
curl -X POST http://localhost:8000/api/v1/projects/ -H "Authorization: Bearer <jwt>" -d '{...}'

# 5. 執行測試
pytest tests/test_events.py -v
```

## 注意事項

- `publish_event_sync` 在 `db.commit()` 之後呼叫，確保前端查詢時資料已寫入
- `Last-Event-ID` 保留參數介面但不實作回放（Redis pub/sub 無持久化）；斷線重連後前端主動 refetch
- Nginx 反代時需設定 `proxy_buffering off` 和 `proxy_read_timeout` 以支援 SSE 長連線
