from typing import List, Dict, Optional

import streamlit as st

from src.api.models.web_search import WebSearchRequest, WebSearchResponse
from src.api.models.facets import (
    FacetResponse,
    HierarchicalFacetResponse,
    NumericFacetResponse,
    TermFacetResponse,
    NumberStats,
    HierarchicalAggregationBucket,
    TermAggregationBucket,
)
from src.api.models.filters import FieldFilter
from src.api.service.search import perform_search
from src.api.constants import FilterType


@st.cache_data(
    ttl=15 * 60,
    max_entries=1000,
    hash_funcs={WebSearchRequest: lambda r: r.model_dump()},
)
def search(request: WebSearchRequest) -> WebSearchResponse:
    """
    Executes a full search based on the given request.

    Args:
        request (WebSearchRequest): Contains the search query parameters.

    Returns:
        WebSearchResponse: The structured search response.
    """
    raw_response = perform_search(request)
    return transform_search_response(raw_response, request)


def transform_search_response(
    raw_response: Dict, request: WebSearchRequest
) -> WebSearchResponse:
    """
    Converts raw search response into a structured WebSearchResponse.

    Args:
        raw_response (Dict): Raw response from the backend.
        request (WebSearchRequest): Original search request.

    Returns:
        WebSearchResponse: Formatted response with hits, pagination, and facets.
    """
    took_in_millis = raw_response.get("took", 0)
    total_hits = raw_response.get("hits", {}).get("total", {}).get("value", 0)
    request.pagination.total_pages = request.pagination.calculate_total_pages(
        total_hits
    )

    facets = extract_facets_from_aggregations(
        aggregations=raw_response.get("aggregations", {}),
        request_filters=request.facets.filters or [],
    )
    # TODO: parse specific sourcw
    return WebSearchResponse(
        took_in_millis=took_in_millis,
        total_hits=total_hits,
        pagination=request.pagination,
        facets=facets,
        hits=raw_response.get("hits", {}).get("hits", []),
    )


def build_hierarchical_tree(
    buckets: List[Dict], field_filter: Optional[FieldFilter] = None
) -> HierarchicalAggregationBucket:
    """
    Constructs a hierarchical facet tree and fills in missing parent nodes.

    Args:
        buckets (List[Dict]): Buckets representing hierarchical data.
        field_filter (Optional[FieldFilter]): Field filter for selected nodes.

    Returns:
        HierarchicalBucket: The root of the hierarchical facet tree.
    """
    node_map = {}

    # Step 1: Parse buckets into nodes
    for bucket in buckets:
        key_parts = bucket["key"].split("/")
        node_path = "/".join(key_parts)
        node_type = (
            bucket["_type"]["buckets"][0]["key"] if bucket["_type"]["buckets"] else ""
        )

        node = HierarchicalAggregationBucket(
            key=key_parts[-1],
            doc_count=bucket["doc_count"],
            path=node_path,
            category_type=node_type,
            is_selected=(node_path in (field_filter.values if field_filter else [])),
        )
        node_map[node_path] = node

    # Step 2: Ensure all parent nodes exist
    for node_path in list(node_map.keys()):
        parts = node_path.split("/")
        for i in range(1, len(parts)):
            parent_path = "/".join(parts[:i])
            if parent_path not in node_map:
                parent_key = parts[i - 1]
                # Aggregate child data
                children_doc_count = sum(
                    child.doc_count
                    for path, child in node_map.items()
                    if path.startswith(parent_path + "/")
                    and len(path.split("/")) == len(parent_path.split("/")) + 1
                )
                child_types = {
                    child.category_type
                    for path, child in node_map.items()
                    if path.startswith(parent_path + "/")
                    and len(path.split("/")) == len(parent_path.split("/")) + 1
                }
                dummy_type = child_types.pop() if len(child_types) == 1 else "dummy"

                # Create and add the dummy node
                node_map[parent_path] = HierarchicalAggregationBucket(
                    key=parent_key,
                    doc_count=children_doc_count,
                    path=parent_path,
                    category_type=dummy_type,
                )

    # Step 3: Build the tree
    root = None
    for node_path, node in node_map.items():
        parent_path = "/".join(node_path.split("/")[:-1])
        if parent_path in node_map:
            node_map[parent_path].children.append(node)
        else:
            root = node

    return root


def format_aggregation_field(
    field_aggregation: Dict,
    filter_type: FilterType,
    is_filtered: bool = False,
    field_filter: Optional[FieldFilter] = None,
) -> FacetResponse:
    """
    Formats a field aggregation into a FacetResponse.

    Args:
        field_aggregation (Dict): The aggregation data for the field.
        filter_type (FilterType): Type of filter applied.
        is_filtered (bool): If the field is filtered.
        field_filter (Optional[FieldFilter]): Filter applied to the field.

    Returns:
        FacetResponse: A structured facet response for the field.
    """
    if filter_type == FilterType.term:
        term_buckets = [
            TermAggregationBucket(
                **bucket,
                is_selected=(
                    bucket["key"] in (field_filter.values if field_filter else [])
                ),
            )
            for bucket in field_aggregation.get("_values", {}).get("buckets", [])
        ]
        facet_data = TermFacetResponse(entries=term_buckets)

    elif filter_type == FilterType.numeric:
        stats = NumberStats(**field_aggregation.get("_values", {}))
        facet_data = NumericFacetResponse(stats=stats)

    elif filter_type == FilterType.hierarchical:
        hierarchical_tree = build_hierarchical_tree(
            field_aggregation.get("_values", {}).get("buckets", []),
            field_filter=field_filter,
        )
        facet_data = HierarchicalFacetResponse(root_bucket=hierarchical_tree)

    else:
        raise ValueError(f"Unsupported filter type: {filter_type}")

    return FacetResponse(
        field=field_aggregation.get("key", ""),
        facet_type=filter_type,
        is_filtered=is_filtered,
        doc_count=field_aggregation.get("_unique_docs", {}).get("doc_count", 0),
        data=facet_data,
    )


def extract_facets_from_aggregations(
    aggregations: Dict, request_filters: List[FieldFilter]
) -> List[FacetResponse]:
    """
    Extracts facets from search aggregations.

    Args:
        aggregations (Dict): Aggregations data.
        request_filters (List[FieldFilter]): Filters applied to the search.

    Returns:
        List[FacetResponse]: List of formatted facets.
    """
    facets = []

    def process_buckets(buckets, filter_type, is_filtered):
        for bucket in buckets:
            field_filter = (
                next((f for f in request_filters if f.field == bucket["key"]), None)
                if is_filtered
                else None
            )
            facets.append(
                format_aggregation_field(bucket, filter_type, is_filtered, field_filter)
            )

    # Process unselected fields
    unselected = aggregations.get("_unselected_fields", {})
    for filter_type in FilterType:
        process_buckets(
            unselected.get(f"_unselected_{filter_type.name}", {})
            .get("_names", {})
            .get("buckets", []),
            filter_type,
            is_filtered=False,
        )

    # Process selected fields
    for key, value in aggregations.items():
        for filter_type in FilterType:
            if key.startswith(f"_selected_{filter_type.name}_"):
                process_buckets(
                    value.get(key, {}).get("_names", {}).get("buckets", []),
                    filter_type,
                    is_filtered=True,
                )

    return facets
