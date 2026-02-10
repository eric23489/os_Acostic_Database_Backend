---
name: coverage-analysis
description: 分析測試覆蓋率，識別未覆蓋的程式碼路徑。
---

分析「$ARGUMENTS」的測試覆蓋率：

**覆蓋率目標:**

| 類型 | 目標 | 說明 |
|------|------|------|
| 行覆蓋率 | 80%+ | 基本要求 |
| 分支覆蓋率 | 70%+ | if/else 路徑 |
| 函式覆蓋率 | 90%+ | 所有公開方法 |

**關鍵路徑 (必須 100%):**
- [ ] 權限檢查邏輯
- [ ] 主要成功路徑
- [ ] 錯誤回滾邏輯

**可能遺漏的路徑:**
- 例外處理分支
- 邊界條件判斷
- 預設值邏輯

**覆蓋率檢查:**
```bash
pytest --cov=app/services/xxx --cov-report=term-missing
```

**未覆蓋分析:**
```
Name                    Stmts   Miss  Cover   Missing
-----------------------------------------------------
app/services/xxx.py       100     10    90%   45-50, 78
```

**改善建議:**
- 新增測試案例覆蓋 Missing 行
- 考慮是否為死碼可移除
- 評估是否需要達成 100%

**執行報告:**
```bash
pytest --cov --cov-report=html
# 開啟 htmlcov/index.html 查看詳細報告
```
