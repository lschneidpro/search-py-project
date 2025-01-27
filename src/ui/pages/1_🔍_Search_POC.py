from typing import List, Tuple

import streamlit as st

from src.api.models.web_search import WebSearchRequest, FacetsRequest, Pagination
from src.api.api import search

from src.ui.components import facets as st_facets
from src.ui.components import menu as st_menu
from src.ui.components import search_bar as st_searchbar


# Mock search function for demonstration purposes
def dummy_search_function(searchterm: str) -> List[Tuple[str, str]]:
    return [(searchterm, searchterm), ("1", "Sample 1"), ("2", "Sample 2")]


# Main App Logic
st.set_page_config(page_title="Search Demo", page_icon="🔍")
st.title("Search Demo")


st_searchbar.display_searchbox()

q_user = st_searchbar.get_searchbox_query()

request_categories = WebSearchRequest(
    q=q_user,
    pagination=Pagination(page=1, page_size=0),
    facets=FacetsRequest(enabled=True),
)
response_categories = search.search(request=request_categories)

with st.sidebar:
    type_facets = next(
        (f for f in response_categories.facets if f.field == "type"), None
    )
    if type_facets:
        st_menu.display_hierarchical_menu(type_facets.data.root_bucket)
        st.divider()


if q_user or st_menu.get_filter_hierarchical_menu():
    category_filter = st_menu.get_filter_hierarchical_menu()
    facets_filters = st_facets.get_filters_facets()

    search_request = WebSearchRequest(
        q=q_user,
        pagination=Pagination(page=1, page_size=10),
        pre_filters=[category_filter] if category_filter else None,
        facets=FacetsRequest(enabled=True, filters=facets_filters),
    )
    search_response = search.search(request=search_request)

    if search_response.hits:
        st.info(f"Found {search_response.total_hits} results.")
        for hit in search_response.hits:
            st.write(hit["_source"])

        if search_response.facets:
            with st.sidebar:
                st_facets.display_filters_tags()
                st_facets.display_facets(search_response.facets, exclude=["type"])
    else:
        st.write("No results found.")
