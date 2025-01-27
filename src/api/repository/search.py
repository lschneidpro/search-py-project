from typing import Optional
from pprint import pprint

from elasticsearch import NotFoundError, Elasticsearch
import streamlit as st

from src.api.config import HOST


class SearchRepo:
    """
    A class to interact with an Elasticsearch instance for index management,
    document insertion, reindexing, and querying.
    """

    def __init__(self):
        """
        Initializes the Search class and connects to Elasticsearch.
        Prints client information on successful connection.
        """
        try:
            self.es = Elasticsearch(hosts=HOST)
            client_info = self.es.info()
            print("Connected to Elasticsearch!")
            pprint(client_info.body)
        except Exception as e:
            print(f"Failed to connect to Elasticsearch: {e}")

    def create_index(self, index: str, mappings: dict = None, settings: dict = None):
        """
        Creates a new index in Elasticsearch, deleting any existing index with the same name.
        """
        self.es.indices.delete(index=index, ignore_unavailable=True)
        response = self.es.indices.create(
            index=index, mappings=mappings, settings=settings
        )
        print(f"Index '{index}' created successfully.")
        return response

    def insert_document(self, index: str, document: dict) -> dict:
        """
        Inserts a single document into a specified index.
        """
        response = self.es.index(index=index, document=document)
        print(f"Document inserted into '{index}' with ID {response['_id']}")
        return response

    def insert_documents(
        self, index: str, documents: list, pipeline: Optional[str] = None
    ) -> dict:
        """
        Inserts multiple documents into a specified index using bulk operations.
        """
        operations = []
        for document in documents:
            operations.append({"index": {"_index": index}})
            operations.append(document)

        response = self.es.bulk(operations=operations, pipeline=pipeline)

        print(f"{len(documents)} documents inserted into '{index}'")
        return response

    def reindex(
        self,
        index: str,
        documents: list,
        mappings: dict = None,
        settings: dict = None,
        pipeline: Optional[str] = None,
    ) -> dict:
        """
        Recreates an index with the specified mappings and settings, then inserts the provided documents.
        """
        self.create_index(index, mappings=mappings, settings=settings)
        return self.insert_documents(index, documents, pipeline=pipeline)

    def search(self, index: str, **query_args) -> dict:
        """
        Searches for documents in the specified index with the given query arguments.
        """

        response = self.es.search(index=index, **query_args)
        took = response["took"]
        print(f"Search results from '{index}' retrieved successfully in {took} ms.")
        return response

    def retrieve_document(self, index: str, id: str) -> dict:
        """
        Retrieves a document from the specified index by its ID.
        """
        try:
            document = self.es.get(index=index, id=id)
            print(f"Document with ID '{id}' retrieved from '{index}'")
            return document
        except NotFoundError:
            print(f"Document with ID '{id}' not found in '{index}'")


@st.cache_resource(ttl=3600)
def get_search_client() -> SearchRepo:
    """
    Initializes and caches the search repository client with a 1-hour TTL.

    Returns:
        SearchRepo: The initialized search repository client.
    """
    return SearchRepo()
