"""
Simple Auth Service
A simplified version of the auth service for development
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uvicorn

app = FastAPI(
    title="Auth Service",
    description="Authentication and authorization service",
    version="1.0.0"
)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "auth-svc", "version": "1.0.0"}

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Auth Service is running", "service": "auth-svc"}

# Authentication models
class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

class UserCreate(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None

# Authentication endpoints
@app.post("/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Simulate login - returns mock token"""
    if request.email and request.password:
        return TokenResponse(
            access_token="mock_token_" + request.email.replace("@", "_"),
            token_type="bearer",
            expires_in=3600
        )
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/auth/register", response_model=dict)
async def register(user: UserCreate):
    """Simulate user registration"""
    return {
        "message": "User registered successfully",
        "user_id": "mock_user_" + user.email.replace("@", "_"),
        "email": user.email
    }

@app.post("/auth/verify", response_model=dict)
async def verify_token(token: str):
    """Simulate token verification"""
    if token.startswith("mock_token_"):
        return {
            "valid": True,
            "user_id": token.replace("mock_token_", "").replace("_", "@"),
            "expires_in": 3600
        }
    return {"valid": False}

@app.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str):
    """Simulate token refresh"""
    return TokenResponse(
        access_token="refreshed_" + refresh_token,
        token_type="bearer", 
        expires_in=3600
    )

@app.delete("/auth/logout")
async def logout():
    """Simulate logout"""
    return {"message": "Logged out successfully"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3001)
