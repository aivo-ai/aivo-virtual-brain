"""
Simple User Service
A simplified version of the user service for development
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
from datetime import datetime

app = FastAPI(
    title="User Service",
    description="User management and profile service",
    version="1.0.0"
)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "user-svc", "version": "1.0.0"}

# Root endpoint
@app.get("/")
async def root():
    return {"message": "User Service is running", "service": "user-svc"}

# User models
class UserProfile(BaseModel):
    user_id: str
    email: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None

class UserPreferences(BaseModel):
    language: str = "en"
    timezone: str = "UTC"
    notifications_enabled: bool = True

# Mock user storage
mock_users = {
    "user_1": UserProfile(
        user_id="user_1",
        email="demo@example.com",
        full_name="Demo User",
        avatar_url=None,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
}

# User management endpoints
@app.get("/users/{user_id}", response_model=UserProfile)
async def get_user(user_id: str):
    """Get user profile by ID"""
    if user_id in mock_users:
        return mock_users[user_id]
    raise HTTPException(status_code=404, detail="User not found")

@app.put("/users/{user_id}", response_model=UserProfile)
async def update_user(user_id: str, update: UserUpdate):
    """Update user profile"""
    if user_id not in mock_users:
        raise HTTPException(status_code=404, detail="User not found")
    
    user = mock_users[user_id]
    if update.full_name is not None:
        user.full_name = update.full_name
    if update.avatar_url is not None:
        user.avatar_url = update.avatar_url
    user.updated_at = datetime.now()
    
    return user

@app.get("/users", response_model=List[UserProfile])
async def list_users(limit: int = 10, offset: int = 0):
    """List all users with pagination"""
    users_list = list(mock_users.values())
    return users_list[offset:offset + limit]

@app.delete("/users/{user_id}")
async def delete_user(user_id: str):
    """Delete user account"""
    if user_id not in mock_users:
        raise HTTPException(status_code=404, detail="User not found")
    
    del mock_users[user_id]
    return {"message": "User deleted successfully"}

@app.get("/users/{user_id}/preferences", response_model=UserPreferences)
async def get_user_preferences(user_id: str):
    """Get user preferences"""
    if user_id not in mock_users:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserPreferences()

@app.put("/users/{user_id}/preferences", response_model=UserPreferences)
async def update_user_preferences(user_id: str, preferences: UserPreferences):
    """Update user preferences"""
    if user_id not in mock_users:
        raise HTTPException(status_code=404, detail="User not found")
    
    return preferences

@app.post("/users/{user_id}/avatar")
async def upload_avatar(user_id: str, avatar_data: str):
    """Upload user avatar (mock implementation)"""
    if user_id not in mock_users:
        raise HTTPException(status_code=404, detail="User not found")
    
    mock_users[user_id].avatar_url = f"https://avatars.example.com/{user_id}.jpg"
    mock_users[user_id].updated_at = datetime.now()
    
    return {"message": "Avatar uploaded successfully", "avatar_url": mock_users[user_id].avatar_url}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3002)
