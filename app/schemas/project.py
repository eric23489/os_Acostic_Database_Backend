from typing import Optional
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, ConfigDict, field_validator, field_serializer


class ProjectBase(BaseModel):
    name: str
    area: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    is_finished: Optional[bool] = False
    owner: Optional[str] = None
    contractor: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None

    @field_validator("start_time", "end_time")
    @classmethod
    def set_timezone(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is not None and v.tzinfo is None:
            # 如果時間沒有時區資訊，預設加上台灣時區 (UTC+8)
            tw_tz = timezone(timedelta(hours=8))
            return v.replace(tzinfo=tw_tz)
        return v


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    area: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    is_finished: Optional[bool] = None
    owner: Optional[str] = None
    contractor: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None


class ProjectResponse(ProjectBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("start_time", "end_time", "created_at", "updated_at")
    def serialize_dt(self, dt: Optional[datetime], _info):
        if dt is None:
            return None
        return dt.astimezone(timezone(timedelta(hours=8)))
