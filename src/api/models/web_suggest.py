from typing import Optional, List
from typing_extensions import Annotated

from pydantic import BaseModel, Field, StringConstraints

from src.api.models.suggestions import Suggestion


class WebSuggestRequest(BaseModel):
    q: str = Field(
        default=None,
        description=(
            "The primary text input entered by the user in the search bar. "
            "This is usually an incomplete or partial query string (e.g., 'Leathe' for 'Leather Seats') "
            "and is used to generate relevant autocomplete suggestions."
        ),
        example="Leathe",
    )
    context_tags: Optional[List[str]] = Field(
        default=None,
        description=(
            "A list of context tags derived by the client from the user's input, used to filter the underlying documents. "
            "These tags refine the suggestion results and can be reused from a previous autocomplete response. "
            "For example, 'Blue' and 'SUV' might represent specific attributes extracted from the input."
        ),
        example=["Blue", "SUV"],
    )

    preference: Optional[str] = Field(
        default=None,
        description=(
            "Custom preference string to control shard selection for consistent routing. "
            "If the cluster state and selected shards do not change, searches using the same preference value "
            "are routed to the same shards in the same order."
        ),
        examples=["custom-preference"],
    )

    class Config:
        extra = "forbid"


class WebSuggestResponse(BaseModel):
    """
    Represents the response for a web suggestion API,
    including the time taken to process and a list of suggestions.
    """

    took_in_millis: int = Field(
        default=0,
        description="The time taken to process the request, in milliseconds.",
        example=45,
    )
    suggestions: Optional[List[Suggestion]] = Field(
        default=None, description="A list of suggestion buckets, if available."
    )
