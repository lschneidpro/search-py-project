import time

import streamlit as st


# Utility Functions
def clear_session():
    """Clear all session state keys."""
    for key in st.session_state.keys():
        del st.session_state[key]



def timed_function(func):
    """Decorator to print the start, end, and elapsed time of a function."""

    def wrapper(*args, **kwargs):
        start_time = time.time()
        print(
            f"Starting '{func.__name__}' at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))}"
        )

        # Run the actual function
        result = func(*args, **kwargs)

        end_time = time.time()
        elapsed_time = end_time - start_time
        print(
            f"Finished '{func.__name__}' at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time))}"
        )
        print(f"Elapsed time for '{func.__name__}': {elapsed_time:.2f} seconds\n")

        return result

    return wrapper

def number_of_search_terms_from(query_string):
    """
    Returns the number of terms in the query string using space as a separator
    :param query_string: String containing zero or more words separated by spaces
    :return: Number with the amount of found terms
    """
    return len(query_string.split())