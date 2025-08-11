from fastapi import FastAPI
from datetime import datetime
import os

app = FastAPI(title="Auth Service", description="Authentication service", version="0.1.0")

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "auth-svc",
        "version": "0.1.0"
    }

@app.get("/readiness")
def readiness():
    return {
        "ready": True,
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {"basic": {"status": "ok"}}
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
