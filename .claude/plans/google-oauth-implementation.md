# Google OAuth 帳號註冊功能 (完整版)

> **狀態：已完成** (2026-02-09)
>
> - 所有程式碼已實作
> - 資料庫遷移已執行
> - 28 個測試全部通過
> - 待設定：Google Cloud Console 憑證

---

## 功能範圍

1. **Google 登入/註冊** - 點擊即完成
2. **OAuth 帳號可設密碼** - 備用登入方式
3. **忘記密碼** - 密碼重設 + Google 帳號提示
4. **綁定 Google** - 已登入使用者可綁定 Google
5. **解除綁定** - 可解除 Google 綁定 (需先有密碼)

---

## 使用者情境

### 情境 1：新使用者 Google 登入
```
點擊 Google 登入 → Google 授權 → 自動建立帳號 → 登入成功
```
DB: 新增 user (password_hash = NULL)

### 情境 2：回訪使用者 Google 登入
```
點擊 Google 登入 → Google 授權 → 直接登入
```
DB: 更新 last_login_at

### 情境 3：同 email 已有本地帳號
```
點擊 Google 登入 → 自動綁定 Google → 登入成功
```
DB: 更新 oauth_provider, oauth_sub

### 情境 4：OAuth 帳號設定密碼
```
登入後 → 帳號設定 → 設定密碼 → 之後可用密碼登入
```
DB: 更新 password_hash

### 情境 5：忘記密碼 (純 Google 帳號)
```
點擊「忘記密碼」→ 輸入 email → 系統檢查
    ↓
顯示：「此帳號使用 Google 登入，請點擊 Google 登入」
```
DB: 無變更

### 情境 6：忘記密碼 (有密碼帳號)
```
點擊「忘記密碼」→ 輸入 email → 發送重設信
    ↓
點擊信件連結 → 設定新密碼 → 完成
```
DB: 更新 password_hash

### 情境 7：忘記密碼 (有密碼 + Google)
```
點擊「忘記密碼」→ 輸入 email
    ↓
顯示：「已發送重設信，或您可用 Google 登入」
```

### 情境 8：綁定 Google (已登入使用者)
```
登入後 → 帳號設定 → 點擊「綁定 Google」
    ↓
跳轉 Google 授權 → 授權成功
    ↓
綁定成功，之後可用 Google 登入
```
DB: 更新 oauth_provider, oauth_sub

### 情境 9：解除 Google 綁定
```
登入後 → 帳號設定 → 點擊「解除綁定」
    ↓
系統檢查：是否有設密碼？
    ↓
有密碼 → 解除成功
無密碼 → 「請先設定密碼」
```
DB: 清空 oauth_provider, oauth_sub

### 情境 10：錯誤處理
- 授權取消 → 返回登入頁
- Token 驗證失敗 → 401 錯誤
- 軟刪除帳號 → 「帳號已停用」
- 重設連結過期 → 「連結已過期，請重新申請」
- 解除綁定無密碼 → 「請先設定密碼」
- 綁定時 Google 已被其他帳號使用 → 「此 Google 帳號已被使用」

---

## 關鍵決策

- [x] 同 email 本地帳號：**自動綁定**
- [x] 軟刪除帳號：**禁止復原**，需管理員介入
- [x] Google OAuth 自動設 `is_verified = true`
- [x] OAuth 帳號可設密碼：**支援**

---

## 實作內容

### 1. DB 變更

```python
# app/models/user.py 新增欄位
oauth_provider = Column(String(50), nullable=True)   # "google"
oauth_sub = Column(String(255), nullable=True)       # Google 唯一 ID

# password_hash 改為 nullable=True (允許純 OAuth 帳號)
password_hash = Column(String(255), nullable=True)

# 唯一索引
Index("uq_oauth_sub_active", "oauth_provider", "oauth_sub",
      unique=True, postgresql_where=(is_deleted.is_(False)))
```

### 2. API 端點

| 端點 | 方法 | 說明 |
|------|------|------|
| `/oauth/google/authorize` | GET | 取得 Google 授權 URL |
| `/oauth/google/callback` | GET | 處理回調，返回 JWT |
| `/users/me/password` | PUT | 設定密碼 |
| `/users/me/oauth/link` | POST | 綁定 Google (已登入) |
| `/users/me/oauth/unlink` | DELETE | 解除 Google 綁定 |
| `/auth/forgot-password` | POST | 忘記密碼，發送重設信 |
| `/auth/reset-password` | POST | 重設密碼 (用 token) |

### 3. 檔案變更

**新增：**
- `app/services/oauth_service.py` - Google OAuth 邏輯
- `app/services/password_reset_service.py` - 密碼重設邏輯
- `app/api/v1/endpoints/api_oauth.py` - OAuth API 端點
- `app/schemas/oauth.py` - OAuth schemas
- `app/schemas/password_reset.py` - 密碼重設 schemas
- `alembic/versions/xxx_add_oauth_fields.py` - 遷移

**修改：**
- `app/models/user.py` - 新增 oauth 欄位，password_hash nullable，新增 reset_token 欄位
- `app/schemas/user.py` - UserResponse 加入 oauth_provider
- `app/services/user_service.py` - 新增 set_password()
- `app/api/v1/endpoints/api_users.py` - 新增設定密碼端點
- `app/api/v1/endpoints/api_auth.py` - 新增忘記/重設密碼端點
- `app/core/config.py` - 新增 Google OAuth 設定
- `app/api/v1/api.py` - 註冊 OAuth router
- `requirements.txt` - 新增 google-auth

### 4. 環境變數

```env
GOOGLE_OAUTH_CLIENT_ID=xxx
GOOGLE_OAUTH_CLIENT_SECRET=xxx
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/api/v1/oauth/google/callback
```

---

## 實作步驟

| 步驟 | 內容 | 工作量 |
|------|------|--------|
| 1 | Model 新增欄位 + 遷移 | 1h |
| 2 | Config 新增設定 | 0.5h |
| 3 | OAuthService 實作 | 2h |
| 4 | OAuth API 端點 (authorize, callback) | 1.5h |
| 5 | 設定密碼 API | 1h |
| 6 | 綁定/解除綁定 API | 1.5h |
| 7 | PasswordResetService 實作 | 1.5h |
| 8 | 忘記/重設密碼 API | 1h |
| 9 | 測試 | 4h |

**總工作量：14h**

---

## 測試案例

**Google OAuth:**
| 類型 | 測試 | 驗證 |
|------|------|------|
| Happy | 新使用者 Google 登入 | 建立帳號，返回 JWT |
| Happy | 回訪使用者 Google 登入 | 直接登入，返回 JWT |
| Happy | 同 email 自動綁定 | 綁定 Google，返回 JWT |
| Error | 授權取消 | 返回錯誤訊息 |
| Error | Token 驗證失敗 | 返回 401 |

**設定密碼:**
| 類型 | 測試 | 驗證 |
|------|------|------|
| Happy | OAuth 帳號設定密碼 | password_hash 更新 |
| Happy | 設定密碼後用密碼登入 | 登入成功 |
| Error | 密碼格式錯誤 | 返回 400 |

**綁定/解除綁定:**
| 類型 | 測試 | 驗證 |
|------|------|------|
| Happy | 已登入使用者綁定 Google | oauth_provider 更新 |
| Happy | 有密碼使用者解除綁定 | oauth_provider 清空 |
| Error | 未登入呼叫綁定 | 返回 401 |
| Error | 已綁定再次綁定 | 返回「已綁定」 |
| Error | 無密碼解除綁定 | 返回「請先設定密碼」 |
| Error | Google 帳號已被使用 | 返回「此帳號已被使用」 |

**忘記密碼:**
| 類型 | 測試 | 驗證 |
|------|------|------|
| Happy | 有密碼帳號申請重設 | 發送重設信 |
| Happy | 用 token 重設密碼 | password_hash 更新 |
| Info | 純 Google 帳號申請重設 | 提示用 Google 登入 |
| Info | 有 Google 綁定帳號 | 發送信 + 提示可用 Google |
| Error | Email 不存在 | 返回通用訊息 (安全) |
| Error | 重設 token 過期 | 返回「連結已過期」 |
| Error | 軟刪除帳號申請重設 | 返回「帳號已停用」 |

---

## 驗證方式

1. 執行遷移：`alembic upgrade head`
2. 啟動服務：`uvicorn app.main:app --reload`
3. 測試 OAuth 流程：
   - 訪問 `/oauth/google/authorize`
   - 完成 Google 授權
   - 確認返回 JWT
4. 測試設定密碼：
   - 用 JWT 呼叫 `/users/me/password`
   - 確認可用密碼登入
5. 測試忘記密碼：
   - 呼叫 `/auth/forgot-password`
   - 確認收到重設信 (或 console 輸出 token)
   - 用 token 呼叫 `/auth/reset-password`
   - 確認可用新密碼登入
6. 執行測試：`pytest tests/test_oauth*.py tests/test_password_reset.py -v`

---

## 備註：發送郵件

忘記密碼需要發送郵件。有兩種方式：

**開發階段：** 在 console 輸出 reset token，不實際發送郵件

**正式環境：** 需要設定郵件服務 (SMTP 或第三方如 SendGrid)

```env
# 郵件設定 (正式環境)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=xxx
SMTP_PASSWORD=xxx
```
