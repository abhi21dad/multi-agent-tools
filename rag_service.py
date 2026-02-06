"""
RAG Service - Document Processing and Retrieval
Handles PDF uploads, chunking, embedding, and similarity search
"""

import os
from typing import List, Optional
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from dotenv import load_dotenv

load_dotenv()

# Directory to store ChromaDB data
CHROMA_PERSIST_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
DOCUMENTS_DIR = os.path.join(os.path.dirname(__file__), "uploaded_docs")

# Create directories if they don't exist
os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
os.makedirs(DOCUMENTS_DIR, exist_ok=True)

# Initialize embeddings
embeddings = OpenAIEmbeddings()

# Initialize or load ChromaDB vector store
vectorstore = Chroma(
    collection_name="pdf_documents",
    embedding_function=embeddings,
    persist_directory=CHROMA_PERSIST_DIR
)


def process_pdf(file_path: str, filename: str) -> dict:
    """
    Process a PDF file: load, chunk, and add to vector store.
    
    Args:
        file_path: Path to the PDF file
        filename: Original filename for metadata
        
    Returns:
        dict with status and number of chunks processed
    """
    try:
        # Load PDF
        loader = PyPDFLoader(file_path)
        documents = loader.load()
        
        if not documents:
            return {"success": False, "error": "No content extracted from PDF"}
        
        # Add filename to metadata
        for doc in documents:
            doc.metadata["source_filename"] = filename
        
        # Split into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        chunks = text_splitter.split_documents(documents)
        
        # Add to vector store
        vectorstore.add_documents(chunks)
        
        return {
            "success": True,
            "filename": filename,
            "pages": len(documents),
            "chunks": len(chunks),
            "message": f"Successfully processed '{filename}': {len(documents)} pages, {len(chunks)} chunks"
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def search_documents(query: str, k: int = 5) -> List[dict]:
    """
    Search the vector store for relevant documents.
    
    Args:
        query: Search query
        k: Number of results to return
        
    Returns:
        List of matching document chunks with content and metadata
    """
    try:
        results = vectorstore.similarity_search_with_relevance_scores(query, k=k)
        
        formatted_results = []
        for doc, score in results:
            formatted_results.append({
                "content": doc.page_content,
                "source": doc.metadata.get("source_filename", "Unknown"),
                "page": doc.metadata.get("page", "N/A"),
                "relevance_score": round(score, 3)
            })
        
        return formatted_results
        
    except Exception as e:
        return [{"error": str(e)}]


def get_context_for_query(query: str, k: int = 3) -> str:
    """
    Get formatted context string for RAG.
    Used by the chatbot to augment prompts with document context.
    
    Args:
        query: User's question
        k: Number of chunks to include
        
    Returns:
        Formatted context string
    """
    results = search_documents(query, k=k)
    
    if not results or (len(results) == 1 and "error" in results[0]):
        return ""
    
    context_parts = []
    for i, result in enumerate(results, 1):
        source = result.get("source", "Unknown")
        page = result.get("page", "N/A")
        content = result.get("content", "")
        context_parts.append(f"[Source: {source}, Page {page}]\n{content}")
    
    return "\n\n---\n\n".join(context_parts)


def list_uploaded_documents() -> List[str]:
    """
    List all documents that have been uploaded and processed.
    
    Returns:
        List of document filenames
    """
    try:
        # Get unique source filenames from the vectorstore
        collection = vectorstore._collection
        if collection.count() == 0:
            return []
        
        # Get all metadata and extract unique filenames
        all_data = collection.get(include=["metadatas"])
        filenames = set()
        for metadata in all_data.get("metadatas", []):
            if metadata and "source_filename" in metadata:
                filenames.add(metadata["source_filename"])
        
        return sorted(list(filenames))
        
    except Exception as e:
        print(f"Error listing documents: {e}")
        return []


def clear_all_documents() -> dict:
    """
    Clear all documents from the vector store.
    
    Returns:
        dict with status
    """
    global vectorstore
    try:
        # Delete the collection and recreate
        vectorstore.delete_collection()
        vectorstore = Chroma(
            collection_name="pdf_documents",
            embedding_function=embeddings,
            persist_directory=CHROMA_PERSIST_DIR
        )
        return {"success": True, "message": "All documents cleared"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# For testing
if __name__ == "__main__":
    print("RAG Service initialized")
    print(f"ChromaDB directory: {CHROMA_PERSIST_DIR}")
    print(f"Documents directory: {DOCUMENTS_DIR}")
    docs = list_uploaded_documents()
    print(f"Uploaded documents: {docs}")
