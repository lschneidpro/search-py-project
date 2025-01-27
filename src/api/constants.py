from enum import Enum

class FilterType(Enum):
    hierarchical = "hierarchical"
    numeric = "number"
    term = "term"


class FilterTypeToESField(Enum):
    hierarchical = "pathFacetData"
    numeric = "numberFacetData"
    term = "termFacetData"