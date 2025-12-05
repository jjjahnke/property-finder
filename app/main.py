from fastapi import FastAPI
from app.api import properties, events
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME)

app.include_router(properties.router, prefix=f"{settings.API_V1_STR}/properties", tags=["properties"])
app.include_router(events.router, prefix=f"{settings.API_V1_STR}/events", tags=["events"])

@app.get("/")
def read_root():
    return {"Hello": "World"}
