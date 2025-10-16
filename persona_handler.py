"""
Persona Handler
Handles persona loading and configuration from job metadata
"""

import json
import logging
from typing import Dict, Optional, Tuple
from livekit.agents import JobContext

from prompts import AGENT_INSTRUCTION


def load_persona_from_metadata(ctx: JobContext) -> Tuple[str, Optional[str], Optional[str], str, Optional[Dict]]:
    """
    Load persona configuration from job metadata
    
    Returns:
        Tuple of (agent_instructions, welcome_message, closing_message, persona_name, full_config)
    """
    agent_instructions = AGENT_INSTRUCTION  # default fallback
    welcome_message = None
    closing_message = None
    persona_name = "default"
    full_config = None
    
    if not ctx.job.metadata:
        logging.info("No job metadata found, using default persona")
        return agent_instructions, welcome_message, closing_message, persona_name, full_config
    
    try:
        config = json.loads(ctx.job.metadata)
        if not config:
            logging.info("Empty metadata config, using default persona")
            return agent_instructions, welcome_message, closing_message, persona_name, full_config
            
        full_config = config
        logging.info(f"Loaded configuration from metadata for mobile: {config.get('mobileNo', 'unknown')}")
        
        # Extract persona configuration safely
        campaigns = config.get("campaigns", [])
        if campaigns and len(campaigns) > 0:
            voice_agents = campaigns[0].get("voiceAgents", [])
            if voice_agents and len(voice_agents) > 0:
                persona = voice_agents[0].get("persona", {})
                if persona:
                    # Update agent instructions with persona data
                    personality = persona.get("personality")
                    conversation_structure = persona.get("conversationStructure")
                    
                    if personality:
                        agent_instructions = personality
                        logging.info("Agent instructions loaded from persona.personality")
                    elif conversation_structure:
                        agent_instructions = conversation_structure  
                        logging.info("Agent instructions loaded from persona.conversationStructure")
                    
                    # Extract messages
                    welcome_message = persona.get("welcomeMessage")
                    closing_message = persona.get("closingMessage")
                    persona_name = persona.get("name", "unknown")
                    
                    # Also check fullConfig.messages if not found in persona directly
                    if not welcome_message or not closing_message:
                        full_config_obj = persona.get("fullConfig", {})
                        messages = full_config_obj.get("messages", {})
                        welcome_message = welcome_message or messages.get("welcomeMessage")
                        closing_message = closing_message or messages.get("closingMessage")
                    
                    logging.info(f"Loaded persona: {persona_name}")
                    if welcome_message:
                        logging.info(f"Welcome message: {welcome_message[:50]}...")
                        
    except (json.JSONDecodeError, IndexError, KeyError) as e:
        logging.warning(f"Could not parse persona from job metadata: {e}. Using default instructions.")
    except Exception as e:
        logging.error(f"Unexpected error parsing persona metadata: {e}")
    
    return agent_instructions, welcome_message, closing_message, persona_name, full_config


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
                             welcome_message: Optional[str], closing_message: Optional[str]):
    """Attach persona configuration to session for tools and logging"""
    try:
        setattr(session, "full_config", full_config)
        setattr(session, "persona_name", persona_name)
        setattr(session, "welcome_message", welcome_message)
        setattr(session, "closing_message", closing_message)
        logging.info(f"Attached persona config to session: {persona_name}")
        return True
    except Exception as e:
        logging.warning(f"Failed to attach config to session: {e}")
        return False