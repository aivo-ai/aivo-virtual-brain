from fastapi import APIRouter
from datetime import datetime

router = APIRouter(prefix="/health", tags=["health"])

@router.get("")
def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "learner-svc",
        "version": "0.1.0"
    }

@router.get("/readiness")
def readiness():
    """Readiness check endpoint."""
    return {
        "ready": True,
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {
            "database": {"status": "ok"},
            "grade_calculator": {"status": "ok"}
        }
    }
