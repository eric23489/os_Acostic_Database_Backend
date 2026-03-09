import re
from datetime import datetime, timedelta, timezone

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from app.enums.enums import ProjectType


class ProjectBase(BaseModel):
    name: str | None = None
    name_zh: str | None = Field(None, max_length=100)
    area: str | None = Field(None, max_length=100)
    description: str | None = Field(None, max_length=2000)
    start_time: datetime | None = None
    end_time: datetime | None = None
    is_finished: bool | None = False
    owner: str | None = Field(None, max_length=200)
    contractor: str | None = Field(None, max_length=200)
    contact_name: str | None = Field(None, max_length=100)
    contact_phone: str | None = Field(None, max_length=30)
    contact_email: str | None = Field(None, max_length=254)
    project_type: ProjectType | None = None

    @field_validator("start_time", "end_time")
    @classmethod
    def set_timezone(cls, v: datetime | None) -> datetime | None:
        if v is not None and v.tzinfo is None:
            # 如果時間沒有時區資訊，預設加上台灣時區 (UTC+8)
            tw_tz = timezone(timedelta(hours=8))
            return v.replace(tzinfo=tw_tz)
        return v

    @model_validator(mode="after")
    def validate_time_range(self) -> "ProjectBase":
        if self.start_time and self.end_time and self.start_time > self.end_time:
            raise ValueError("start_time must be before or equal to end_time")
        return self


class ProjectCreate(ProjectBase):
    @field_validator("name")
    @classmethod
    def validate_project_name(cls, v: str | None) -> str | None:
        # Allow None - name can be auto-generated from name_zh
        if v is None:
            return v

        # MinIO/S3 Bucket naming rules:
        # 1. Length 3-63 characters
        # 2. Lowercase letters, numbers, dots, hyphens
        # 3. Start/end with letter or number
        # 4. No IP address format

        # Auto-convert to lowercase
        v = v.lower()

        if not re.match(r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$", v):
            raise ValueError(
                "Project name must be 3-63 chars, lowercase, numbers,"
                " dots, hyphens only, and start/end with alphanumeric."
            )

        return v


class ProjectUpdate(BaseModel):
    name: str | None = None
    name_zh: str | None = Field(None, max_length=100)
    area: str | None = Field(None, max_length=100)
    description: str | None = Field(None, max_length=2000)
    start_time: datetime | None = None
    end_time: datetime | None = None
    is_finished: bool | None = None
    owner: str | None = Field(None, max_length=200)
    contractor: str | None = Field(None, max_length=200)
    contact_name: str | None = Field(None, max_length=100)
    contact_phone: str | None = Field(None, max_length=30)
    contact_email: str | None = Field(None, max_length=254)
    project_type: ProjectType | None = None

    @field_validator("name")
    @classmethod
    def validate_project_name(cls, v: str | None) -> str | None:
        # Allow None - name can be auto-generated from name_zh
        if v is None:
            return v

        # MinIO/S3 Bucket naming rules:
        # 1. Length 3-63 characters
        # 2. Lowercase letters, numbers, dots, hyphens
        # 3. Start/end with letter or number
        # 4. No IP address format

        # Auto-convert to lowercase
        v = v.lower()

        if not re.match(r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$", v):
            raise ValueError(
                "Project name must be 3-63 chars, lowercase, numbers,"
                " dots, hyphens only, and start/end with alphanumeric."
            )

        return v


class ProjectResponse(ProjectBase):
    name: str  # In response, name is always present
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("start_time", "end_time", "created_at", "updated_at")
    def serialize_dt(self, dt: datetime | None, _info):
        if dt is None:
            return None
        return dt.astimezone(timezone(timedelta(hours=8)))

    @field_serializer("project_type")
    def serialize_project_type(self, pt: ProjectType | None, _info):
        if pt is None:
            return None
        return pt.value
