---
name: test-cases
description: 設計詳細的測試案例清單，包含各種情境覆蓋。
---

設計「$ARGUMENTS」的測試案例：

**測試案例清單:**

| 類型 | 測試名稱 | 驗證目標 | 優先級 |
|------|---------|----------|--------|
| Permission | test_requires_login | 未登入回傳 401 | P0 |
| Permission | test_requires_admin | 非 Admin 回傳 403 | P0 |
| Happy | test_success | 成功執行回傳 200 | P0 |
| Error | test_not_found | 不存在回傳 404 | P1 |
| Error | test_validation_error | 驗證失敗回傳 400 | P1 |
| Edge | test_empty_data | 空資料處理 | P2 |
| Edge | test_large_batch | 大量資料處理 | P2 |

**測試案例模板:**
```python
def test_case_name(self, client, fixtures):
    """測試說明：驗證什麼行為。"""
    # Arrange - 準備測試資料

    # Act - 執行操作
    response = client.method("/endpoint")

    # Assert - 驗證結果
    assert response.status_code == expected
    assert response.json()["field"] == expected
```

**驗證清單:**
- [ ] 回應狀態碼
- [ ] 回應內容
- [ ] 資料庫狀態變化
- [ ] 副作用 (MinIO, 日誌)
