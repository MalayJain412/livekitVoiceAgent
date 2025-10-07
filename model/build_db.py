# build_db.py - Vector store builder for TXT knowledge base
import os
from dotenv import load_dotenv
from typing import List

# LangChain Imports
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Configuration
CHROMA_DB_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")
DATA_FILE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "triotech_knowledge.txt")   # <-- Triotech knowledge base
MAX_CHUNK_SIZE = 1500               # max characters per chunk
CHUNK_OVERLAP = 200                 # overlap between chunks

def load_txt_file() -> str:
    """Load and clean the TXT data file"""
    print(f"Loading TXT data from {DATA_FILE_PATH}...")
    try:
        with open(DATA_FILE_PATH, 'r', encoding='utf-8') as f:
            text = f.read()
        return text
    except Exception as e:
        print(f"Error loading TXT file: {e}")
        exit(1)

def create_documents_from_text(text: str) -> List[Document]:
    """
    Convert raw text into LangChain Documents with metadata
    """
    metadata = {"source": os.path.abspath(DATA_FILE_PATH)}
    return [Document(page_content=text, metadata=metadata)]

def chunk_documents(documents: List[Document]) -> List[Document]:
    """
    Split text into overlapping chunks for embeddings
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=MAX_CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        add_start_index=True
    )
    chunks = text_splitter.split_documents(documents)
    print(f"Split into {len(chunks)} chunks")
    return chunks

def build_vector_store():
    """Build and persist the vector store"""
    print("--- Starting Vector Store Build Process ---")
    load_dotenv()

    # Verify API key
    # google_api_key = os.getenv("GOOGLE_API_KEY_1")
    # if not google_api_key:
    #     print("CRITICAL ERROR: GOOGLE_API_KEY_1 not found in environment")
    #     exit(1)

    # 1. Load TXT data
    print("Step 1: Loading TXT data...")
    raw_text = load_txt_file()
    
    # 2. Wrap in Document
    print("Step 2: Creating initial Document...")
    documents = create_documents_from_text(raw_text)
    
    # 3. Chunking
    print("Step 3: Splitting into chunks...")
    chunks = chunk_documents(documents)
    
    # 4. Initialize embeddings
    print("Step 4: Initializing embeddings...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    # 5. Create and persist vector store
    print(f"Step 5: Creating vector store at {CHROMA_DB_PATH}...")
    try:
        Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=CHROMA_DB_PATH
        )
        print("SUCCESS: Vector store created and persisted")
    except Exception as e:
        print(f"Error creating vector store: {e}")
        exit(1)
    
    # 6. Verify
    if os.path.exists(CHROMA_DB_PATH) and os.listdir(CHROMA_DB_PATH):
        print("--- BUILD SUCCESSFUL ---")
    else:
        print("--- BUILD FAILED ---")
        exit(1)

if __name__ == '__main__':
    build_vector_store()
