from pydantic import BaseModel, Field

class Suggestion(BaseModel):
    """
    A model representing a suggestion bucket with a key and document count.
    """
    key: str = Field(..., description="Unique identifier for the bucket value.")
    doc_count: int = Field(..., ge=0, description="Number of documents associated with this bucket.")