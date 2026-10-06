from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager

from app.auth import get_current_user
from app.config import settings
from app.database import init_db, session_scope
from app.repository.users import ensure_default_user
from app.routers.auth import router as auth_router
from app.routers.ws import router as ws_router
from app.routers.ropes import router as ropes_router
from app.routers.runs import router as runs_router
from app.routers.current import router as current_router
from app.routers.defects import router as defects_router
from app.routers.settings import router as settings_router
from app.routers.robot import router as robot_router
from app.routers.video import router as video_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with session_scope() as db:
        ensure_default_user(db, settings.DEFAULT_USERNAME, settings.DEFAULT_PASSWORD)
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

# Every route below serves inspection data and needs a signed-in operator.
# The websocket routers check the token inside their handlers instead.
signed_in = [Depends(get_current_user)]

# routers 
app.include_router(auth_router)
app.include_router(ws_router)
app.include_router(ropes_router, dependencies=signed_in)
app.include_router(runs_router, dependencies=signed_in)
app.include_router(current_router, dependencies=signed_in)
app.include_router(defects_router, dependencies=signed_in)
app.include_router(settings_router, dependencies=signed_in)
app.include_router(robot_router, dependencies=signed_in)
app.include_router(video_router)