from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.routes import router
from .core.config import settings
from .db.database import init_db
from .market.stream import stream
from .alerts.processor import processor

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await stream.start()
    await processor.start()
    yield
    await processor.stop()
    await stream.stop()

app=FastAPI(title='AI Trading Platform API',version='1.2.0',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=[x.strip() for x in settings.cors_origins.split(',')],allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
app.include_router(router,prefix='/api')
