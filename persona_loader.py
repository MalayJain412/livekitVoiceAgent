"""
Persona Loader Module

Handles dynamic loading of personas based on incoming caller number.
Fetches persona configuration from API and applies it to the agent session.
"""

import os
import logging
import asyncio
import requests
import re
import functools
import time
from typing import Optional, Dict, Any

from transcript_logger import log_event


def normalize_caller(raw: str) -> str:
    """Normalize caller number by removing non-digits and country codes."""
    if not raw:
        return ""
    # strip non-digit characters
    s = re.sub(r"\D", "", str(raw))
    # if leading country code 91 and length > 10, take last 10 digits
    if s.startswith("91") and len(s) > 10:
        s = s[-10:]
    # if leading zeros, strip
    s = s.lstrip("0")
    return s


@functools.lru_cache(maxsize=256)
def load_persona_sync(caller: str, timeout: int = 5) -> Optional[Dict[str, Any]]:
    """Synchronous persona fetch used with asyncio.to_thread (cached)."""
    if not caller:
        return None
    try:
        base = os.getenv("PERSONA_API_BASE", "https://devcrm.xeny.ai/apis/api/public/mobile")
        url = f"{base}/{caller}"
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        campaigns = data.get("campaigns") or []
        if not campaigns:
            return None
        # pick first campaign -> first voiceAgent -> persona
        persona = campaigns[0]["voiceAgents"][0].get("persona")
        return persona
    except Exception as e:
        logging.warning(f"Failed to load persona for {caller}: {e}")
        return None


async def detect_and_apply_persona(session, agent) -> None:
    """
    Detect caller from session metadata and apply matching persona.
    
    Args:
        session: The AgentSession instance
        agent: The Agent instance to update instructions on
    """
    caller = None
    try:
        # Prefer room metadata
        room = getattr(session, "room", None)
        if room:
            try:
                rm = getattr(room, "metadata", None) or {}
                caller = rm.get("caller") or rm.get("caller_id") or rm.get("from")
            except Exception:
                caller = None

            # If no room caller, inspect participants
            if not caller:
                participants = getattr(room, "participants", None) or {}
                try:
                    iterable = participants.values() if isinstance(participants, dict) else participants
                    for p in iterable:
                        try:
                            pmeta = getattr(p, "metadata", None) or {}
                            caller = pmeta.get("caller_id") or pmeta.get("callerNumber") or pmeta.get("from") or getattr(p, "identity", None)
                            if caller:
                                break
                        except Exception:
                            continue
                except Exception:
                    pass
    except Exception:
        caller = None

    # Fallback to env default for local testing
    if not caller:
        caller = os.getenv("DEFAULT_CALLER", "8655701159")

    caller = normalize_caller(caller)

    try:
        # attach caller number to session
        try:
            setattr(session, "caller_number", caller)
        except Exception:
            pass

        # fetch persona in background thread (non-blocking main loop)
        persona = await asyncio.to_thread(load_persona_sync, caller)
        if persona:
            try:
                setattr(session, "caller_persona", persona)
            except Exception:
                pass

            # update prompts module and agent.instructions best-effort
            try:
                instr = persona.get("personality") or persona.get("conversationStructure")
                if instr:
                    try:
                        agent.instructions = instr
                    except Exception:
                        pass
                    try:
                        import prompts as _prompts
                        if hasattr(_prompts, "set_agent_instruction"):
                            _prompts.set_agent_instruction(instr)
                        elif hasattr(_prompts, "AGENT_INSTRUCTION"):
                            _prompts.AGENT_INSTRUCTION = instr
                    except Exception:
                        pass

            except Exception:
                pass

            # log success event
            try:
                log_event({
                    "type": "persona_loaded",
                    "caller": caller,
                    "persona_name": persona.get("name"),
                    "persona_id": persona.get("_id"),
                    "ts": time.time(),
                })
            except Exception:
                pass
        else:
            try:
                log_event({
                    "type": "persona_not_found",
                    "caller": caller,
                    "ts": time.time(),
                })
            except Exception:
                pass
    except Exception as e:
        logging.warning(f"Persona detection error for {caller}: {e}")


def start_persona_detection(session, agent) -> None:
    """
    Start background persona detection task (non-blocking).
    
    Args:
        session: The AgentSession instance
        agent: The Agent instance to update instructions on
    """
    try:
        asyncio.create_task(detect_and_apply_persona(session, agent))
    except Exception:
        pass