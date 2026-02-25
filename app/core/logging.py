import logging
import sys

from app.core.config import settings


def setup_logging() -> None:
    """設定全域 logging，輸出純文字到 stdout。"""
    log_format = "%(asctime)s %(levelname)-8s %(name)s:%(filename)s:%(lineno)d - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=settings.log_level.upper(),
        format=log_format,
        datefmt=date_format,
        stream=sys.stdout,
        force=True,
    )

    # 降低第三方 library 的 log 噪音
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
