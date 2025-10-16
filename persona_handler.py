"""
Persona Handler
Handles persona loading and configuration from job metadata and CRM API fallback
"""

import json
import logging
import os
import asyncio
import requests
import functools
from typing import Dict, Optional, Tuple
from livekit.agents import JobContext

from prompts import AGENT_INSTRUCTION, SESSION_INSTRUCTION
from transcript_logger import log_event


@functools.lru_cache(maxsize=256)
def load_persona_from_api(dialed_number: str, timeout: int = 5) -> Optional[Dict]:
    """
    Synchronous persona fetch from CRM API (cached).
    Used as fallback when job metadata is missing.
    """
    if not dialed_number:
        return None
    try:
        base = os.getenv("PERSONA_API_BASE", "https://devcrm.xeny.ai/apis/api/public/mobile")
        url = f"{base}/{dialed_number}"
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        
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
    session_instructions = None
    closing_message = None
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

        # 3. Safely extract the persona object from the config
        # This single block replaces the redundant nested logic
        persona = config.get("campaigns", [{}])[0].get("voiceAgents", [{}])[0].get("persona", {})

        if not persona:
            logging.warning("Config loaded, but no valid persona object was found inside.")
            return agent_instructions, session_instructions, closing_message, persona_name, full_config

        # 4. Extract all necessary components from the persona
        personality = persona.get("personality", "")
        conversation_structure = persona.get("conversationStructure", "")
        workflow = persona.get("workflow", "")  # This is the Knowledge Base
        
        messages = persona.get("fullConfig", {}).get("messages", {})
        welcome_message = persona.get("welcomeMessage") or messages.get("welcomeMessage", "")
        closing_message = persona.get("closingMessage") or messages.get("closingMessage", "") # Correctly assign to the return variable
        
        persona_name = persona.get("name", "unknown")
        logging.info(f"Building instructions for persona: {persona_name}")

        # 5. Build the AGENT INSTRUCTION (the agent's core identity)
        agent_instructions = f"""
# CORE IDENTITY & RULES
You are {persona_name}.
{personality}

# CONVERSATION STRUCTURE
You must follow these steps for structuring the conversation:
{conversation_structure}

# KNOWLEDGE BASE & WORKFLOW
You must use the following information to answer user questions. Do not use outside knowledge.
{workflow}

# DATA COLLECTION
If the conversation requires it, you can ask for the following data fields for lead generation. Only ask for what is necessary.
- Required: name, email, phone number.
- Optional: organization name, position.
"""
        logging.info("Agent instructions built successfully.")

        # 6. Build the initial SESSION INSTRUCTION (the first command) and assign it for return
        if welcome_message:
            session_instructions = f"Start the conversation by delivering your welcome message: '{welcome_message}'"
            logging.info(f"Session instruction created with welcome message: {welcome_message[:50]}...")
        else:
            session_instructions = "Greet the user and ask how you can help them."
            logging.info("No welcome message found; using generic greeting for session instruction.")

    except Exception as e:
        logging.error(f"Error loading persona from API for {dialed_number}: {e}", exc_info=True)

    # 7. Return all the configured values
    return agent_instructions, session_instructions, closing_message, persona_name, full_config

async def load_persona_with_fallback(ctx: JobContext) -> Tuple[str, Optional[str], Optional[str], str, Optional[Dict]]:
    """
    Load persona configuration with fallback strategy:
    1. Try job metadata first (webhook-provided config)
    2. Fall back to API call using DEFAULT_CALLER environment variable
    
    Returns:
        Tuple of (agent_instructions, session_instructions, closing_message, persona_name, full_config)
    """
    # First try metadata
    if ctx.job.metadata:
        logging.info("Attempting to load persona from job metadata")
        result = load_persona_from_metadata(ctx)
        if result[3] != "default":  # persona_name != "default" means we found valid persona
            logging.info("Successfully loaded persona from job metadata")
            return result
        else:
            logging.info("Job metadata present but no valid persona found, falling back to API")
    else:
        logging.info("No job metadata found, falling back to API")
    
    # Fallback to API call using DEFAULT_CALLER
    default_caller = os.getenv("DEFAULT_CALLER", "8655701143")
    logging.info(f"Loading persona from API using DEFAULT_CALLER: {default_caller}")
    
    result = await load_persona_from_dialed_number(default_caller)
    
    # Log the persona loading event
    try:
        if result[4]:  # full_config is not None
            log_event({
                "type": "persona_loaded_from_api",
                "dialed_number": default_caller,
                "persona_name": result[3],
                "source": "api_fallback"
            })
        else:
            log_event({
                "type": "persona_not_found",
                "dialed_number": default_caller,
                "source": "api_fallback"
            })
    except Exception as e:
        logging.warning(f"Failed to log persona loading event: {e}")
    
    return result
from transcript_logger import log_event


def load_persona_from_metadata(ctx: JobContext) -> Tuple[str, Optional[str], Optional[str], str, Optional[Dict]]:
    """
    Load persona configuration from job metadata
    
    Returns:
        Tuple of (agent_instructions, session_instructions, closing_message, persona_name, full_config)
    """
    agent_instructions = AGENT_INSTRUCTION  # default fallback
    session_instructions = SESSION_INSTRUCTION  # default fallback
    closing_message = None
    persona_name = "default"
    full_config = None
    
    if not ctx.job.metadata:
        logging.info("No job metadata found, using default persona")
        return agent_instructions, session_instructions, closing_message, persona_name, full_config
    
    try:
        config = json.loads(ctx.job.metadata)
        if not config:
            logging.info("Empty metadata config, using default persona")
            return agent_instructions, session_instructions, closing_message, persona_name, full_config
            
        full_config = config
        logging.info(f"Loaded configuration from metadata for mobile: {config.get('mobileNo', 'unknown')}")
        
        # Extract persona configuration safely
        campaigns = config.get("campaigns", [])
        if campaigns and len(campaigns) > 0:
            voice_agents = campaigns[0].get("voiceAgents", [])
            if voice_agents and len(voice_agents) > 0:
                persona = voice_agents[0].get("persona", {})
                if persona:
                    # Extract components
                    personality = persona.get("personality", "")
                    conversation_structure = persona.get("conversationStructure", "")
                    welcome_message = persona.get("welcomeMessage", "")
                    closing_message = persona.get("closingMessage", "")
                    persona_name = persona.get("name", "unknown")
                    
                    # Also check fullConfig.messages if not found in persona directly
                    if not welcome_message or not closing_message:
                        full_config_obj = persona.get("fullConfig", {})
                        messages = full_config_obj.get("messages", {})
                        welcome_message = welcome_message or messages.get("welcomeMessage", "")
                        closing_message = closing_message or messages.get("closingMessage", "")
                    
                    # Build comprehensive agent instructions
                    agent_instruction_parts = []
                    
                    if personality:
                        agent_instruction_parts.append(f"# Persona\n{personality}")
                    
                    if welcome_message:
                        agent_instruction_parts.append(f"# Welcome Message\nAlways start conversations with: \"{welcome_message}\"")
                    
                    if closing_message:
                        agent_instruction_parts.append(f"# Closing Message\nWhen ending conversations, use: \"{closing_message}\"")
                    
                    # Combine all parts
                    if agent_instruction_parts:
                        agent_instructions = "\n\n".join(agent_instruction_parts)
                        logging.info("Agent instructions built from persona components")
                    
                    # Use conversation structure for session instructions
                    if conversation_structure:
                        session_instructions = conversation_structure
                        logging.info("Session instructions loaded from persona.conversationStructure")
                    
                    logging.info(f"Loaded persona: {persona_name}")
                    if welcome_message:
                        logging.info(f"Welcome message: {welcome_message[:50]}...")
                        
    except (json.JSONDecodeError, IndexError, KeyError) as e:
        logging.warning(f"Could not parse persona from job metadata: {e}. Using default instructions.")
    except Exception as e:
        logging.error(f"Unexpected error parsing persona metadata: {e}")
    
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