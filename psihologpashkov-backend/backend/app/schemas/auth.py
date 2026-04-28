from typing import Literal

from pydantic import BaseModel


class TokenPayload(BaseModel):
    sub: str
    type: Literal["access", "refresh"]
    exp: int
    iat: int
    jti: str
