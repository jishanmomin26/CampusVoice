"""CampusVoice FastAPI Application Entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.endpoints import health, feedback, nlp, analysis, auth, users

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure Cross-Origin Resource Sharing (CORS)
# Uses FRONTEND_URL from environment settings
cors_origins = [settings.FRONTEND_URL]
if "http://localhost:5173" not in cors_origins:
    cors_origins.append("http://localhost:5173")
if "http://127.0.0.1:5173" not in cors_origins:
    cors_origins.append("http://127.0.0.1:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root-level health endpoint: GET /health
app.include_router(health.router, tags=["Health"])

# Versioned health endpoint: GET /api/v1/health
app.include_router(health.router, prefix=settings.API_V1_STR, tags=["Health"])

# Versioned feedback endpoints: POST & GET /api/v1/feedback
app.include_router(
    feedback.router,
    prefix=f"{settings.API_V1_STR}/feedback",
    tags=["Feedback"],
)

# Versioned feedback analysis endpoint: POST /api/v1/feedback/analyze
app.include_router(
    analysis.router,
    prefix=f"{settings.API_V1_STR}/feedback",
    tags=["Analysis"],
)

# Versioned NLP test endpoints: POST /api/v1/nlp/preprocess
app.include_router(
    nlp.router,
    prefix=f"{settings.API_V1_STR}/nlp",
    tags=["NLP"],
)

# Versioned authentication endpoints: POST & GET /api/v1/auth
app.include_router(
    auth.router,
    prefix=f"{settings.API_V1_STR}/auth",
    tags=["Auth"],
)

# Versioned user management endpoints: GET, POST, PATCH /api/v1/users
app.include_router(
    users.router,
    prefix=f"{settings.API_V1_STR}/users",
    tags=["Users"],
)


@app.get("/", tags=["Root"])
async def root():
    """Welcome endpoint providing service metadata and API pointers."""
    return {
        "message": "Welcome to CampusVoice API",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "health_check": "/health",
        "feedback_api": f"{settings.API_V1_STR}/feedback",
        "docs": "/docs",
    }
