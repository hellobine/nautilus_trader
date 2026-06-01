from typing import Any

from pydantic import BaseModel


class ApiError(BaseModel):
    """统一的结构化错误返回体。"""

    code: str
    message: str
    detail: Any | None = None
