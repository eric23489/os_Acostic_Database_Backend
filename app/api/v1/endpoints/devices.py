from fastapi import APIRouter

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("/", summary="List devices (placeholder)")
def list_devices():
    return {"message": "Device endpoints will be added soon."}
