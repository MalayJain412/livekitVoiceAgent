import logging
from datetime import datetime, time
from typing import Dict, Optional, Tuple
import pytz
import os
import json
from livekit import api
from livekit.agents import get_job_context

def load_test_config() -> Optional[Dict]:
    """
    Load test configuration from local file for testing validation logic.
    Used when TEST_API_RESPONSE_FILE is set.
    """
    test_file = os.getenv("TEST_API_RESPONSE_FILE")
    if test_file:
        try:
            logging.info(f"TEST MODE: Loading validation config from local file: {test_file}")
            with open(test_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logging.info(f"Successfully loaded test config from {test_file}")
            return data
        except Exception as e:
            logging.error(f"Failed to load test config from {test_file}: {e}")
            return None
    return None

def validate_campaign_schedule(schedule: Dict) -> bool:
    """
    Validate if current time is within the campaign schedule.

    Args:
        schedule: Schedule dict from API response containing:
            - activeHours: {"start": "HH:MM", "end": "HH:MM"}
            - startDate: ISO date string
            - endDate: ISO date string
            - daysOfWeek: list of lowercase day names
            - timeZone: timezone string

    Returns:
        bool: True if within schedule, False otherwise
    """
    try:
        timezone = pytz.timezone(schedule.get("timeZone", "UTC"))
        # timezone = "IST"
        now = datetime.now(timezone)

        # Check date range
        start_date = datetime.fromisoformat(schedule["startDate"].replace("Z", "+00:00"))
        end_date = datetime.fromisoformat(schedule["endDate"].replace("Z", "+00:00"))

        if not (start_date <= now <= end_date):
            logging.info(f"Call outside date range: {start_date} to {end_date}")
            return False

        # Check day of week
        current_day = now.strftime("%A").lower()
        allowed_days = [day.lower() for day in schedule.get("daysOfWeek", [])]

        if current_day not in allowed_days:
            logging.info(f"Call on {current_day}, allowed days: {allowed_days}")
            return False

        # Check active hours
        active_hours = schedule.get("activeHours", {})
        start_time = time.fromisoformat(active_hours.get("start", "00:00"))
        end_time = time.fromisoformat(active_hours.get("end", "23:59"))
        current_time = now.time()

        if not (start_time <= current_time <= end_time):
            logging.info(f"Call at {current_time}, active hours: {start_time} to {end_time}")
            return False

        return True

    except Exception as e:
        logging.error(f"Error validating schedule: {e}")
        return False

def validate_credit_balance(client: Dict) -> bool:
    """
    Validate if client has sufficient credit balance.

    Args:
        client: Client dict from API response containing credits object

    Returns:
        bool: True if balance > 20, False otherwise
    """
    try:
        balance = client.get("credits", {}).get("balance", 0)
        # balance = 100
        if balance <= 20:
            logging.info(f"Insufficient credit balance: {balance}")
            return False
        return True
    except Exception as e:
        logging.error(f"Error validating credit balance: {e}")
        return False

def validate_campaign_status(campaigns: list) -> bool:
    """
    Validate if campaign status is active.

    Args:
        campaigns: List of campaign dicts from API response

    Returns:
        bool: True if status is active, False otherwise
    """
    try:
        if not campaigns:
            logging.info("No campaigns found")
            return False

        status = campaigns[0].get("status")
        # status = "active"
        if status != "active":
            logging.info(f"Campaign status is {status}, not active")
            return False

        return True

    except Exception as e:
        logging.error(f"Error validating campaign status: {e}")
        return False

def validate_agent_availability(full_config: Dict) -> Tuple[bool, str]:
    """
    Main validation function that checks all conditions.

    Args:
        full_config: Full API response dict

    Returns:
        tuple: (is_valid: bool, failure_reason: str)
    """
    if not full_config:
        return False, "No configuration loaded"

    campaigns = full_config.get("campaigns", [])
    if not campaigns:
        return False, "No campaigns found"

    campaign = campaigns[0]
    client = campaign.get("client", {})
    schedule = campaign.get("schedule", {})

    # Check schedule
    if not validate_campaign_schedule(schedule):
        return False, "Outside scheduled hours"

    # Check credit balance
    if not validate_credit_balance(client):
        return False, "Insufficient credit balance"

    # Check campaign status
    if not validate_campaign_status(campaigns):
        return False, "Campaign not active"

    return True, ""

async def hangup_call():
    """
    End the call by deleting the room.
    """
    ctx = get_job_context()
    if ctx is None:
        logging.warning("No job context available for hangup")
        return

    try:
        await ctx.api.room.delete_room(
            api.DeleteRoomRequest(room=ctx.room.name)
        )
        logging.info("Call hung up due to validation failure")
    except Exception as e:
        logging.error(f"Error hanging up call: {e}")