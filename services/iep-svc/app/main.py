# AIVO IEP Service - FastAPI Main Application  
# S1-11 Implementation - Strawberry GraphQL with CRDT Support

from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter
import strawberry
from contextlib import asynccontextmanager
import logging

from .resolvers import Query, Mutation, Subscription
from .database import engine, Base

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Strawberry GraphQL schema
schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    subscription=Subscription
)

# Application lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    logger.info("Starting IEP Service...")
    
    # Create database tables
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
    
    yield
    
    logger.info("IEP Service shutting down...")

# Create FastAPI application
app = FastAPI(
    title="AIVO IEP Service",
    description="Individual Education Program (IEP) management with GraphQL, CRDT, and E-Signatures",
    version="1.0.0",
    lifespan=lifespan
)

# Create GraphQL router
graphql_app = GraphQLRouter(
    schema,
    graphiql=True,  # Enable GraphiQL IDE in development
    path="/graphql"
)

# Include GraphQL router
app.include_router(graphql_app, prefix="/api/v1")

# Health check endpoints
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "aivo-iep-svc",
        "version": "1.0.0",
        "description": "IEP Service with Strawberry GraphQL",
        "graphql_endpoint": "/api/v1/graphql",
        "graphiql_ide": "/api/v1/graphql"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "iep-svc",
        "version": "1.0.0",
        "features": {
            "graphql": True,
            "crdt_collaboration": True,
            "e_signatures": True,
            "real_time_subscriptions": True
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8004,
        reload=True,
        log_level="info"
    )
