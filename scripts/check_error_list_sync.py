"""
驗證 app/core/exceptions.py 與 docs/error-list.md 的 AppException 定義同步。

退出碼：
  0 = 同步正常
  1 = 有不一致或缺漏
"""

from __future__ import annotations

import io
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# Windows 終端強制 UTF-8 輸出
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).parent.parent
EXCEPTIONS_PATH = REPO_ROOT / "app" / "core" / "exceptions.py"
ERROR_LIST_PATH = REPO_ROOT / "docs" / "error-list.md"

# 從 status.HTTP_404_NOT_FOUND 取出數字部分
_STATUS_CODE_RE = re.compile(r"HTTP_(\d+)_\w+")


@dataclass
class ErrorEntry:
    error_code: str
    message: str
    http_status: int


def _parse_http_status(raw: str) -> int:
    """將 'status.HTTP_404_NOT_FOUND' 轉為整數 404。"""
    match = _STATUS_CODE_RE.search(raw)
    if not match:
        raise ValueError(f"無法解析 HTTP status: {raw!r}")
    return int(match.group(1))


def parse_exceptions(path: Path) -> dict[str, ErrorEntry]:
    """解析 exceptions.py，回傳 error_code -> ErrorEntry 的 dict。"""
    text = path.read_text(encoding="utf-8")

    # 匹配 AppException(...) 多行區塊
    # 使用 [^\n]*\n\s* 跳過行尾的 noqa 注釋等內容
    block_re = re.compile(
        r"AppException\(\s*"
        r'error_code\s*=\s*"([^"]+)"[^\n]*\n\s*'
        r'message\s*=\s*"([^"]+)"[^\n]*\n\s*'
        r"http_status\s*=\s*(status\.HTTP_\d+_\w+)",
    )

    entries: dict[str, ErrorEntry] = {}
    for match in block_re.finditer(text):
        error_code = match.group(1)
        message = match.group(2)
        http_status = _parse_http_status(match.group(3))
        entries[error_code] = ErrorEntry(
            error_code=error_code,
            message=message,
            http_status=http_status,
        )
    return entries


def parse_error_list(path: Path) -> dict[str, ErrorEntry]:
    """解析 error-list.md table 行，回傳 error_code -> ErrorEntry 的 dict。"""
    text = path.read_text(encoding="utf-8")

    # 匹配格式：| `ERROR_CODE` | 404 | some message |
    row_re = re.compile(r"\|\s*`([A-Z_]+)`\s*\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|")

    entries: dict[str, ErrorEntry] = {}
    for match in row_re.finditer(text):
        error_code = match.group(1)
        http_status = int(match.group(2))
        message = match.group(3).strip()
        entries[error_code] = ErrorEntry(
            error_code=error_code,
            message=message,
            http_status=http_status,
        )
    return entries


def validate(
    from_code: dict[str, ErrorEntry],
    from_docs: dict[str, ErrorEntry],
) -> list[str]:
    """比對兩邊差異，回傳錯誤訊息列表。"""
    errors: list[str] = []

    code_keys = set(from_code)
    docs_keys = set(from_docs)

    for key in sorted(code_keys - docs_keys):
        errors.append(f"[缺文件] {key} 在 exceptions.py 有定義，但 error-list.md 沒有")

    for key in sorted(docs_keys - code_keys):
        errors.append(
            f"[過期文件] {key} 在 error-list.md 有記錄，但 exceptions.py 沒有定義"
        )

    for key in sorted(code_keys & docs_keys):
        code_entry = from_code[key]
        docs_entry = from_docs[key]

        if code_entry.message != docs_entry.message:
            errors.append(
                f"[message 不一致] {key}\n"
                f"  exceptions.py : {code_entry.message!r}\n"
                f"  error-list.md : {docs_entry.message!r}"
            )

        if code_entry.http_status != docs_entry.http_status:
            errors.append(
                f"[http_status 不一致] {key}\n"
                f"  exceptions.py : {code_entry.http_status}\n"
                f"  error-list.md : {docs_entry.http_status}"
            )

    return errors


def main() -> None:
    from_code = parse_exceptions(EXCEPTIONS_PATH)
    from_docs = parse_error_list(ERROR_LIST_PATH)

    errors = validate(from_code, from_docs)

    if not errors:
        print("OK: exceptions.py 與 error-list.md 完全同步")
        sys.exit(0)

    for error in errors:
        print(error)
    print(f"\n共 {len(errors)} 個不一致，請修正後再提交")
    sys.exit(1)


if __name__ == "__main__":
    main()
