import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router

app = FastAPI()

default_cors_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
configured_cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", ",".join(default_cors_origins)).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=configured_cors_origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
