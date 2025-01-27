from typing import Dict, List, Optional
from src.api.models.filters import FieldFilter, NumericRangeFilter
from src.api.constants import FilterTypeToESField, FilterType


def construct_nested_filters(filters: List[FieldFilter]) -> Dict:
    """
    Constructs a nested Elasticsearch query for the given filters.

    Args:
        filters (List[FieldFilter]): A list of filters to apply.

    Returns:
        Dict: The nested Elasticsearch query.
    """
    if not filters:
        return {"match_all": {}}

    valid_filters = [
        _build_filter_for_field(field_filter)
        for field_filter in filters
        if _build_filter_for_field(field_filter) is not None
    ]

    return {"bool": {"filter": valid_filters}}


def _build_filter_for_field(field_filter: FieldFilter) -> Optional[Dict]:
    """
    Converts a single field filter into a nested Elasticsearch filter.

    Args:
        field_filter (FieldFilter): The field filter object.

    Returns:
        Optional[Dict]: A nested filter query, or None if the filter is invalid.
    """
    base_path = FilterTypeToESField[field_filter.filter_type.name].value
    if not base_path:
        return None

    filter_conditions = [{"term": {f"{base_path}.name": field_filter.field}}]

    if (
        field_filter.filter_type in {FilterType.term, FilterType.hierarchical}
        and field_filter.values
    ):
        filter_conditions.append({"terms": {f"{base_path}.value": field_filter.values}})
    elif field_filter.filter_type == FilterType.numeric and field_filter.ranges:
        range_filter = _build_range_filters(base_path, field_filter.ranges)
        if range_filter:
            filter_conditions.append(range_filter)

    return {
        "nested": {
            "_name": f"filter__{field_filter.field}",
            "path": base_path,
            "query": {"bool": {"filter": filter_conditions}},
        }
    }


def _build_range_filters(
    base_path: str, ranges: List[NumericRangeFilter]
) -> Optional[Dict]:
    """
    Constructs a range filter for numeric fields.

    Args:
        base_path (str): The Elasticsearch path for numeric data.
        ranges (List[RangeFilter]): A list of range filter objects.

    Returns:
        Optional[Dict]: A range filter query, or None if no valid ranges are provided.
    """
    range_conditions = [
        {
            "range": {
                f"{base_path}.value": {
                    "gte": range_.min,
                    "lte": range_.max,
                }
            }
        }
        for range_ in ranges
        if range_.min is not None or range_.max is not None
    ]

    if not range_conditions:
        return None

    return {"bool": {"should": range_conditions}}
