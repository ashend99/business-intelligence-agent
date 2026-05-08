"""
Module: ingestion/splitter.py
Date: 2026-05-08
"""
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

def split_documents(docs: list[Document],
                    chunk_size: int = 1000,
                    chunk_overlap: int = 150) -> list[Document]:
    """
    Split a list of Documents into smaller chunks using 
    RecursiveCharacterTextSplitter.
    Args:
        docs: List of Documents to split.
        chunk_size: Maximum number of characters in each chunk.
        chunk_overlap: Number of characters to overlap between chunks.
    Returns:
        List of split Documents with added 'chunk_id' in metadata.
    """
    # Return empty list immediately if there are no documents to split
    if not docs:
        return []

    # Validate chunk_size and chunk_overlap parameters to prevent infinite 
    # loops or errors
    if chunk_size <= 0:
        raise ValueError(f"chunk_size must be > 0, got {chunk_size}")    
    if chunk_overlap >= chunk_size:
        raise ValueError(f"chunk_overlap must be < chunk_size, "
                         f"got {chunk_overlap} >= {chunk_size}")
    
    # Filter out empty documents in a single pass (avoids O(n²) identity check)
    docs = [doc for doc in docs if doc.page_content.strip()]
    if not docs:
        return []
    
    # Split documents into smaller chunks using RecursiveCharacterTextSplitter.
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size,
                                              chunk_overlap=chunk_overlap)
    documents = splitter.split_documents(docs)

    # Add ordered chunk_id to each document's metadata for traceability.
    for i, doc in enumerate(documents):
        doc.metadata["chunk_id"] = i
    return documents

