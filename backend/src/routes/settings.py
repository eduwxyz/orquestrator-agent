"""Settings routes for auto-cleanup configuration."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/settings", tags=["settings"])


# Esquemas Pydantic
class AutoCleanupSettings(BaseModel):
    """Auto-cleanup configuration settings."""
    enabled: bool
    cleanup_after_days: int  # 1-30 days


class AutoCleanupResponse(BaseModel):
    """Response for auto-cleanup settings."""
    success: bool
    settings: AutoCleanupSettings


class UpdateAutoCleanupRequest(BaseModel):
    """Request to update auto-cleanup settings."""
    enabled: Optional[bool] = None
    cleanup_after_days: Optional[int] = None


# Em memória por enquanto (pode ser movido para DB/config file depois)
_auto_cleanup_settings = AutoCleanupSettings(
    enabled=True,
    cleanup_after_days=7
)


@router.get("/auto-cleanup", response_model=AutoCleanupResponse)
async def get_auto_cleanup_settings():
    """Get current auto-cleanup settings."""
    return AutoCleanupResponse(
        success=True,
        settings=_auto_cleanup_settings
    )


@router.put("/auto-cleanup", response_model=AutoCleanupResponse)
async def update_auto_cleanup_settings(request: UpdateAutoCleanupRequest):
    """Update auto-cleanup settings."""
    global _auto_cleanup_settings

    if request.enabled is not None:
        _auto_cleanup_settings.enabled = request.enabled

    if request.cleanup_after_days is not None:
        if request.cleanup_after_days < 1 or request.cleanup_after_days > 30:
            raise HTTPException(
                status_code=400,
                detail="cleanup_after_days must be between 1 and 30"
            )
        _auto_cleanup_settings.cleanup_after_days = request.cleanup_after_days

    return AutoCleanupResponse(
        success=True,
        settings=_auto_cleanup_settings
    )
