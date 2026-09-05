from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager

from app.config import settings
from app.database import init_db
from app.routers.ws import router as ws_router
from app.routers.ropes import router as ropes_router
from app.routers.runs import router as runs_router
from app.routers.current import router as current_router
from app.routers.defects import router as defects_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/api/health", tags=["meta"])
def health():
    return {"status": "ok"}

# routers 
app.include_router(ws_router)
app.include_router(ropes_router)
app.include_router(runs_router)
app.include_router(current_router)
app.include_router(defects_router)