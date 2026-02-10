---
name: fixture-design
description: 設計測試 Fixture，包含測試資料和環境設置。
---

設計「$ARGUMENTS」的測試 Fixture：

**用戶 Fixture:**
```python
@pytest.fixture
def mock_admin_user():
    """Mock Admin 用戶。"""
    user = MagicMock()
    user.id = 1
    user.email = "admin@example.com"
    user.role = UserRole.ADMIN.value
    user.is_active = True
    return user

@pytest.fixture
def mock_normal_user():
    """Mock 一般用戶。"""
    user = MagicMock()
    user.id = 2
    user.email = "user@example.com"
    user.role = UserRole.USER.value
    user.is_active = True
    return user
```

**資料 Fixture:**
```python
@pytest.fixture
def sample_resource():
    """建立測試用資源。"""
    return MagicMock(
        id=1,
        name="test-resource",
        is_deleted=False,
    )

@pytest.fixture
def deleted_resource():
    """建立已刪除的資源。"""
    return MagicMock(
        id=2,
        name="deleted-resource",
        is_deleted=True,
        deleted_at=datetime.now(UTC),
    )
```

**Fixture 設計原則:**
- 單一職責
- 可重用
- 名稱清晰
- 獨立不互相依賴

**清理策略:**
- 使用 `yield` 進行清理
- 每個測試獨立環境
