from typing import List, Optional

import streamlit as st

from src.api.models.web_suggest import WebSuggestRequest, WebSuggestResponse
from src.api.models.suggestions import Suggestion
from src.api.service.suggest import perform_search


@st.cache_data(
    ttl=15 * 60,
    max_entries=1000,
    hash_funcs={WebSuggestRequest: lambda r: r.model_dump()},
)
def search(request: WebSuggestRequest) -> WebSuggestResponse:
    """
    Executes a full search based on the provided request.

    Args:
        request (WebSuggestRequest): The search request containing query parameters.

    Returns:
        WebSuggestResponse: A structured response containing the time taken and suggestions.
    """
    raw_response = perform_search(request)
    took_in_millis = raw_response.get("took", 0)

    # Extract suggestions from the response's aggregations
    aggregations = raw_response.get("aggregations", {})
    suggestions = extract_suggestions_from_aggregations(aggregations)

    return WebSuggestResponse(took_in_millis=took_in_millis, suggestions=suggestions)


def extract_suggestions_from_aggregations(aggregations: dict) -> Optional[List[Suggestion]]:
    """
    Extracts suggestions from the aggregations dictionary.

    Args:
        aggregations (dict): Aggregations from the raw search response.

    Returns:
        Optional[List[Suggestion]]: A list of suggestions or None if no suggestions are found.
    """
    # Safely navigate the nested structure to access the buckets
    buckets = (
        aggregations
        .get("topics_parent", {})
        .get("topics", {})
        .get("topics", {})
        .get("buckets", [])
    )

    # Convert bucket data to Suggestion instances
    return [Suggestion(**bucket) for bucket in buckets]