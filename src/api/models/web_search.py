from typing import Optional, Any, List

from pydantic import BaseModel, Field

from src.api.models.facets import FacetsRequest, FacetResponse
from src.api.models.filters import FieldFilter
from src.api.models.pagination import Pagination


class WebSearchRequest(BaseModel):
    """
    Model representing a web search request with query, filters, facets, pagination, and additional preferences.
    """

    q: Optional[str] = Field(
        None, description="User-provided search query string.", example="example query"
    )
    pagination: Pagination = Field(
        default=Pagination(),
        description="Pagination parameters for the search results.",
    )
    pre_filters: Optional[List[FieldFilter]] = Field(
        None,
        description="Filters to apply on specific fields before facet aggregations.",
        example=[
            {
                "field_name": "category",
                "type": "term",
                "values": ["Electronics", "Books"],
            },
            {
                "field_name": "price",
                "type": "number",
                "ranges": [{"min": 10, "max": 100}],
            },
        ],
    )
    facets: Optional[FacetsRequest] = Field(
        None,
        description="Facet filters to refine search results based on aggregations.",
        examples=[
            {
                "enabled": True,
                "filters": [
                    {
                        "field_name": "color",
                        "type": "term",
                        "values": ["Blue", "Black"],
                    },
                    {
                        "field_name": "price",
                        "type": "number",
                        "ranges": [{"min": 10, "max": 100}, {"min": 200, "max": 300}],
                    },
                    {
                        "field_name": "type",
                        "type": "hierarchical",
                        "values": [
                            "Type/Machine/Forwarder",
                            "Type/Machine/Crawler Pipe Layer",
                        ],
                    },
                ],
            }
        ],
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
    # sort_by: Optional[str] = Field(
    #     default=None,
    #     description="Field to sort the search results by (e.g., 'price', 'date').",
    #     example="price"
    # )
    # sort_order: Optional[str] = Field(
    #     default="desc",
    #     description="Sort order for the search results: 'asc' for ascending or 'desc' for descending.",
    #     regex="^(asc|desc)$",
    #     example="desc"
    # )
    # include_highlights: Optional[bool] = Field(
    #     default=False,
    #     description="Whether to include highlighted snippets in the search results.",
    #     example=True
    # )

    class Config:
        extra = "forbid"


class WebSearchResponse(BaseModel):
    """
    Represents the structured response of a web search.

    Attributes:
        took_in_millis (int): Time taken to execute the search, in milliseconds.
        total_hits (int): Total number of hits for the search query.
        pagination (Pagination): Pagination details.
        hits (Optional[Any]): The actual search results.
        facets (Optional[List[FieldFacetsResponse]]): Facet results, if applicable.
    """

    took_in_millis: int = Field(
        0, description="Time taken in milliseconds.", example=45
    )
    total_hits: int = Field(0, description="Total number of hits.")
    pagination: Optional[Pagination] = Field(
        None,
        description="Pagination details for the results.",
        example={"page": 1, "page_size": 5, "total_pages": 4},
    )
    hits: Optional[Any] = Field(None, description="Search result hits.")
    facets: Optional[List[FacetResponse]] = Field(
        None,
        description="Facet results returned from the search, if applicable.",
        example=[
            {
                "field_name": "exterior_color",
                "type": "term",
                "is_filtered": False,
                "doc_count": 1355,
                "data": {
                    "entries": [
                        {
                            "key": "Red",
                            "id": None,
                            "doc_count": 283,
                            "is_selected": False,
                        },
                        {
                            "key": "Blue",
                            "id": None,
                            "doc_count": 272,
                            "is_selected": False,
                        },
                    ]
                },
            },
            {
                "field_name": "price",
                "type": "number",
                "is_filtered": False,
                "doc_count": 1355,
                "data": {
                    "stats": {"min": 1000.0, "max": 10000.0, "avg": 5726.42},
                },
            },
            {
                "field_name": "type",
                "type": "hierarchical",
                "is_filtered": False,
                "doc_count": 1355,
                "data": {
                    "entries": {
                        "key": "Type",
                        "doc_count": 1355,
                        "path": "Type",
                        "type": "root",
                        "children": [
                            {
                                "key": "Vehicle",
                                "doc_count": 1353,
                                "path": "Type/Vehicle",
                                "type": "type",
                                "children": [
                                    {
                                        "key": "SUV",
                                        "doc_count": 350,
                                        "path": "Type/Vehicle/SUV",
                                        "type": "category",
                                        "children": [],
                                    }
                                ],
                            },
                            {
                                "key": "Machine",
                                "doc_count": 2,
                                "path": "Type/Machine",
                                "type": "type",
                                "children": [
                                    {
                                        "key": "Harvester",
                                        "doc_count": 1,
                                        "path": "Type/Machine/Harvester",
                                        "type": "category",
                                        "children": [],
                                    }
                                ],
                            },
                        ],
                    }
                },
            },
        ],
    )

    class Config:
        extra = "forbid"
        json_schema_extra = {
            "example": {
                "took_in_millis": 45,
                "total_hits": 1355,
                "pagination": {"page": 1, "page_size": 5, "total_pages": 4},
                "hits": [{"id": "1", "title": "Example result"}],
                "facets": [
                    {
                        "field_name": "exterior_color",
                        "type": "term",
                        "is_filtered": False,
                        "doc_count": 1355,
                        "data": {
                            "entries": [
                                {"key": "Red", "doc_count": 283, "is_selected": False},
                                {"key": "Blue", "doc_count": 272, "is_selected": False},
                            ]
                        },
                    }
                ],
            }
        }
