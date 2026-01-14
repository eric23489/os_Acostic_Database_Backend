from fastapi import APIRouter

from app.api.v1.endpoints import api_users
from app.api.v1.endpoints import api_recorders
from app.api.v1.endpoints import api_projects
from app.api.v1.endpoints import api_points
from app.api.v1.endpoints import api_deployments

api_router = APIRouter()
api_router.include_router(api_users.router)
api_router.include_router(api_recorders.router)
api_router.include_router(api_projects.router)
api_router.include_router(api_points.router)
api_router.include_router(api_deployments.router)
