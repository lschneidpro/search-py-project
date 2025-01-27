from typing import Dict, List, Optional

from src.api.models.facets import FieldFilter
from src.api.constants import FilterTypeToESField, FilterType
from src.api.service.builders_filters import construct_nested_filters


def _build_terms_aggregation(
    field: str,
    size: int,
    include: Optional[List[str]] = None,
    exclude: Optional[List[str]] = None,
) -> Dict:
    """
    Builds a terms aggregation with optional include/exclude filters.

    Args:
        field (str): The field for the terms aggregation.
        size (int): The maximum number of buckets to include.
        include (Optional[List[str]]): Fields to include.
        exclude (Optional[List[str]]): Fields to exclude.

    Returns:
        Dict: Terms aggregation query.
    """
    terms_aggregation = {"terms": {"field": field, "size": size}}
    if include:
        terms_aggregation["terms"]["include"] = include
    if exclude:
        terms_aggregation["terms"]["exclude"] = exclude
    return terms_aggregation


def _build_reverse_nested_cardinality_aggregation(field: str) -> Dict:
    """
    Builds a reverse nested cardinality aggregation.

    Args:
        field (str): The field to calculate cardinality on.

    Returns:
        Dict: Reverse nested cardinality aggregation query.
    """
    return {
        "_unique_docs": {
            "reverse_nested": {},
            "aggs": {
                "_cardinality_docs": {
                    "cardinality": {"field": field, "precision_threshold": 5000}
                }
            },
        }
    }


def _build_sub_aggregation(filter_type: FilterType, size: int) -> Dict:
    """
    Constructs a sub-aggregation for a given filter type.

    Args:
        filter_type (FilterType): The type of filter (e.g., 'term', 'number', 'hierarchical').
        size (int): The maximum number of buckets to include.

    Returns:
        Dict: Sub-aggregation query.
    """
    base_path = FilterTypeToESField[filter_type.name].value

    if filter_type == FilterType.term:
        return {"_values": _build_terms_aggregation(f"{base_path}.value", size)}
    if filter_type == FilterType.hierarchical:
        return {
            "_values": {
                **_build_terms_aggregation(f"{base_path}.value", size),
                "aggs": {"_type": _build_terms_aggregation(f"{base_path}.type", 1)},
            }
        }
    if filter_type == FilterType.numeric:
        return {"_values": {"stats": {"field": f"{base_path}.value"}}}

    raise ValueError(f"Unsupported filter type: {filter_type.name}")


def _build_field_aggregation(
    filter_type: FilterType,
    include: Optional[List[str]] = None,
    exclude: Optional[List[str]] = None,
    size: int = 1000,  # TODO Set specific size
) -> Dict:
    """
    Builds an Elasticsearch aggregation for a specific field type.

    Args:
        filter_type (FilterType): The type of field.
        include (Optional[List[str]]): List of fields to include.
        exclude (Optional[List[str]]): List of fields to exclude.
        size (int): Maximum number of buckets to include.

    Returns:
        Dict: Aggregation query.
    """
    base_path = FilterTypeToESField[filter_type.name].value
    terms_agg = _build_terms_aggregation(f"{base_path}.name", size, include, exclude)
    cardinality_agg = _build_reverse_nested_cardinality_aggregation("id.keyword")

    return {
        "nested": {"path": base_path},
        "aggs": {
            "_names": {
                **terms_agg,
                "aggs": {
                    **cardinality_agg,
                    **_build_sub_aggregation(filter_type, size),
                },
            }
        },
    }


def _build_selected_aggregation(
    field_filter: FieldFilter, excluded_filters: List[FieldFilter]
) -> Dict:
    """
    Builds an aggregation for a field with selected filters, excluding certain filters.

    Args:
        field_filter (FieldFilter): The field filter to build the aggregation for.
        excluded_filters (List[FieldFilter]): Filters to exclude.

    Returns:
        Dict: Aggregation query for the selected field.
    """
    excluded_filter_query = construct_nested_filters(filters=excluded_filters)
    return {
        "filter": excluded_filter_query,
        "aggs": {
            f"_selected_{field_filter.filter_type.name}_{field_filter.field}": _build_field_aggregation(
                filter_type=field_filter.filter_type,
                include=[field_filter.field],
            )
        },
    }


def build_selected_field_aggregations(filters: List[FieldFilter]) -> Dict:
    """
    Constructs aggregations for selected filters.

    Args:
        filters (List[FieldFilter]): List of field filters.

    Returns:
        Dict: Aggregation queries for selected fields.
    """
    return {
        f"_selected_{field.filter_type.name}_{field.field}": _build_selected_aggregation(
            field_filter=field,
            excluded_filters=[f for f in filters if f != field],
        )
        for field in filters
    }


def build_unselected_field_aggregations(filters: List[FieldFilter] = []) -> Dict:
    """
    Constructs aggregations for fields without selected filters.

    Args:
        filters (List[FieldFilter]): List of active filters.

    Returns:
        Dict: Aggregation queries for unselected fields.
    """
    excluded_fields = {
        filter_type: [f.field for f in filters if f.filter_type == filter_type]
        for filter_type in FilterType
    }

    return {
        "_unselected_fields": {
            "filter": construct_nested_filters(filters=filters),
            "aggs": {
                f"_unselected_{filter_type.name}": _build_field_aggregation(
                    filter_type=filter_type,
                    exclude=excluded_fields[filter_type],
                )
                for filter_type in FilterType
            },
        }
    }
