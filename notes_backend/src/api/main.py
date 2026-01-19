from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes.notes import router as notes_router

app = FastAPI(
    title="Simple Notes API",
    description="REST API for creating, viewing, updating, and deleting notes.",
    version="0.1.0",
    openapi_tags=[
        {"name": "health", "description": "Service health and readiness endpoints"},
        {"name": "notes", "description": "CRUD operations for notes"},
    ],
)

# Keep CORS enabled as currently configured (permissive).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers under /api.
app.include_router(notes_router, prefix="/api")


@app.get(
    "/",
    tags=["health"],
    summary="Health check",
    description="Basic health check endpoint.",
    operation_id="health_check",
)
def health_check():
    """Return a simple health status payload."""
    return {"message": "Healthy"}
