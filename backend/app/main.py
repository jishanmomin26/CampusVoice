"""CampusVoice FastAPI Application Entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.endpoints import health

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure Cross-Origin Resource Sharing (CORS)
# Allows local React development server to interact with the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include root-level health router: GET /health
app.include_router(health.router)

# Include versioned API router: GET /api/v1/health
app.include_router(health.router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Root"])
async def root():
    """Welcome endpoint providing metadata and pointers."""
    return {
        "message": "Welcome to CampusVoice API",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "health_check": "/health",
        "docs": "/docs",
    }
