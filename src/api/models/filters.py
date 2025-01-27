from typing import List, Optional
from typing_extensions import Self

from pydantic import BaseModel, Field, model_validator

from src.api.constants import FilterType


### Request Models ###
class NumericRangeFilter(BaseModel):
    """Defines a range filter with minimum and maximum values."""

    min: Optional[float] = Field(
        None, description="Minimum value for the range filter."
    )
    max: Optional[float] = Field(
        None, description="Maximum value for the range filter."
    )

    @model_validator(mode="after")
    def validate_min_max(self) -> Self:
        """Ensure at least one of 'min' or 'max' is specified."""
        if self.min is None and self.max is None:
            raise ValueError("At least one of 'min' or 'max' must be specified.")
        return self


class FieldFilter(BaseModel):
    """Defines a filter for querying specific fields."""

    field: str = Field(..., description="The name of the field to apply the filter.")
    filter_type: FilterType = Field(
        ..., description="The type of filter: 'term', 'numeric', or 'hierarchical'."
    )
    values: Optional[List[str]] = Field(
        None, description="List of specific values for term or hierarchical filters."
    )
    ranges: Optional[List[NumericRangeFilter]] = Field(
        None, description="Range limits for numeric filters."
    )

    @model_validator(mode="after")
    def validate_filter_compatibility(self) -> Self:
        """Validates the filter parameters based on the filter type."""
        has_values = bool(self.values)
        has_ranges = bool(self.ranges)

        # Define validation rules
        filter_rules = {
            FilterType.term: (has_values, not has_ranges),
            FilterType.numeric: (not has_values, has_ranges),
            FilterType.hierarchical: (has_values, not has_ranges),
        }

        if self.filter_type not in filter_rules:
            raise ValueError(f"Unsupported filter type: {self.filter_type}")

        expected_values, expected_ranges = filter_rules[self.filter_type]
        if not expected_values:
            raise ValueError(
                f"For filter type '{self.filter_type.value}', 'values' must be specified."
            )
        if not expected_ranges:
            raise ValueError(
                f"For filter type '{self.filter_type.value}', 'ranges' cannot be specified."
            )
        return self

    class Config:
        extra = "forbid"
