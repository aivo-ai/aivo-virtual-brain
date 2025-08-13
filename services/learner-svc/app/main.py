from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from .routers import health, learners, persona
from .database import engine, Base

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Learner Service",
    description="AIVO Virtual Brains - Learner Management and Private Brain Service",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(learners.router)
app.include_router(persona.router)

@app.get("/")
def read_root():
    return {
        "message": "AIVO Learner Service",
        "version": "1.0.0",
        "features": [
            "Learner Management",
            "Private Brain Personas", 
            "AI Model Bindings",
            "Teacher/Guardian Access Control"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
