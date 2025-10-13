# Friday AI Project Import Structure Mapping

This document lists the current Python import structure and the new import structure required after migration to the proposed architecture.

---

## 1. Current Import Structure

### Main Project
```
from tools import get_weather, search_web, triotech_info, create_lead, detect_lead_intent
from prompts import AGENT_INSTRUCTION, SESSION_INSTRUCTION
# Use `config.setup_conversation_log()` to ensure `conversations/` exists (no legacy file is created)
from livekit.plugins.google import LLM
from livekit.plugins.cartesia import TTS
```

### RAG Model (Xeny Rag Model)
```
from build_db import build_vector_store
from runapi import initialize_rag_pipeline
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
```

### Knowledge Files
```
open('Xeny Rag Model/knowledge.txt')
open('Xeny Rag Model/triotech_knowledge.txt')
open('data/triotech_content.json')
```

---

## 2. New Import Structure (After Migration)

### Main Project
```
from tools import get_weather, search_web, triotech_info, create_lead, detect_lead_intent
from prompts import AGENT_INSTRUCTION, SESSION_INSTRUCTION
from config import setup_conversation_log
from livekit.plugins.google import LLM
from livekit.plugins.cartesia import TTS
```

### RAG Model (model/)
```
from model.build_db import build_vector_store
from model.runapi import initialize_rag_pipeline
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
```

### Knowledge Files
```
open('data/knowledge.txt')
open('data/triotech_knowledge.txt')
open('data/triotech_content.json')
```

---

## 3. Mapping Table (Old → New)

| Old Location                              | New Location                |
|-------------------------------------------|-----------------------------|
| Xeny Rag Model/build_db.py                | model/build_db.py           |
| Xeny Rag Model/runapi.py                  | model/runapi.py             |
| Xeny Rag Model/knowledge.txt              | data/knowledge.txt          |
| Xeny Rag Model/triotech_knowledge.txt     | data/triotech_knowledge.txt |
| Xeny Rag Model/chroma_db/                 | model/chroma_db/            |
| Xeny Rag Model/templates/index.html       | model/templates/index.html  |
| Xeny Rag Model/requirements.txt           | Consolidated into main requirements.txt |

---

**After migration, update all import statements and file open paths to use the new structure.**

Ready for migration!
