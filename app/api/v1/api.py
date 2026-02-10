from fastapi import APIRouter

from app.api.v1.endpoints import (
    api_audio,
    api_auth,
    api_deployments,
    api_oauth,
    api_points,
    api_projects,
    api_recorders,
    api_users,
)

api_router = APIRouter()
api_router.include_router(api_users.router)
api_router.include_router(api_recorders.router)
api_router.include_router(api_projects.router)
api_router.include_router(api_points.router)
api_router.include_router(api_deployments.router)
api_router.include_router(api_audio.router)
api_router.include_router(api_oauth.router)
api_router.include_router(api_auth.router)
