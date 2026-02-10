# 提升測試覆蓋率

> **狀態：已完成** (2026-02-09)
>
> - 4 個測試檔案新增
> - 59 個新單元測試
> - 192 個測試全部通過
> - 覆蓋率從 75% 提升至 85%

## 目標
將整體覆蓋率從 75% 提升到 85%+

## 優先補強檔案

| 檔案 | 目前 | 目標 | 需測試項目 |
|------|------|------|-----------|
| `user_service.py` | 20% | 80% | create_user, authenticate_user, update_user, delete_user, restore_user, set_password |
| `auth.py` | 39% | 80% | get_current_user (JWT 驗證), get_current_admin_user |
| `password_reset_service.py` | 42% | 80% | initiate_password_reset, reset_password, send_reset_email |
| `oauth_service.py` | 31% | 70% | authenticate_with_google, link/unlink (需 mock requests) |

## 新增測試檔案

### `tests/test_user_service.py`
測試 UserService 所有方法：
- create_user: 成功、email 重複
- authenticate_user: 成功、不存在、密碼錯誤、無密碼、停用帳號
- get_users: 正常查詢
- update_user: 成功、不存在、更新密碼
- delete_user: 成功、不存在
- restore_user: 成功、不存在、email 衝突
- set_password: 成功、不存在、密碼太短

### `tests/test_auth.py`
測試認證函式：
- get_current_user: 有效 token、無效 token、過期 token、使用者不存在、停用使用者
- get_current_admin_user: admin 通過、非 admin 拒絕

### `tests/test_password_reset_service_unit.py`
測試 PasswordResetService：
- initiate_password_reset: 有密碼帳號、OAuth-only、不存在、停用帳號
- reset_password: 成功、token 不存在、token 過期、密碼太短
- send_reset_email: console 輸出模式

### `tests/test_oauth_service_unit.py`
測試 OAuthService (mock requests)：
- get_google_authorization_url: 成功、未設定
- exchange_code_for_tokens: 成功、失敗
- authenticate_with_google: 新使用者、回訪、自動綁定、已停用
- link_google_account: 成功、已綁定、帳號被占用
- unlink_google_account: 成功、未綁定、無密碼

## 驗證
```bash
pytest --cov=app --cov-report=term-missing tests/
```
