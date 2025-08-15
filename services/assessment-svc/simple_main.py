from fastapi import FastAPI
from datetime import datetime
import os

app = FastAPI(title="Assessment Service", description="Assessment and evaluation service", version="0.1.0")

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "assessment-svc",
        "version": "0.1.0"
    }

@app.get("/readiness")
def readiness():
    return {
        "ready": True,
        "timestamp": datetime.utcnow().isoformat(),
        "service": "assessment-svc",
        "checks": {
            "database": "skip", # Skip DB checks for now
            "external_apis": "skip"
        }
    }

@app.get("/")
def root():
    return {"message": "AIVO Assessment Service", "status": "running"}

@app.get("/api/v1/status")
def status():
    return {
        "service": "assessment-svc",
        "status": "operational",
        "version": "0.1.0",
        "timestamp": datetime.utcnow().isoformat()
    }

# Simple assessment endpoints
@app.post("/api/v1/assessments")
def create_assessment():
    return {"message": "Assessment creation endpoint - under development"}

@app.get("/api/v1/assessments/{assessment_id}")
def get_assessment(assessment_id: str):
    return {"message": f"Get assessment {assessment_id} - under development"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3004)
