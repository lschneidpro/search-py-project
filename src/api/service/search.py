from typing import Dict, Tuple, Optional


from src.api.models.web_search import WebSearchRequest
from src.api.repository.search import get_search_client
from src.api.service.builders_filters import construct_nested_filters
from src.api.service.builders_aggs import (
    build_unselected_field_aggregations,
    build_selected_field_aggregations,
)
from src.api.config import INDEX



def construct_query(request: WebSearchRequest) -> Dict:
    """
    Builds the base Elasticsearch query with optional filters.

    Args:
        request (WebSearchRequest): The search request containing query parameters.

    Returns:
        Dict: The constructed Elasticsearch query.
    """
    base_query = {"bool": {"must": [{"match_all": {}}]}}

    if request.q:
        base_query = {
            "bool": {
                "must": [
                    {
                        "combined_fields": {
                            "query": request.q,
                            "fields": [
                                "search_data.full_text_boosted.standard^7",
                                "search_data.full_text.standard^2",
                            ],
                            "minimum_should_match": "75%",
                            "_name": "match__standard",
                        }
                    }
                ],
                "should": [
                    {
                        "combined_fields": {
                            "query": request.q,
                            "fields": [
                                "search_data.full_text_boosted^7",
                                "search_data.full_text^2",
                            ],
                            "operator": "OR",
                            "_name": "match__minimal",
                        }
                    },
                    {
                        "combined_fields": {
                            "query": request.q,
                            "fields": [
                                "search_data.full_text_boosted.shingles^7",
                                "search_data.full_text.shingles^2",
                            ],
                            "operator": "OR",
                            "_name": "match__shingles",
                        }
                    },
                ],
            }
        }

    if request.pre_filters:
        nested_filters = construct_nested_filters(request.pre_filters)
        if nested_filters:
            base_query["bool"].setdefault("filter", []).append(nested_filters)

    return base_query


def construct_aggregations_and_post_filter(
    request: WebSearchRequest,
) -> Tuple[Dict, Optional[Dict]]:
    """
    Constructs Elasticsearch aggregations and a post filter based on the search request.

    Args:
        request (WebSearchRequest): The search request object.

    Returns:
        Tuple[Dict, Optional[Dict]]: A tuple containing the aggregations and an optional post filter.
    """
    aggregations = {}
    post_filter = None

    if request.facets and request.facets.enabled:
        filters = request.facets.filters

        if filters:
            # Build both selected and unselected field aggregations
            aggregations.update(
                {
                    **build_unselected_field_aggregations(filters),
                    **build_selected_field_aggregations(filters),
                }
            )
            # Create a post filter for selected facets
            post_filter = construct_nested_filters(filters)
        else:
            # Build aggregations for unselected fields only
            aggregations.update(build_unselected_field_aggregations())

    return aggregations, post_filter


def perform_search(request: WebSearchRequest) -> dict:
    """
    Executes a search request on the Elasticsearch index.

    Args:
        request (WebSearchRequest): The search request containing query, filters, and pagination.

    Returns:
        dict: The Elasticsearch search response.
    """
    client = get_search_client()

    # Construct query and aggregations
    query = construct_query(request)
    aggregations, post_filter = construct_aggregations_and_post_filter(request)

    # Perform the search
    resp = client.search(
        index=INDEX,
        query=query,
        aggs=aggregations,
        post_filter=post_filter,
        size=request.pagination.page_size,
        from_=request.pagination.calculate_from(),
        preference=request.preference,
    )

    return resp
