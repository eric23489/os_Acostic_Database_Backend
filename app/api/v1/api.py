from fastapi import APIRouter

from app.api.v1.endpoints import api_users
from app.api.v1.endpoints import api_recorders

api_router = APIRouter()
api_router.include_router(api_users.router)
api_router.include_router(api_recorders.router)