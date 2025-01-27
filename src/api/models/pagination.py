import math
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class Pagination(BaseModel):
    """
    Model representing pagination logic, including validations and utility methods.
    """

    page: int = Field(
        default=1,
        ge=1,
        description="The current page number (1-based index).",
        examples=[1],
    )
    page_size: int = Field(
        default=10,
        ge=0,
        le=50,
        description=(
            "The number of hits to return per page. "
            "By default, you cannot page through more than 10,000 hits."
        ),
        examples=[5],
    )
    total_pages: Optional[int] = Field(
        default=None,
        ge=0,
        description="The total number of pages, computed based on total hits.",
        examples=[40],
    )

    def calculate_from(self) -> int:
        """
        Calculate the offset (starting index) for the current page in a paginated list.

        Returns:
            int: The offset for the current page.
        """
        return self.page_size * (self.page - 1)

    def calculate_total_pages(self, total_hits: int) -> int:
        """
        Calculate the total number of pages based on the total number of hits.

        Args:
            total_hits (int): The total number of items available.

        Returns:
            int: The total number of pages.
        """
        if self.page_size==0:
            return 0
        return math.ceil(total_hits / self.page_size)

    @model_validator(mode="after")
    def validate_result_window(self):
        """
        Validate that the result window does not exceed the maximum allowable range of 10,000.
        """
        size = self.page_size
        from_ = self.calculate_from()

        if size + from_ >= 10000:
            raise ValueError(
                f"from + size must be less than or equal to: [10000] but was [{size + from_}]"
            )

        return self
