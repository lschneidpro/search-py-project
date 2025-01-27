from typing import Optional

import math

from src.utils import number_of_search_terms_from
from src.api.repository.search import get_search_client
from src.api.models.web_suggest import WebSuggestRequest

from src.api.config import INDEX


def get_completion_prefix(input_string: str) -> Optional[str]:
    """
    Extracts the completion prefix from the input string.

    Args:
        input_string (str): The user-provided input.

    Returns:
        str | None: The prefix for completion, or None if the string is too short.
    """
    # if the input string is too short, then don't attempt completion
    if len(input_string) < 2:
        return None

    # get the last uncompleted string
    input_string = input_string.lstrip()
    last_space_index = input_string.rfind(" ")
    prefix = input_string[last_space_index + 1 :]

    # if the prefix is 1 or less chars then include the previous word in the prefix
    if len(prefix) <= 1:
        previous_space_index = input_string[:last_space_index].rfind(" ")
        prefix = input_string[previous_space_index + 1 :]

    return prefix


def construct_query(context_tags: list[str]) -> Optional[dict]:
    """
    Constructs a query for Elasticsearch based on context tags.

    Args:
        context_tags (list[str]): Tags for query context.

    Returns:
        dict | None: The Elasticsearch query or None if no tags are provided.
    """
    if not context_tags:
        return None

    return {
        "bool": {
            "filter": [
                {
                    "nested": {
                        "_name": f"completion_match__{tag}",
                        "path": "completion_terms",
                        "query": {
                            "match": {
                                "completion_terms.tag.edge_ngram": {"query": tag}
                            }
                        },
                    }
                }
                for tag in context_tags
            ]
        }
    }



def construct_aggregations(query_string: str) -> Optional[dict]:
    """
    Constructs Elasticsearch aggregations based on the query string.

    Args:
        query_string (str): The user input query.

    Returns:
        dict | None: Aggregations for Elasticsearch or None if the query is not applicable.
    """
    # Extract the prefix and validate its presence
    prefix = get_completion_prefix(query_string)
    if not prefix:
        return None

    # Calculate search term counts and fuzzy prefix length
    search_terms_count = number_of_search_terms_from(query_string)
    prefix_terms_count = number_of_search_terms_from(prefix)
    fuzzy_prefix_length = max(1, math.floor(len(prefix) / 3))

    # Fields used in the aggregation
    edge_ngram_field = "completion_terms.tag.edge_ngram"
    keyword_field = "completion_terms.tag.keyword"

    # Define common "should" clauses for prefix matches
    common_should_clauses = [
        {"term": {edge_ngram_field: prefix}},
        {"match_phrase": {edge_ngram_field: {"query": prefix}}},
        {
            "match": {
                edge_ngram_field: {
                    "query": prefix,
                    "operator": "OR",
                    "fuzziness": "AUTO",
                    "prefix_length": fuzzy_prefix_length,
                }
            }
        },
    ]

    # Determine aggregation strategy based on search terms
    if search_terms_count <= 1:
        should_clauses = common_should_clauses
        include_param = None  # No `include` parameter for single search term
    elif search_terms_count == prefix_terms_count:
        should_clauses = [
            {
                "multi_match": {
                    "query": prefix,
                    "type": "bool_prefix",
                    "fields": [
                        "completion_terms.tag",
                        "completion_terms.tag._2gram",
                        "completion_terms.tag._3gram",
                    ],
                }
            }
        ]
        include_param = f"{prefix}.*"  # Exact match inclusion for prefix terms
    else:
        should_clauses = common_should_clauses
        include_param = f"{prefix}.*"  # Partial inclusion for other cases

    # Configure the terms aggregation
    terms_aggregation = {"field": keyword_field, "size": 10}
    if include_param:
        terms_aggregation["include"] = include_param

    # Build and return the nested aggregation
    return {
        "topics_parent": {
            "nested": {"path": "completion_terms"},
            "aggs": {
                "topics": {
                    "filter": {"bool": {"should": should_clauses}},
                    "aggs": {"topics": {"terms": terms_aggregation}},
                }
            },
        }
    }


def perform_search(request: WebSuggestRequest) -> dict:
    """
    Executes a search request on the Elasticsearch index.

    Args:
        request (WebSearchRequest): The search request containing query, filters, and pagination.

    Returns:
        dict: The Elasticsearch search response.
    """
    client = get_search_client()

    # Construct query and aggregations
    query = construct_query(request.context_tags)
    aggregations = construct_aggregations(request.q)

    # Perform the search
    resp = client.search(
        index=INDEX,
        query=query,
        aggs=aggregations,
        size=0,
        preference=request.preference,
        filter_path="took,**.buckets.key,**.buckets.doc_count"
    )

    return resp
