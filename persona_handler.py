"""
Persona Handler
Handles persona loading and configuration from dialed number extraction and CRM API
"""

import json
import logging
import os
import asyncio
import requests
import functools
import re
from typing import Dict, Optional, Tuple
from livekit.agents import JobContext
from livekit.api.room_service import RoomService

from prompts import AGENT_INSTRUCTION, SESSION_INSTRUCTION
from transcript_logger import log_event

def _extract_number_from_sip_uri(sip_uri: str) -> str:
    """
    Extract phone number from SIP URI.
    Handles various formats like sip:+918655701159@domain, sip:8655701159@domain
    """
    if not sip_uri:
        return ""

    # Remove 'sip:' prefix if present
    if sip_uri.startswith('sip:'):
        sip_uri = sip_uri[4:]

    # Extract the part before '@' or before any other delimiter
    # Handle formats like +918655701159@domain or 8655701159@domain
    number_part = sip_uri.split('@')[0] if '@' in sip_uri else sip_uri

    # Remove any non-digit characters except + at the beginning
    cleaned = re.sub(r'(?<!^)\+', '', number_part)  # Remove + not at start
    cleaned = re.sub(r'[^\d+]', '', cleaned)  # Remove non-digits except +

    return cleaned

async def get_sip_participant_and_number(ctx: JobContext) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract dialed number from SIP participant in the room.
    Returns (participant_identity, dialed_number) or (None, None) if not found.
    """
    try:
        # Get room service client
        room_svc = RoomService(ctx.connection)

        # List participants in the room
        participants = await room_svc.list_participants(ctx.room.name)

        # Find SIP participant (kind == 2 for SIP participants)
        sip_participant = None
        for p in participants.participants:
            if p.kind == 2:  # SIP participant
                sip_participant = p
                break

        if not sip_participant:
            logging.warning(f"No SIP participant found in room {ctx.room.name}")
            return None, None

        # Extract number from participant attributes or identity
        dialed_number = None

        # Priority 1: Check participant attributes for dialedNumber
        if sip_participant.attributes:
            dialed_number = sip_participant.attributes.get('dialedNumber')

        # Priority 2: Extract from SIP URI in identity
        if not dialed_number and sip_participant.identity:
            dialed_number = _extract_number_from_sip_uri(sip_participant.identity)

        # Priority 3: Extract from room name (fallback)
        if not dialed_number:
            # Room names might contain the number, e.g., "room_8655701159"
            room_name = ctx.room.name
            if '_' in room_name:
                potential_number = room_name.split('_')[-1]
                if potential_number.isdigit():
                    dialed_number = potential_number

        if dialed_number:
            logging.info(f"Extracted dialed number '{dialed_number}' from SIP participant {sip_participant.identity}")
            return sip_participant.identity, dialed_number
        else:
            logging.warning(f"Could not extract dialed number from SIP participant {sip_participant.identity}")
            return sip_participant.identity, None

    except Exception as e:
        logging.error(f"Error extracting SIP participant and number: {e}")
        return None, None

def _sanitize_personality_prompt(raw_personality: str) -> str:
    """
    Cleans and de-duplicates a raw personality prompt from the API
    to resolve contradictions.
    """
    if not raw_personality:
        return "You are a helpful assistant." # Default fallback

    # --- Re-build the personality from scratch based on our "source of truth" ---

    # 1. Define the true Core Purpose (Lead Gen & Appointments)
    core_directive = (
        "# 1. CORE DIRECTIVE (MANDATORY)\n"
        "Your *only* purpose is to assist with **Lead Generation** and **Appointment Scheduling**.\n"
        "You MUST NOT assist with any other topics (like order tracking, technical support, billing, etc.)."
    )

    # 2. Define the true Off-Topic Handling (Polite Redirect, not "ignore")
    off_topic_handling = (
        "# 2. HANDLING OFF-TOPIC REQUESTS\n"
        "If the user asks for anything not related to lead generation or appointments, "
        "you MUST politely decline and guide them back.\n"
        "- **Example Script (Hinglish):** \"Main samajh gayi, lekin main sirf lead generation aur "
        "appointment scheduling mein hi aapki madad kar sakti hoon. Kya aap inme se kisi service mein interested hain?\"\n"
        "- **Example Script (English):** \"I understand, but I can only assist with lead generation and "
        "appointment scheduling. Are you interested in one of those services?\""
    )

    # 3. Define the true Language Rules (Mirror the user)
    language_rules = (
        "# 3. LANGUAGE RULES (MANDATORY)\n"
        "- **Mirror the User:** Your language MUST match the user's.\n"
        "- If the user speaks Hindi, respond in Hindi.\n"
        "- If the user speaks English, respond in English.\n"
        "- If the user speaks Hinglish (mix), respond in Hinglish.\n"
        "- **Identity:** Always use feminine verb forms for yourself (e.g., karungi, jaa rahi hoon)."
    )

    # 4. Define the true Conversation/Tone Rules (Consolidated & De-duplicated)
    conversation_rules = (
        "# 4. CONVERSATION RULES\n"
        "- **Tone:** Be warm, empathetic, and professional, but also efficient.\n"
        "- **Clarity:** Keep responses concise (2-3 sentences).\n"
        "- **Avoid Vague Replies:** You MUST NOT use standalone, context-free words like 'bilkul,' 'sure,' or 'okay.' "
        "Always provide a specific, helpful answer.\n"
        "  - **Instead of:** \"Bilkul.\"\n"
        "  - **Say:** \"Bilkul, main aapki details note kar leti hoon.\"\n"
        "- **Before Ending:** After fulfilling a request (like creating a lead), you MUST always ask "
        "if the user needs more help before you end the call (e.g., \"Aur koi madad chahiye aapko?\")."
    )

    # 5. Combine the new, clean rules into a single string
    clean_personality = "\n\n".join([
        "You are Xeny, a warm and professional AI sales assistant.", # Start with a clean intro
        core_directive,
        off_topic_handling,
        language_rules,
        conversation_rules
    ])

    return clean_personality

def _build_persona_prompts(
    persona_name: str,
    personality: str,
    workflow: str,
    conversation_structure: str,
    welcome_message: str
) -> Tuple[str, str]:
    """
    Builds the final, structured AGENT_INSTRUCTION and SESSION_INSTRUCTION
    using the master f-string templates.
    """

    # Build the AGENT INSTRUCTION (the agent's core identity)
    agent_instructions = f"""
# 1. CORE PERSONA
You are {persona_name}.
{personality}

# 2. LANGUAGE & TONE RULES (FROM PERSONA)
# (This section is now built into the sanitized personality string)

# 3. KNOWLEDGE BASE (WORKFLOW)
- You MUST strictly follow the information below to answer user questions.
- You MUST NOT use any outside knowledge or make up information.
---
{workflow}
---

# 4. CONVERSATION STRUCTURE
- You must follow these general steps for structuring the conversation:
---
{conversation_structure}
---

# 5. LEAD GENERATION RULES (CRITICAL WORKFLOW)
- **Required Fields:** name, email, phone number.
- **Optional Fields:** organization name, position.
- **Tools:** You have two tools: `detect_lead_intent` and `create_lead`.

- **YOU MUST FOLLOW THESE STEPS IN THIS EXACT ORDER:**
    - **STEP 1: DETECT INTENT.** Use `detect_lead_intent`...
    - **STEP 2: GATHER DETAILS.** If intent is detected, politely ask for all **Required Fields**.
    - **STEP 3: CONFIRM DETAILS (MANDATORY).** After the user provides their last detail (e.g., "product manager"), you **MUST NOT** create the lead yet. Your *very next* response **MUST** be to read back their details in **English Only** for confirmation.
        - *Example:* "Okay, just to confirm, your name is Malay Jean, your phone is (623) 215-5888, and your email is malejan1234@therateGmail.com. Is that correct?"
    - **STEP 4: ASK PERMISSION (MANDATORY).** After they say "yes" to STEP 3, you **MUST** then ask for permission in Hinglish: "Kya main aapki details save karke sales team ko forward kar dun?"
    - **STEP 5: CREATE LEAD.** **Only if** they say "yes" to STEP 4, you **MUST** then call the `create_lead` tool.
    - **STEP 6: FINAL CONFIRMATION.** After the tool runs, speak its output (e.g., "Shukriya!...") and then you **MUST** ask: "Aur koi madad chahiye aapko?" or "Is there anything else I can help you with?"

# 6. HOW TO EXPLAIN THE PROCESS
- If a user asks *how* the lead or scheduling process works, you MUST say:
"Zaroor. Main aapki details (jaise naam, phone, email, company, aur aapka interest) **process** karke hamari **specialist sales team** ko **forward** kar doongi, jiske baad woh aapse contact karenge.

Iske alawa, agar aap prefer karein, toh main aapke liye ek appointment bhi **schedule** kar sakti hoon. Main aapki details ko hamari team ke calendar se **sync** karke, aapke convenient time par ek meeting book kar dungi aur aapko ek **calendar invite** automatically mil jaayega."

# 7. TOOL USAGE: ENDING THE CALL (CRITICAL RULES)
- **CRITICAL:** You **MUST NOT** call `end_call` in the same turn as `create_lead`.
- **CRITICAL:** After a successful lead creation (STEP 6), you **MUST** wait for the user to respond to your "Is there anything else...?" question.
- You must ask if there is anything else the user needs help with before ending the call.
- You MUST only call `end_call` when the user *explicitly* says "goodbye," "no, that's all," "thank you, bye," or a similar hangup phrase.
- You MUST NOT say "goodbye" yourself.
"""
    logging.info("Agent instructions built successfully.")

    # This is the flow for the SESSION_INSTRUCTION, not part of the agent's core rules
    lead_generation_flow = """
                1. Greeting → Introduce company (if new user).
                2. Detect need → Product info or Business requirement.
                3. If lead intent detected (demo, pricing, company intro, interest in the product or integrations) → Ask politely for name, email, company, interest.
                4. Before saving confirm the lead details with the user --> make sure these lead details are always pronounced in english and correctly like "Name: XYZ, Email: xyz@example.com, Phone: 1234567890, Organization: ABC Corp, Position: Manager".
                5. Confirm before saving: "Kya main aapki details save karke sales team ko forward kar dun?"
                6. If yes → Use 'create_lead' tool → Share confirmation.
    """

    # Build the initial SESSION INSTRUCTION (the first command)
    session_instructions = f"""
# TASK
Start the conversation. Your very first message to the user MUST be this exact greeting:
"{welcome_message}"

# GUIDELINES
- Always reply in Hinglish (mix Hindi + simple English), unless following the user's language.
- Use 'detect_lead_intent' tool to check if lead opportunity is there.
- Use 'create_lead' to create the lead.
- Follow this flow for lead generation:
{lead_generation_flow}

- Always try to guide conversation towards requirement capture.
- Be professional, helpful, and efficient.
"""
    logging.info("Session instructions built successfully.")

    return agent_instructions, session_instructions

@functools.lru_cache(maxsize=256)
def load_persona_from_api(dialed_number: str, timeout: int = 5) -> Optional[Dict]:
    """
    Synchronous persona fetch from CRM API (cached).

    Raises:
        ValueError: If API returns "No campaigns found" message
    """
    if not dialed_number:
        return None

    try:
        base = os.getenv("PERSONA_API_BASE", "https://devcrm.xeny.ai/apis/api/public/mobile")
        url = f"{base}/{dialed_number}"
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()

        # Check for "No campaigns found" response and fail validation directly
        if isinstance(data, dict) and data.get("message") == "No campaigns found":
            logging.error(f"API returned 'No campaigns found' for {dialed_number} - failing validation")
            raise ValueError(f"No campaigns found for number {dialed_number}")

        # Extract persona from API response
        campaigns = data.get("campaigns") or []
        if not campaigns:
            logging.warning(f"No campaigns found for {dialed_number}")
            return None

        voice_agents = campaigns[0].get("voiceAgents", [])
        if not voice_agents:
            logging.warning(f"No voice agents found for {dialed_number}")
            return None

        persona = voice_agents[0].get("persona")
        if not persona:
            logging.warning(f"No persona found for {dialed_number}")
            return None

        logging.info(f"Successfully loaded persona from API for {dialed_number}: {persona.get('name', 'unknown')}")
        return data  # Return full config for consistency with metadata format

    except ValueError:
        # Re-raise ValueError (our "No campaigns found" case) to fail validation
        raise
    except Exception as e:
        logging.warning(f"Failed to load persona from API for {dialed_number}: {e}")
        return None

async def load_persona_from_dialed_number(dialed_number: str) -> Tuple[str, Optional[str], Optional[str], str, Optional[Dict]]:
    """
    Load persona configuration from CRM API for a dialed number.
    Returns agent instructions, initial session instructions, closing message, persona name, and full config.
    """
    # 1. Set default return values
    agent_instructions = AGENT_INSTRUCTION  # Default instructions
    session_instructions = SESSION_INSTRUCTION
    closing_message = "Thank you for contacting us. Goodbye." # Default closing
    persona_name = "default"
    full_config = None

    try:
        # 2. Fetch config from the API
        config = await asyncio.to_thread(load_persona_from_api, dialed_number)
        if not config:
            logging.info(f"No persona config found for dialed number {dialed_number}, using defaults.")
            return agent_instructions, session_instructions, closing_message, persona_name, full_config

        full_config = config
        logging.info(f"Successfully loaded config from API for {dialed_number}")

        # 3. Safely extract the persona object
        persona = config.get("campaigns", [{}])[0].get("voiceAgents", [{}])[0].get("persona", {})

        if not persona:
            logging.warning("Config loaded, but no valid persona object was found inside.")
            return agent_instructions, session_instructions, closing_message, persona_name, full_config

        # 4. Extract all necessary components from the persona
        raw_personality = persona.get("personality", "")
        conversation_structure = persona.get("conversationStructure", "")
        workflow = persona.get("workflow", "")  # This is the Knowledge Base

        messages = persona.get("fullConfig", {}).get("messages", {})

        if persona.get("welcomeMessage"):
            welcome_message = persona.get("welcomeMessage") or messages.get("welcomeMessage", "")
        else:
            welcome_message = "Greet the user and ask how you can help them."

        # Get Closing Message (This is returned, NOT put in the prompt)
        if persona.get("closingMessage"):
            # --- FIX: Clean the closing message ---
            raw_closing = persona.get("closingMessage") or messages.get("closingMessage", "")
            if "If issue resolved" in raw_closing or "Closing" in raw_closing:
                logging.warning(f"Corrupt closing message detected. Using default.")
                closing_message = "Thank you for contacting us. Have a wonderful day!"
            else:
                closing_message = raw_closing
        else:
            closing_message = "Thank you for contacting us. Have a wonderful day!"

        persona_name = persona.get("name", "unknown")
        logging.info(f"Building instructions for persona: {persona_name}")

        # 5. --- SANITIZE AND BUILD ---
        # Use the helper functions to fix contradictions and build prompts
        personality = _sanitize_personality_prompt(raw_personality)

        agent_instructions, session_instructions = _build_persona_prompts(
            persona_name=persona_name,
            personality=personality,
            workflow=workflow,
            conversation_structure=conversation_structure,
            welcome_message=welcome_message
        )

    except ValueError:
        logging.error(f"Validation failed for {dialed_number}: No campaigns found")
        raise
    except Exception as e:
        logging.error(f"Error loading persona from API for {dialed_number}: {e}", exc_info=True)

    # 7. Return all the configured values
    return agent_instructions, session_instructions, closing_message, persona_name, full_config

def apply_persona_to_agent(agent, agent_instructions: str, persona_name: str):
    """Apply persona configuration to an agent"""
    if agent_instructions != AGENT_INSTRUCTION:
        try:
            agent.instructions = agent_instructions
            logging.info(f"Agent instructions updated with persona data for: {persona_name}")
            return True
        except Exception as e:
            logging.warning(f"Failed to update agent instructions: {e}")
            return False
    return False

def attach_persona_to_session(session, full_config: Optional[Dict], persona_name: str,
                             session_instructions: Optional[str], closing_message: Optional[str]):
    """Attach persona configuration to session for tools and logging"""
    try:
        setattr(session, "full_config", full_config)
        setattr(session, "persona_name", persona_name)
        setattr(session, "session_instructions", session_instructions)
        setattr(session, "closing_message", closing_message)
        logging.info(f"Attached persona config to session: {persona_name}")
        return True
    except Exception as e:
        logging.warning(f"Failed to attach config to session: {e}")
        return False