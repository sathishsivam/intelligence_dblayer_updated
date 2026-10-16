from ...build_metadata import retriever


def retrieve_documents(query: str):
    """
    Retrieve candidate tables from FAISS.
    """
    return retriever.invoke(query)
