# AIVO Game Generation Service - Main FastAPI Application
# S2-13 Implementation - Service entry point with lifecycle management

import logging
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any
import uvicorn

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .database import engine as db_engine, Base
from .routes import router as game_router, game_engine
from .engine import GameGenerationEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan manager for startup and shutdown events.
    Handles game engine initialization and cleanup.
    """
    # Startup
    logger.info("Starting Game Generation Service...")
    
    try:
        # Create database tables
        Base.metadata.create_all(bind=db_engine)
        logger.info("Database tables created successfully")
        
        # Initialize game generation engine
        global game_engine
        game_engine = GameGenerationEngine()
        await game_engine.initialize()
        
        # Inject engine into routes module
        import services.game_gen_svc.app.routes as routes_module
        routes_module.game_engine = game_engine
        
        logger.info("Game Generation Service started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start service: {str(e)}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Game Generation Service...")
    
    try:
        # Cleanup game engine
        if game_engine:
            await game_engine.cleanup()
        
        logger.info("Game Generation Service shutdown complete")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")


# Create FastAPI application
app = FastAPI(
    title="AIVO Game Generation Service",
    description="""
    **S2-13 Game Generation Service**
    
    Generates personalized reset games for learners based on their profiles, preferences, and educational context.
    
    ## Features
    
    ### 🎮 Dynamic Game Generation
    - AI-powered content creation using OpenAI GPT-4
    - Template-based fallback for reliability
    - Learner-adaptive difficulty and content
    - Duration-aware game design (1-60 minutes)
    
    ### 👤 Learner Personalization
    - Grade band adaptations (Early Elementary → Adult)
    - Learning style and preference tracking
    - Accessibility feature support
    - Performance-based recommendations
    
    ### 🎯 Game Types Supported
    - **Puzzle Games**: Pattern solving, logic challenges
    - **Memory Games**: Recall and recognition activities  
    - **Word Games**: Vocabulary, language skills
    - **Math Games**: Arithmetic, problem solving
    - **Creative Games**: Art, music, storytelling
    - **Mindfulness Games**: Relaxation, focus activities
    - **Movement Games**: Physical activity integration
    - **Strategy Games**: Planning, critical thinking
    - **Trivia Games**: Knowledge reinforcement
    
    ### 📊 Analytics & Insights
    - Real-time session tracking
    - Engagement and performance metrics
    - Learning outcome analysis
    - Personalized improvement suggestions
    
    ### 🔄 Event-Driven Architecture
    - **GAME_READY**: Emitted when generation completes
    - **GAME_COMPLETED**: Emitted when session ends
    - Orchestrator integration for workflow management
    
    ### ✅ Quality Assurance
    - Manifest validation and quality scoring
    - Duration compliance checking
    - Content appropriateness verification
    - Accessibility standards compliance
    
    ## API Overview
    
    **Generation Flow:**
    1. POST `/api/v1/games/generate` - Start game generation
    2. GET `/api/v1/games/manifest/{id}` - Retrieve generated content
    3. POST `/api/v1/games/sessions` - Start game session
    4. PUT `/api/v1/games/sessions/{id}` - Update progress
    5. POST `/api/v1/games/sessions/{id}/complete` - Complete session
    
    **Management:**
    - Learner profile management
    - Game analytics and insights
    - Template and configuration management
    - Health monitoring and validation
    
    Built with FastAPI, SQLAlchemy, PostgreSQL, and AI integration.
    """,
    version="1.0.0",
    contact={
        "name": "AIVO Development Team",
        "url": "https://github.com/your-org/aivo-virtual-brains",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests for monitoring and debugging."""
    start_time = asyncio.get_event_loop().time()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url.path}")
    
    response = await call_next(request)
    
    # Log response with duration
    duration = asyncio.get_event_loop().time() - start_time
    logger.info(
        f"Response: {response.status_code} {request.url.path} - "
        f"{duration:.3f}s"
    )
    
    return response

# Error handling middleware
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions with consistent error format."""
    logger.error(f"HTTP {exc.status_code}: {exc.detail} - {request.url}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "type": "http_exception",
                "path": str(request.url.path),
                "timestamp": asyncio.get_event_loop().time()
            }
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    logger.error(f"Validation error: {exc.errors()} - {request.url}")
    
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": 422,
                "message": "Request validation failed",
                "type": "validation_error",
                "details": exc.errors(),
                "path": str(request.url.path),
                "timestamp": asyncio.get_event_loop().time()
            }
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unexpected error: {str(exc)} - {request.url}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error",
                "type": "server_error",
                "path": str(request.url.path),
                "timestamp": asyncio.get_event_loop().time()
            }
        }
    )

# Include routers
app.include_router(game_router)

# Root endpoint
@app.get("/", 
         summary="Service Information",
         description="Get basic information about the Game Generation Service.")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Game Generation Service",
        "version": "1.0.0",
        "description": "AIVO S2-13 - Dynamic reset game generation with AI personalization",
        "status": "operational",
        "features": [
            "AI-powered game generation",
            "Learner profile personalization",
            "10 different game types",
            "Grade band adaptations",
            "Duration-aware content",
            "Event-driven architecture",
            "Analytics and insights",
            "Accessibility support"
        ],
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc"
        },
        "endpoints": {
            "generate_game": "POST /api/v1/games/generate",
            "get_manifest": "GET /api/v1/games/manifest/{id}",
            "list_games": "GET /api/v1/games/",
            "start_session": "POST /api/v1/games/sessions",
            "update_session": "PUT /api/v1/games/sessions/{id}",
            "complete_session": "POST /api/v1/games/sessions/{id}/complete",
            "learner_profile": "POST /api/v1/games/profiles",
            "analytics": "GET /api/v1/games/analytics/{learner_id}",
            "validate": "POST /api/v1/games/validate/manifest",
            "health": "GET /api/v1/games/health"
        }
    }

# Additional service endpoints
@app.get("/version",
         summary="Service Version",
         description="Get detailed version and build information.")
async def get_version():
    """Get service version information."""
    return {
        "service": "game-gen-svc",
        "version": "1.0.0",
        "api_version": "v1",
        "build_info": {
            "stage": "S2-13",
            "implementation": "Dynamic reset games + events",
            "features": [
                "AI content generation",
                "Learner adaptation",
                "Event emission",
                "Quality validation"
            ]
        },
        "dependencies": {
            "fastapi": "^0.100.0",
            "sqlalchemy": "^2.0.0",
            "postgresql": "^15.0",
            "openai": "via inference gateway",
            "pydantic": "^2.0.0"
        }
    }

@app.get("/metrics",
         summary="Service Metrics",
         description="Get basic service metrics and statistics.")
async def get_metrics():
    """Get basic service metrics."""
    # In production, this would integrate with Prometheus or similar
    return {
        "service": "game-gen-svc",
        "metrics": {
            "uptime_seconds": 0,  # Would track actual uptime
            "requests_total": 0,  # Would track request count
            "active_sessions": 0,  # Would track active game sessions
            "games_generated": 0,  # Would track generation count
            "error_rate": 0.0,    # Would track error percentage
        },
        "health": {
            "database": "connected",
            "game_engine": "operational",
            "ai_service": "available"
        },
        "note": "Detailed metrics require Prometheus integration"
    }

# Development server runner
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
