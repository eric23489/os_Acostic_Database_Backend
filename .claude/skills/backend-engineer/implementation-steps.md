---
name: implementation-steps
description: 列出具體的實作步驟，包含檔案路徑和程式碼片段。
---

「$ARGUMENTS」的實作步驟：

**Step 1: 準備工作**
- [ ] 閱讀相關現有程式碼
- [ ] 確認 Schema 需求
- [ ] 確認測試策略

**Step 2: Service 層實作**
檔案: `app/services/xxx_service.py`
```python
def new_method(self, param: Type) -> ReturnType:
    """方法說明。"""
    # 實作內容
    pass
```

**Step 3: API 層實作**
檔案: `app/api/v1/endpoints/api_xxx.py`
```python
@router.method("/path", response_model=Schema)
def endpoint_name(
    param: Type,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """端點說明。"""
    return Service(db).method(param)
```

**Step 4: 測試**
檔案: `tests/test_xxx.py`
- [ ] 權限測試
- [ ] 成功案例
- [ ] 錯誤案例
- [ ] 邊界條件

**Step 5: 驗證**
- [ ] 執行測試: `pytest tests/test_xxx.py -v`
- [ ] 手動測試 API
- [ ] 程式碼審查
