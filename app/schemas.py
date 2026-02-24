from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str
    k: int = 3


class Doc(BaseModel):
    id: str
    title: str = ""
    text: str
    score: float = 0.0
