from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"]


class RootResponse(BaseModel):
    app: str
    status: Literal["ok"]
    docs_url: str
    health_url: str
