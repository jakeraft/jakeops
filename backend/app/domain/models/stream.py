from pydantic import BaseModel


class StreamEvent(BaseModel):
    type: str
    subtype: str | None = None
    parent_tool_use_id: str | None = None
    message: dict | None = None
    session_id: str | None = None


class StreamMetadata(BaseModel):
    model: str = "unknown"
    cwd: str | None = None
    skills: list[str] = []
    plugins: list[str] = []
    cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    duration_ms: int = 0
    is_success: bool = False
    result_text: str = ""
