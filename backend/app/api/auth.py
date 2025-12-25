"""用户认证 API"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core import create_access_token, get_settings
from app.schemas import TokenResponse

router = APIRouter()
settings = get_settings()


class UserLogin(BaseModel):
    """登录请求"""
    username: str
    password: str


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin):
    """用户登录 - 仅验证 env 配置的 admin 账号"""
    if data.username != settings.admin_username or data.password != settings.admin_password:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    token = create_access_token({"username": settings.admin_username})
    return TokenResponse(token=token, username=settings.admin_username)
