from pydantic import BaseModel


class UserBase(BaseModel):
    username: str
    email: str


class UserCreate(UserBase):
    pass


class UserResponse(UserBase):
    id: int
    role: str

    class Config:
        from_attributes = True  # 允許從 ORM 物件讀取資料
