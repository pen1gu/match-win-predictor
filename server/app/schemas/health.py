from pydantic import BaseModel, Field


class HealthRead(BaseModel):
    status: str = "ok"
