from typing import Optional

import streamlit as st
import streamlit_antd_components as sac

from src.api.models.facets import HierarchicalAggregationBucket
from src.api.models.filters import FieldFilter
from src.ui.components import facets as facets
from src.utils import clear_session

SESSION_STATE_MENU = "menu_state"

def get_filter_hierarchical_menu() -> Optional[FieldFilter]:
    """
    Retrieve the selected hierarchical category from the session state.

    Returns:
        FieldFilter | None: A FieldFilter object representing the selected category,
                            or None if no category is selected.
    """
    selected_path = st.session_state.get(SESSION_STATE_MENU, {}).get("selected_path")

    if selected_path:
        return FieldFilter(
            field="type", filter_type="hierarchical", values=[selected_path]
        )
    return None

def build_hierarchical_menu_item(data: HierarchicalAggregationBucket) -> sac.MenuItem:
    """
    Recursively build hierarchical menu items for a given data node.

    Args:
        data (HierarchicalBucket): A hierarchical bucket representing a category.

    Returns:
        sac.MenuItem: A Streamlit Ant Design MenuItem representing the given category.
    """
    # Base case: If no children, return a MenuItem with an empty children list
    label = f"{data.key} ({data.doc_count})"
    if not data.children:
        return sac.MenuItem(label=label)

    # Recursively build children
    children = [build_hierarchical_menu_item(child) for child in data.children]

    # Return the MenuItem with children
    return sac.MenuItem(label=label, children=children)

def find_label_and_path(menu_items, target_index, current_path=""):
    if not menu_items:  # Check if menu_items is None or empty
        return None

    for item in menu_items:
        # Check if the current item is a MenuItem or a dictionary
        if isinstance(item, dict):
            item_children = item.get("children", [])
            item_key = item.get("key")
            item_label = item.get("label")
        else:
            item_children = item.children or []
            item_key = getattr(item, "key", None)
            item_label = item.label

        # Clean the label by removing the parenthesis and their content
        clean_label = item_label.split(" (")[0]

        # Update the path
        path = f"{current_path}/{clean_label}" if current_path else clean_label

        # If the key matches the target index, return the cleaned label and path
        if item_key == target_index:
            return {"label": clean_label, "path": path}

        # Recursively search in the children, if any
        if item_children:  # Add this check to ensure children is iterable
            result = find_label_and_path(item_children, target_index, path)
            if result:
                return result

    return None  # Return None if the target index is not found

def display_hierarchical_menu(hierarchical_categories: HierarchicalAggregationBucket):
    """
    Display a hierarchical category tree component in Streamlit for category selection.

    Args:
        hierarchical_categories (HierarchicalBucket): The root category containing all hierarchical data.
    """
    # Initialize session state for the menu
    menu_state = st.session_state.setdefault(
        SESSION_STATE_MENU, {"index": 0, "selected_label": None, "selected_path": None}
    )

    # Build menu items from hierarchical data
    root_menu_item = build_hierarchical_menu_item(hierarchical_categories)
    menu_items = [sac.MenuItem("Home", icon="house-fill"), root_menu_item]

    st.write("**Categories**")
    selected_index = sac.menu(
        items=menu_items,
        index=menu_state["index"],
        variant="light",
        open_index=[1],
        return_index=True,
        open_all=False,
    )

    # Handle menu item selection changes
    if selected_index != menu_state["index"]:
        if selected_index == 0:  # If "Home" is selected, clear the session state
            clear_session()
            st.rerun()
        else:
            # Find the selected item's label and path
            selected_item = find_label_and_path(menu_items, selected_index)
            st.session_state[SESSION_STATE_MENU] = {
                "index": selected_index,
                "selected_label": selected_item["label"],
                "selected_path": selected_item["path"],
            }
            # Clear facets state when a new menu item is selected
            st.session_state.pop(facets.SESSION_STATE_FACETS, None)
            st.rerun()
