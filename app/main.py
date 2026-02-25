import logging

from fastapi import FastAPI

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.middleware import log_requests

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name)
app.middleware("http")(log_requests)

app.include_router(api_router, prefix=settings.api_prefix)
