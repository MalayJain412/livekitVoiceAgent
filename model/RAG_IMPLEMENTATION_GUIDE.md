# RAG Implementation & Update Guide

## Overview
This document explains the Retrieval-Augmented Generation (RAG) implementation in the Friday AI project, its flow, and how to update or edit the RAG system for new knowledge or improved performance.

---

## RAG Architecture

- **Vector Store:**
  - Built using LangChain's ChromaDB integration
  - Knowledge sources: `data/triotech_knowledge.txt`, `data/knowledge.txt`
  - Persisted in `model/chroma_db/`
- **Embeddings:**
  - Uses HuggingFace model: `all-MiniLM-L6-v2`
- **LLM:**
  - Google Gemini (via `langchain_google_genai`)
- **Retriever:**
  - Maximal Marginal Relevance (MMR) for diverse context chunks
- **Prompt:**
  - Custom system prompt for Triotech sales assistant
- **API:**
  - Flask backend (`model/runapi.py`) exposes `/ask` endpoint for queries

---

## RAG Flow

1. **Knowledge Ingestion:**
   - Text files (`triotech_knowledge.txt`, `knowledge.txt`) are loaded and split into chunks
   - Chunks are embedded and stored in ChromaDB
2. **Query Handling:**
   - User query is received via API or tool
   - Retriever fetches relevant chunks from vector store
   - LLM generates a detailed answer using context and prompt
3. **Response:**
   - Answer is returned to the user (web UI or API)

---

## How to Update RAG Knowledge

1. **Edit Knowledge Files:**
   - Update `data/triotech_knowledge.txt` or `data/knowledge.txt` with new information
2. **Rebuild Vector Store:**
   - Run the builder script:
     ```sh
     python model/build_db.py
     ```
   - This will re-ingest, chunk, embed, and persist the updated knowledge
3. **Restart Backend:**
   - Restart the Flask API (`model/runapi.py`) to reload the updated vector store

---

## How to Edit RAG Logic

- **Chunking & Embeddings:**
  - Edit chunk size, overlap, or embedding model in `model/build_db.py`
- **Prompt & LLM:**
  - Update the system prompt or LLM parameters in `model/runapi.py`
- **Retriever Settings:**
  - Change retrieval strategy (e.g., number of chunks, MMR) in `model/runapi.py`
- **API Endpoint:**
  - Modify `/ask` endpoint logic in `model/runapi.py` for custom response formatting

---

## Best Practices

- Always backup knowledge files before major updates
- Rebuild the vector store after any knowledge change
- Test queries after updating to ensure relevant and accurate responses
- Keep API keys and secrets secure in `.env`

---

## Troubleshooting

- If answers are outdated, rebuild the vector store
- If RAG fails, check for missing dependencies or corrupted `chroma_db/`
- Review logs for errors during build or query

---

## References
- [LangChain Documentation](https://python.langchain.com/docs/)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [Google Gemini API](https://ai.google.dev/)

---

For further customization, see comments in `model/build_db.py` and `model/runapi.py`.
