from typing import List, Tuple, Optional

import streamlit as st
from streamlit_searchbox import st_searchbox

from src.api.models.web_suggest import WebSuggestRequest
from src.api.api.suggest import search


SESSION_STATE_SEARCH = "searchbox_state"

def get_suggestion(search_term: str) -> List[Tuple[str, str]]:
    """
    Mock search function to simulate search results based on a search term.

    Args:
        search_term (str): The search term input by the user.

    Returns:
        List[Tuple[str, str]]: A list of tuples containing search term and suggestions.
    """
    # Validate the input length
    if len(search_term) < 2:
        return [(search_term, search_term)]

    # Split the search term into individual words
    terms = search_term.split()

    # Determine the query term (last word) and context tags (all but the last word)
    q = terms[-1]
    context_tags: Optional[List[str]] = terms[:-1] if len(terms) > 1 else None

    # Create the request object
    request = WebSuggestRequest(context_tags=context_tags, q=q)

    # Perform the search
    resp = search(request=request)

    # Extract suggestions from the response
    print(context_tags)

    # Generate suggestions with context tags if available
    if context_tags:
        context_str = ' '.join(context_tags)
        suggestions = [
            (f"{context_str} {s.key}", f"{context_str} {s.key}")
            for s in resp.suggestions
        ]
    else:
        suggestions = [(s.key, s.key) for s in resp.suggestions]

    # Combine the original search term with the suggestions
    return [(search_term, search_term)] + suggestions


def get_searchbox_query() -> str:
    """
    Retrieves the current query stored in the session state for the search box.

    Returns:
        str: The current search query, or None if not set.
    """
    return st.session_state.get(SESSION_STATE_SEARCH)


@st.fragment
def display_searchbox():
    """
    Displays the search box component with debounce and placeholder settings.
    If the search query changes, it clears the session state and triggers a rerun.
    """

    previous_state = st.session_state.setdefault(SESSION_STATE_SEARCH, None)
    # Render the search box and capture the query
    current_query = st_searchbox(
        search_function=get_suggestion,
        placeholder="Enter your search query",
        rerun_scope="fragment",
        debounce=300,
        style_overrides={"clear": {"clearable": "always"}},
        default=previous_state,
    )

    if current_query:
        if current_query != previous_state:
            st.session_state[SESSION_STATE_SEARCH] = current_query
            st.rerun()
