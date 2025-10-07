# run.py - AI Chatbot Backend for TXT Knowledge Base Analysis
import os
import json
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from dotenv import load_dotenv
from google.api_core import exceptions as google_exceptions

# LangChain Imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

# --- Setup ---
app = Flask(__name__)
CORS(app)
load_dotenv()

# --- Global Variables ---
rag_chain = None
CHROMA_DB_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")
api_keys = []
current_key_index = 0

# --- Load API Keys ---
def load_api_keys():
    global api_keys
    i = 1
    while True:
        key = os.getenv(f"GOOGLE_API_KEY_{i}")
        if key:
            api_keys.append(key)
            i += 1
        else:
            break
    if not api_keys:
        print("CRITICAL ERROR: No API keys found.")
    else:
        print(f"SUCCESS: Loaded {len(api_keys)} API key(s).")

# --- LangChain RAG Pipeline Initialization ---
def initialize_rag_pipeline(api_key: str):
    global rag_chain
    if not os.path.exists(CHROMA_DB_PATH):
        print(f"CRITICAL ERROR: Chroma DB not found at {CHROMA_DB_PATH}.")
        return False
    
    try:
        # LLM
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=api_key
        )

        # Embeddings + Vectorstore
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

        
        vectorstore = Chroma(
            persist_directory=CHROMA_DB_PATH,
            embedding_function=embeddings
        )

        # Retriever (best practice: MMR for diverse chunks)
        retriever = vectorstore.as_retriever(
            search_type="mmr",   # maximal marginal relevance
            search_kwargs={"k": 6, "fetch_k": 12}
        )

        # System Prompt
        system_prompt = """You are an advanced AI assistant with expertise in understanding and explaining complex information.
Your role is to answer user questions comprehensively using the provided knowledge base context.

Guidelines:
1. Always ground your answers in the provided context, but expand with reasoning, clarification, and related insights.
2. Provide clear, structured, and well-organized responses (use sections, bullet points, or lists where helpful).
3. Be detailed — explain concepts fully instead of giving short or vague replies.
4. Highlight key insights, important details, and actionable information.
5. If something is unclear in the context, infer the most likely explanation and explicitly state your assumptions.
6. If the information truly does not exist in the knowledge base, say: 
   "The available knowledge base does not provide a direct answer to this question," 
   and suggest possible directions or related knowledge.

Context: {context}"""

        qa_prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}")
        ])
        
        question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)
        rag_chain = create_retrieval_chain(retriever, question_answer_chain)
        print("RAG pipeline initialized successfully.")
        return True
    except Exception as e:
        print(f"Error initializing RAG pipeline: {e}")
        return False

# --- Flask API Endpoints ---
@app.route('/ask', methods=['POST'])
def ask_question():
    global rag_chain, current_key_index
    if not rag_chain:
        return jsonify({'error': 'AI model not ready'}), 503

    data = request.get_json()
    query = data.get('query')
    
    if not query:
        return jsonify({'error': 'Missing query parameter'}), 400

    max_retries = len(api_keys)
    result = {"error": "All API keys exhausted"}
    
    for _ in range(max_retries):
        try:
            response = rag_chain.invoke({"input": query})

            print("Retrieved documents:")
            for doc in response.get("context", []):
                print(doc.page_content[:150], "...\n")

            raw_response = response.get("answer", "").strip()

            # Handle markdown-wrapped JSON (safety, if ever happens)
            if raw_response.startswith("```json"):
                raw_response = raw_response[7:-3].strip()
            elif raw_response.startswith("```"):
                raw_response = raw_response[3:-3].strip()

            # Try parse as JSON (if prompt designed that way), else return text
            try:
                result = json.loads(raw_response)
            except json.JSONDecodeError:
                result = {"answer": raw_response}
            
            break # Success
        except google_exceptions.ResourceExhausted:
            current_key_index = (current_key_index + 1) % len(api_keys)
            initialize_rag_pipeline(api_keys[current_key_index])
        except Exception as e:
            print(f"Unexpected error: {e}")
            result = {"error": "Analysis failed"}
            break
    print(f"Completed with result: {result}")
    return jsonify(result)

@app.route('/')
def home():
    # Simple HTML template (frontend will be served directly)
    template_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    return render_template_string(open(template_path).read())

# --- SCRIPT EXECUTION ---
if __name__ == '__main__':
    load_api_keys()
    if api_keys:
        initialize_rag_pipeline(api_keys[current_key_index])
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
