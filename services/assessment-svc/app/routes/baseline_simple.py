# Simple baseline route for testing
from fastapi import APIRouter

router = APIRouter()

@router.get("/test")
def test_route():
    return {"message": "baseline route working"}
