from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health():
    return {"status": "healthy", "service": "health"}

@router.get("/health/detailed")
async def detailed_health():
    return {"status": "healthy", "checks": {"database": "ok"}}
