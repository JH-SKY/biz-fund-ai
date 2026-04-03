# src/app/api/v1/router.py
"""API v1 라우터 집계."""

from fastapi import APIRouter

from src.app.api.v1.admin_router import router as admin_router
from src.app.api.v1.auth_router import router as auth_router
from src.app.api.v1.business_router import router as business_router
from src.app.api.v1.policy_router import router as policy_router
from src.app.api.v1.users_router import router as users_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(admin_router)
api_router.include_router(business_router)
api_router.include_router(policy_router)
