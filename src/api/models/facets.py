from typing import List, Optional, Union
from typing_extensions import Self

from pydantic import BaseModel, Field, model_validator

from src.api.models.filters import FieldFilter
from src.api.constants import FilterType


### Request Models ###
class FacetsRequest(BaseModel):
    """
    Model to configure facets for filtering and bucket creation.
    """

    enabled: bool = Field(
        default=False, description="Indicates whether facets are enabled."
    )
    filters: Optional[List[FieldFilter]] = Field(
        default=None, description="A list of filters to apply to specific fields."
    )

    class Config:
        """
        Configuration options for the Pydantic model.
        """

        extra = "forbid"


### Response Models ###
class TermAggregationBucket(BaseModel):
    """Bucket representing a term-based aggregation."""

    key: str = Field(..., description="Key representing a specific value or range.")
    id: Optional[str] = Field(
        None, description="Optional unique identifier for the bucket."
    )
    doc_count: int = Field(..., ge=0, description="Count of documents in this bucket.")
    is_selected: bool = Field(False, description="Indicates if this bucket is selected.")


class HierarchicalAggregationBucket(BaseModel):
    """
    Bucket representing a hierarchical aggregation.
    """

    key: str = Field(..., description="Key representing a specific value or range.")
    id: Optional[str] = Field(
        None, description="Optional unique identifier for the bucket."
    )
    doc_count: int = Field(..., ge=0, description="Count of documents in this bucket.")
    is_selected: bool = Field(
        False, description="Indicates whether this bucket is selected."
    )
    path: str = Field(..., description="Full hierarchical path of the bucket.")
    category_type: str = Field(
        ..., description="The type of the hierarchical category."
    )
    # level: int = Field(..., ge=1, description="Level of this bucket in the hierarchy.")
    children: List["HierarchicalAggregationBucket"] = Field(
        default_factory=list,
        description="List of child buckets representing sub-levels in the hierarchy.",
    )


class VariableHistogramBucket(BaseModel):
    """Bucket representing a range in a variable-width histogram."""

    min: float = Field(..., description="Lower bound of the bucket range.")
    max: float = Field(..., description="Upper bound of the bucket range.")
    doc_count: int = Field(..., ge=0, description="Count of documents in this bucket.")


class NumberStats(BaseModel):
    """Statistics for a numeric range."""

    min: float = Field(..., description="Minimum observed value in the range.")
    max: float = Field(..., description="Maximum observed value in the range.")
    avg: float = Field(..., description="Average value observed in the range.")


# Facet-Specific Models
class TermFacetResponse(BaseModel):
    """Data for term-based facets."""

    entries: List[TermAggregationBucket] = Field(
        ..., description="Buckets for term-based facets."
    )


class NumericFacetResponse(BaseModel):
    """Data for numeric facets."""

    # entries: List[VariableHistogramBucket] = Field(
    #     ..., description="Buckets for numeric facets."
    # )
    stats: NumberStats = Field(..., description="Statistics for numeric facets.")


class HierarchicalFacetResponse(BaseModel):
    """Data for hierarchical facets."""

    root_bucket: HierarchicalAggregationBucket = Field(
        ..., description="The root bucket for hierarchical facets."
    )


# Main Facets Response
class FacetResponse(BaseModel):
    """Represents a unified response model for facets."""

    field: str = Field(..., description="The field name associated with the facet.")
    facet_type: FilterType = Field(
        ..., description="The type of the facet: 'term', 'numeric', or 'hierarchical'."
    )
    is_filtered: bool = Field(
        False, description="Indicates if the facet is currently filtered."
    )
    doc_count: int = Field(
        ..., ge=0, description="Total document count for this facet."
    )
    data: Union[TermFacetResponse, NumericFacetResponse, HierarchicalFacetResponse] = (
        Field(..., description="The specific facet data.")
    )

    @model_validator(mode="after")
    def validate_facet_data(self) -> Self:
        """Ensures the data matches the expected structure for the given facet type."""
        expected_models = {
            FilterType.term: TermFacetResponse,
            FilterType.numeric: NumericFacetResponse,
            FilterType.hierarchical: HierarchicalFacetResponse,
        }

        expected_model = expected_models.get(self.facet_type)
        if expected_model and not isinstance(self.data, expected_model):
            raise ValueError(
                f"Expected data for facet type '{self.facet_type.value}' must be of type {expected_model.__name__}."
            )

        return self

    class Config:
        """
        Configuration options for the Pydantic model.
        """

        use_enum_values = True
        extra = "forbid"
