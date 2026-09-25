from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logger import logger
from app.api.endpoints import projects, datasets, preprocessing, scenarios, results, comparison, exports, jobs, hadr, satellite, location_intelligence, assets
import time
import traceback

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/storage", StaticFiles(directory="storage"), name="storage")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error", "detail": str(exc)},
        headers={"Access-Control-Allow-Origin": "*"}
    )

@app.get("/api/health")
async def health_check():
    """Health check endpoint to verify backend status."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": settings.PROJECT_NAME,
        "delft3d": {
            "configured": settings.DELFT3D_ENABLED,
            "mode": settings.DELFT3D_EXECUTION_MODE,
            "available": settings.DELFT3D_ENABLED # In a real env, we might check if the executable is reachable here
        }
    }

app.include_router(projects.router, prefix=f"{settings.API_V1_STR}/projects", tags=["projects"])
app.include_router(location_intelligence.router, prefix=f"{settings.API_V1_STR}/projects", tags=["location_intelligence"])
app.include_router(datasets.router, prefix=settings.API_V1_STR, tags=["datasets"])
app.include_router(preprocessing.router, prefix=settings.API_V1_STR, tags=["preprocessing"])
app.include_router(scenarios.router, prefix=settings.API_V1_STR, tags=["scenarios"])
app.include_router(results.router, prefix=settings.API_V1_STR, tags=["results"])
app.include_router(comparison.router, prefix=settings.API_V1_STR, tags=["comparison"])
app.include_router(exports.router, prefix=settings.API_V1_STR, tags=["exports"])
app.include_router(jobs.router, prefix=settings.API_V1_STR, tags=["jobs"])
app.include_router(hadr.router, prefix=settings.API_V1_STR, tags=["hadr"])
app.include_router(satellite.router, prefix=settings.API_V1_STR, tags=["satellite"])
app.include_router(assets.router, prefix=f"{settings.API_V1_STR}/projects", tags=["assets"])
from app.api.endpoints import government
app.include_router(government.router, prefix=f"{settings.API_V1_STR}/government", tags=["government"])
logger.info(f"Starting {settings.PROJECT_NAME} Backend")
