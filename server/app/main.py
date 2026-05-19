from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from server.app.api.router import router as api_router
from server.config.settings import settings


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        yield

    app = FastAPI(
        title="winner-prediction",
        description="Sofascore 기반 축구 승부 예측 API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    web_demo = Path(__file__).resolve().parents[3] / "client" / "web_demo"
    if web_demo.exists():
        static_dir = web_demo / "static"
        if static_dir.exists():
            app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

        @app.get("/")
        async def index():
            from fastapi.responses import FileResponse

            return FileResponse(str(web_demo / "index.html"))

    return app


app = create_app()
