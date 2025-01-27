from typing import List, Dict, Any

import streamlit as st
from st_ant_tree import st_ant_tree

from src.api.models.facets import FacetResponse, HierarchicalAggregationBucket
from src.api.models.filters import NumericRangeFilter, FieldFilter

SESSION_STATE_FACETS = "facets_state"
DEFAULT_FACETS_NUMBER = 10


def adjust_multiselect_style():
    """Enhance the readability of multiselect dropdowns."""
    st.markdown(
        """
        <style>
            .stMultiSelect [data-baseweb=select] span {
                max-width: 250px;
                font-size: 0.85rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def get_filters_facets() -> List[FieldFilter]:
    """Extract and construct filters from the session state."""
    filters = []

    for field_name, facet_info in st.session_state.get(
        SESSION_STATE_FACETS, {}
    ).items():
        if facet_info["type"] == "numeric" and facet_info["selected"]:
            filters.append(
                FieldFilter(
                    field=field_name,
                    filter_type="numeric",
                    ranges=[
                        NumericRangeFilter(
                            min=facet_info["range"]["selected"][0],
                            max=facet_info["range"]["selected"][1],
                        )
                    ],
                )
            )
        elif facet_info["type"] == "term":
            selected_values = [
                key
                for key, selected in facet_info["buckets"]["selected"].items()
                if selected
            ]
            if selected_values:
                filters.append(
                    FieldFilter(
                        field=field_name, filter_type="term", values=selected_values
                    )
                )
        elif facet_info["type"] == "hierarchical" and facet_info["selected_values"]:
            filters.append(
                FieldFilter(
                    field=field_name,
                    filter_type="hierarchical",
                    values=facet_info["selected_values"],
                )
            )

    return filters


def reset_filter(filter_key: str):
    """Reset a specific filter in the session state."""
    if filter_key in st.session_state[SESSION_STATE_FACETS]:
        del st.session_state[SESSION_STATE_FACETS][filter_key]
    else:
        field, value = filter_key.split(": ")
        st.session_state[SESSION_STATE_FACETS][field]["buckets"]["selected"][value] = (
            False
        )


def get_active_filter_tags() -> List[str]:
    """Retrieve active filter tags for display."""
    active_filters = []

    for field_name, facet_info in st.session_state.get(
        SESSION_STATE_FACETS, {}
    ).items():
        if facet_info["type"] == "number" and facet_info["selected"]:
            active_filters.append(field_name)
        elif facet_info["type"] == "term":
            active_filters.extend(
                f"{field_name}: {key}"
                for key, selected in facet_info["buckets"]["selected"].items()
                if selected
            )
        elif facet_info["type"] == "hierarchical" and facet_info["selected_values"]:
            active_filters.append(field_name)

    return active_filters


def display_filters_tags():
    """Display active filter tags and handle their removal."""
    adjust_multiselect_style()
    active_filters = get_active_filter_tags()

    if not active_filters:
        return

    selected_tags = st.multiselect(
        label="**Active Filters**",
        options=active_filters,
        default=active_filters,
        key="active_filter_tags",
    )

    removed_tags = set(active_filters) - set(selected_tags)
    if removed_tags:
        for removed_tag in removed_tags:
            reset_filter(removed_tag)
        st.rerun()


# Facet Rendering Functions
def render_number_facet(facet: FacetResponse):
    """Render a numeric range facet as a slider."""
    facet_state = st.session_state[SESSION_STATE_FACETS].setdefault(
        facet.field_name,
        {
            "type": "number",
            "range": {
                "min_max": (facet.data.stats.min, facet.data.stats.max),
                "selected": None,
            },
            "selected": False,
        },
    )

    min_value, max_value = facet.data.stats.min, facet.data.stats.max
    facet_state["range"]["min_max"] = (min_value, max_value)

    if min_value != max_value:
        if not facet_state["selected"]:
            facet_state["range"]["selected"] = (min_value, max_value)

        selected_range = st.slider(
            label=f"{facet.field.capitalize()} Range",
            min_value=min_value,
            max_value=max_value,
            value=facet_state["range"]["selected"],
            key=f"slider_{facet.field}",
            label_visibility="collapsed",
            step=5.0,
        )

        if selected_range != facet_state["range"]["selected"]:
            facet_state["range"]["selected"] = selected_range
            facet_state["selected"] = True
            st.rerun()


def render_term_facet(facet: FacetResponse):
    """Render a term facet with checkboxes."""
    facet_state = st.session_state[SESSION_STATE_FACETS].setdefault(
        facet.field, {"type": "term", "buckets": {"selected": {}}}
    )

    for bucket in facet.data.entries[:DEFAULT_FACETS_NUMBER]:
        label = f"{bucket.key} ({bucket.doc_count})"
        is_selected = facet_state["buckets"]["selected"].get(bucket.key, False)
        selected = st.checkbox(
            label=label, value=is_selected, key=f"{facet.field}_{bucket.key}"
        )

        if selected != is_selected:
            facet_state["buckets"]["selected"][bucket.key] = selected
            st.rerun()


def transform_to_tree(data: HierarchicalAggregationBucket) -> List[Dict[str, Any]]:
    """
    Transform hierarchical data into a tree structure suitable for rendering.

    Args:
        data (HierarchicalBucket): The hierarchical data containing keys, document counts, paths, and child nodes.

    Returns:
        List[Dict[str, Any]]: A list representing the tree structure with `value`, `title`, and `children`.
    """

    def process_node(node: HierarchicalAggregationBucket) -> Dict[str, Any]:
        """
        Process a single hierarchical node and its children recursively.

        Args:
            node (HierarchicalBucket): The current hierarchical node.

        Returns:
            Dict[str, Any]: A dictionary representing the processed node with its children.
        """
        return {
            "value": node.path,
            "title": f"{node.key} ({node.doc_count})",
            "children": [process_node(child) for child in node.children]
            if node.children
            else [],
        }

    return [process_node(data)]


def render_hierarchical_facet(facet: FacetResponse):
    """
    Render a hierarchical facet as an interactive tree component.

    Args:
        facet (FieldFacetsResponse): The facet data containing hierarchical entries to be rendered.
    """
    # Initialize or retrieve the state for this facet
    facet_state = st.session_state.setdefault(SESSION_STATE_FACETS, {}).setdefault(
        facet.field, {"type": "hierarchical", "selected_values": []}
    )

    # Convert the hierarchical data to a tree structure
    tree_data = transform_to_tree(facet.data.root_bucket)

    # Render the hierarchical tree with the st_ant_tree component
    selected_values = st_ant_tree(
        treeData=tree_data,
        defaultValue=facet_state["selected_values"],
        allowClear=True,
        showSearch=False,
    )

    # Update the session state if the selected values have changed
    if selected_values != facet_state["selected_values"]:
        facet_state["selected_values"] = selected_values
        st.rerun()


# Display Functions
def display_facets(facets: List[FacetResponse], exclude: List[str] = []):
    """Render facets with appropriate UI components."""
    st.session_state.setdefault(SESSION_STATE_FACETS, {})

    visible_facets = [facet for facet in facets if facet.field not in exclude]
    sorted_facets = sorted(
        visible_facets, key=lambda facet: (facet.facet_type, facet.field)
    )

    for facet in sorted_facets:
        with st.expander(label=f"**Filter by {facet.field}**", expanded=True):
            if facet.facet_type == "term":
                render_term_facet(facet)
            elif facet.facet_type == "numerical":
                render_number_facet(facet)
            elif facet.facet_type == "hierarchical":
                render_hierarchical_facet(facet)
