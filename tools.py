import logging
from livekit.agents import function_tool,RunContext
import requests
from langchain_community.tools import DuckDuckGoSearchRun
import json
import os
import sys
import time
from datetime import datetime
import asyncio

# RAG imports

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

# Lead utilities (MongoDB + JSON fallback)
LEADS_DIR = os.path.join(os.getcwd(), "leads")
os.makedirs(LEADS_DIR, exist_ok=True)

# MongoDB integration with fallback
USE_MONGODB = os.getenv("USE_MONGODB", "true").lower() == "true"

try:
    if USE_MONGODB:
        from db_config import LeadsDB
        MONGODB_AVAILABLE = True
        logging.info("MongoDB integration enabled for leads")
    else:
        MONGODB_AVAILABLE = False
        logging.info("MongoDB integration disabled - using file storage")
except ImportError as e:
    MONGODB_AVAILABLE = False
    logging.warning(f"MongoDB not available, using file storage fallback: {e}")

def save_lead(lead: dict) -> str:
    """Save lead to MongoDB or JSON file fallback. Returns the saved identifier."""
    lead_data = {
        "timestamp": datetime.now().isoformat(),
        "source": "Friday AI Assistant", 
        "status": "new",
        **lead
    }
    
    # Try MongoDB first if available
    if MONGODB_AVAILABLE:
        try:
            lead_id = LeadsDB.create_lead(lead_data)
            if lead_id:
                logging.info(f"FRIDAY AI: Lead saved to MongoDB with ID: {lead_id}")
                return f"mongodb:{lead_id}"
        except Exception as e:
            logging.error(f"Failed to save lead to MongoDB: {e}")
    
    # Fallback to JSON file storage
    ts = time.strftime("%Y%m%d_%H%M%S")
    filename = f"lead_{ts}.json"
    path = os.path.join(LEADS_DIR, filename)
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(lead_data, f, indent=2, ensure_ascii=False)
    
    logging.info(f"FRIDAY AI: Lead saved to file: {path}")
    return path

def is_valid_lead(lead: dict) -> bool:
    """Validate if lead has required fields."""
    required = ["name", "email", "company", "interest"]
    return all(lead.get(field) for field in required)

def validate_email(email: str) -> bool:
    """Basic email validation."""
    return "@" in email and "." in email.split("@")[-1]

# Path to triotech content
TRIOTECH_FILE = os.path.join(os.path.dirname(__file__), "data", "triotech_content.json")
RAG_DB_PATH = os.path.join(os.path.dirname(__file__), "model", "chroma_db")

# Global RAG chain
rag_chain = None
# Flag to indicate if RAG (retrieval-augmented generation) dependencies are available
RAG_AVAILABLE = False

def _load_triotech_data():
    """Load Triotech knowledge base data."""
    try:
        with open(TRIOTECH_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading Triotech data: {e}")
        return {"products": [], "faqs": [], "differentiators": []}

def _initialize_rag_system():
    """Initialize the RAG system for detailed queries"""
    global rag_chain
    
    if not RAG_AVAILABLE:
        logging.warning("RAG system not available - missing dependencies")
        return False
        
    if rag_chain is not None:
        return True  # Already initialized
        
    try:
        # Check if RAG database exists
        if not os.path.exists(RAG_DB_PATH):
            logging.warning(f"RAG database not found at {RAG_DB_PATH}")
            return False
            
        # Get Google API key
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if not google_api_key:
            logging.warning("GOOGLE_API_KEY not found for RAG system")
            return False
            
        # Initialize components
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=google_api_key,
            temperature=0.3
        )
        
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        
        vectorstore = Chroma(
            persist_directory=RAG_DB_PATH,
            embedding_function=embeddings
        )
        
        retriever = vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={"k": 4, "fetch_k": 8}
        )
        
        # Triotech-specific prompt
        system_prompt = """You are a Triotech sales assistant with access to detailed product documentation.
        
Guidelines:
1. Answer questions about Triotech products, features, and services using the provided context.
2. Be specific and detailed when explaining product capabilities.
3. If the context contains relevant information, provide comprehensive answers.
4. Always respond in Hindi unless the user explicitly asks in English.
5. Focus on business benefits and use cases.
6. If information is incomplete, mention what details are available.

Context: {context}"""

        qa_prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}")
        ])
        
        question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)
        rag_chain = create_retrieval_chain(retriever, question_answer_chain)
        
        logging.info("RAG system initialized successfully")
        return True
        
    except Exception as e:
        logging.error(f"Error initializing RAG system: {e}")
        return False

def _query_rag_system(query: str) -> str:
    """Query the RAG system for detailed information"""
    global rag_chain
    
    if not _initialize_rag_system():
        return None
        
    try:
        response = rag_chain.invoke({"input": query})
        answer = response.get("answer", "").strip()
        
        if answer and len(answer) > 50:  # Valid detailed response
            return answer
        else:
            return None
            
    except Exception as e:
        logging.error(f"Error querying RAG system: {e}")
        return None

@function_tool()
async def get_weather(city: str) -> str:
    """Get the current weather for a given city"""
    try:
        response = requests.get(f"https://wttr.in/{city}?format=3")
        if response.status_code == 200:
            logging.info(f"Weather for {city}: {response.text.strip()}")
            return response.text.strip()
        else:
            logging.error(f"Failed to get weather for {city}: {response.status_code}")
            return f"Failed to get weather for {city}: {response.status_code}"
    except Exception as e:
        logging.error(f"Error getting weather for {city}: {e}")
        return f"Error getting weather for {city}: {e}"
    
@function_tool()
async def search_web(query: str) -> str:
    """Search the web for information about a given query using DuckDuckGo Search"""
    try:
        results = DuckDuckGoSearchRun().run(tool_input=query)
        logging.info(f"Search results for '{query}': {results}")
        return results
    except Exception as e:
        logging.error(f"Error searching the web for '{query}': {e}")
        return f"An error occurred while searching the web for '{query}'."

@function_tool()
async def triotech_info(query: str) -> str:
    """
    Hybrid Triotech knowledge system: uses JSON for basic info, RAG for detailed queries.
    Examples:
      - "Tell me about Justtawk" (basic - uses JSON)
      - "What are the detailed features of Justtawk?" (detailed - uses RAG)
      - "How to integrate Convoze with existing systems?" (detailed - uses RAG)
      - "List all products" (basic - uses JSON)
    """
    data = _load_triotech_data()
    query_lower = (query or "").lower()
    
    # Step 1: Try JSON for basic product/FAQ lookup
    json_result = None
    
    # Product lookup by name (exact substring match)
    for p in data.get("products", []):
        if p.get("name", "").lower() in query_lower:
            json_result = f"{p['name']}: {p['desc']} (Target: {p['target']})"
            break
    
    # FAQ lookup if no product match
    if not json_result:
        for faq in data.get("faqs", []):
            fq_lower = faq.get("q", "").lower()
            faq_words = [w for w in fq_lower.split() if len(w) > 3]
            if any(w in query_lower for w in faq_words):
                json_result = f"Q: {faq['q']} → A: {faq['a']}"
                break
    
    # Differentiators lookup
    if not json_result and ("why triotech" in query_lower or "differentiator" in query_lower or "why choose" in query_lower):
        json_result = "Key Differentiators: " + ", ".join(data.get("differentiators", []))
    
    # List products
    if not json_result and ("list" in query_lower and "product" in query_lower):
        names = [p.get("name") for p in data.get("products", [])]
        json_result = "Products: " + ", ".join(names) if names else "माफ़ करें, उत्पाद सूची उपलब्ध नहीं है।"
    
    # Step 2: Determine if detailed query (needs RAG)
    detailed_keywords = [
        "detailed", "features", "how to", "integrate", "implementation", 
        "pricing", "demo", "setup", "configuration", "api", "technical",
        "comparison", "benefits", "use case", "workflow", "process"
    ]
    
    is_detailed_query = any(keyword in query_lower for keyword in detailed_keywords)
    
    # Step 3: Decision logic
    if json_result and not is_detailed_query:
        # Basic query with JSON match - return JSON result
        logging.info(f"Hybrid: Using JSON for basic query: {query}")
        return json_result
    
    elif json_result and is_detailed_query:
        # Detailed query about known product - try RAG first, fallback to enhanced JSON
        logging.info(f"Hybrid: Trying RAG for detailed query about known product: {query}")
        rag_result = _query_rag_system(query)
        
        if rag_result:
            return rag_result
        else:
            # RAG failed, return enhanced JSON response
            return json_result + "\n\nअधिक विस्तृत जानकारी के लिए, कृपया हमारी सेल्स टीम से संपर्क करें।"
    
    elif not json_result and is_detailed_query:
        # No JSON match but detailed query - try RAG
        logging.info(f"Hybrid: Using RAG for unknown detailed query: {query}")
        rag_result = _query_rag_system(query)
        
        if rag_result:
            return rag_result
        else:
            return "माफ़ करें, इस बारे में विस्तृत जानकारी उपलब्ध नहीं है। क्या आप चाहेंगे कि मैं आपको हमारी सेल्स टीम से जोड़ दूँ?"
    
    else:
        # No JSON match and basic query - standard fallback
        logging.info(f"Hybrid: No match found for basic query: {query}")
        return "माफ़ करें, इस बारे में मुझे जानकारी नहीं मिली। क्या आप चाहेंगे कि मैं आपको हमारी सेल्स टीम से जोड़ दूँ?"

@function_tool()
async def create_lead(name: str, email: str, company: str, interest: str, phone: str = "", job_title: str = "", budget: str = "", timeline: str = "") -> str:
    """
    Create a new lead for Triotech sales team.
    Required: name, email, company, interest
    Optional: phone, job_title, budget, timeline
    
    Example: create_lead("John Doe", "john@company.com", "Tech Corp", "AI Voice Bot", "9876543210", "CTO", "50k-100k", "Q1 2025")
    """
    # Validate required fields
    if not all([name, email, company, interest]):
        return "कृपया सभी आवश्यक जानकारी प्रदान करें: नाम, ईमेल, कंपनी, और रुचि का विषय।"
    
    # Validate email
    if not validate_email(email):
        return "कृपया एक वैध ईमेल पता प्रदान करें।"
    
    # Create lead data
    lead_data = {
        "name": name.strip(),
        "email": email.strip().lower(),
        "company": company.strip(),
        "interest": interest.strip(),
        "phone": phone.strip() if phone else "",
        "job_title": job_title.strip() if job_title else "",
        "budget": budget.strip() if budget else "",
        "timeline": timeline.strip() if timeline else ""
    }
    
    # Validate lead
    if not is_valid_lead(lead_data):
        return "लीड डेटा में कुछ समस्या है। कृपया सभी आवश्यक फील्ड भरें।"
    
    try:
        # Save lead
        file_path = save_lead(lead_data)
        
        # Return success message
        return f"धन्यवाद {name}! आपकी जानकारी सुरक्षित कर ली गई है। हमारी सेल्स टीम जल्द ही {company} के लिए {interest} के बारे में आपसे संपर्क करेगी।"
        
    except Exception as e:
        logging.error(f"Error creating lead: {e}")
        return "माफ़ करें, लीड सेव करने में कुछ समस्या हुई है। कृपया दोबारा कोशिश करें।"

@function_tool()
async def detect_lead_intent(user_message: str) -> str:
    """
    Analyze user message to detect if they are introducing themselves or showing business interest.
    Returns guidance on how to respond for lead generation.
    
    Example: detect_lead_intent("I am John from Tech Corp")
    """
    message_lower = user_message.lower()
    
    # Check for self-introduction patterns
    intro_patterns = [
        "i am", "my name is", "this is", "i'm", 
        "from", "company", "business", "organization"
    ]
    
    # Check for business interest patterns
    interest_patterns = [
        "demo", "price", "cost", "quote", "proposal", 
        "solution", "service", "product", "help", "need"
    ]
    
    # Check for company indicators
    company_indicators = [
        "ltd", "limited", "corp", "corporation", "inc", "company",
        "pvt", "private", "llc", "solutions", "systems", "tech"
    ]
    
    has_intro = any(pattern in message_lower for pattern in intro_patterns)
    has_interest = any(pattern in message_lower for pattern in interest_patterns)
    has_company = any(indicator in message_lower for indicator in company_indicators)
    
    if has_intro and (has_company or has_interest):
        return "LEAD_OPPORTUNITY: User is introducing themselves from a company. Ask about their requirements and collect contact details."
    elif has_interest:
        return "INTEREST_DETECTED: User shows business interest. Ask qualifying questions and collect lead information."
    elif has_company:
        return "COMPANY_MENTIONED: User mentioned a company. Explore their needs and collect contact details."
    else:
        return "NO_LEAD_INTENT: Continue normal conversation."

class HangupTool:
    """A tool to manage the call hangup process."""
    def __init__(self, hangup_event: asyncio.Event):
        self._hangup_event = hangup_event

    @function_tool()  # This decorator is the key to making it a valid tool
    async def end_call(self):
        """
        Signals that the conversation is over and the call should be terminated.
        Use this tool when the user wants to hang up or the conversation's goal is met.
        """
        logging.info("end_call tool was called by the agent, setting hangup event.")
        self._hangup_event.set()
        return "Call termination sequence has been initiated."