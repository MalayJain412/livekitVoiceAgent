# Auto Hangup Implementation Approach

Of course. Your approach is exactly right, and **yes, you can manage function calls from the agent at runtime to control the session**.

The standard way to do this is by creating a tool that the agent can call. This tool doesn't return a value in the traditional sense; instead, it signals your main script to proceed with the hang-up sequence. The best way to send this signal in an `asyncio` application is with an `asyncio.Event`.

Think of an `asyncio.Event` as a digital flag 🚩. The main part of your code can pause and wait for the flag to be raised. Your `end_call` tool's only job is to raise that flag.

Here is a complete, step-by-step guide to implement this.

## Step 1: Create the `end_call` Tool

First, let's define the tool. This function will accept the `asyncio.Event` as an argument and set it when called.

In your `tools.py` file, add the following function:

```python
# tools.py
import asyncio
from livekit.agents import aio

# ... (your other tool functions)

async def end_call(hangup_event: asyncio.Event):
    """
    Signals that the conversation is over and the call should be terminated.
    Use this tool when the user wants to hang up or the conversation's goal is met.
    """
    print("end_call tool was called, setting hangup event.") # For debugging
    hangup_event.set()
    return "Call termination sequence initiated."
```

## Step 2: Update the Agent to Use the Tool

Now, we need to make the `Assistant` aware of this tool and give it access to the `hangup_event` flag. We'll pass the event into the agent's constructor.

In your `cagent.py` file, modify the `Assistant` class:

```python
# cagent.py
import functools # NEW: Import functools

# ... (other imports)

class Assistant(Agent):
    # MODIFIED: Update the constructor to accept the hangup_event
    def __init__(self, custom_instructions=None, hangup_event: asyncio.Event = None):
        instances = get_default_instances()
        instructions = custom_instructions if custom_instructions else AGENT_INSTRUCTION

        # NEW: Create a partial function for our tool to include the hangup_event
        # This "bakes" the event into the tool before giving it to the agent.
        end_call_tool = functools.partial(end_call, hangup_event=hangup_event)
        
        # This is needed to help the LLM understand the tool's documentation
        end_call_tool.__doc__ = end_call.__doc__

        super().__init__(
            instructions=instructions,
            llm=instances["llm"],
            # MODIFIED: Add the new tool to the agent's toolkit
            tools=[get_weather, search_web, triotech_info, create_lead, detect_lead_intent, end_call_tool],
        )
    
    # ... (the rest of the Assistant class is unchanged)
```

## Step 3: Orchestrate Everything in the `entrypoint`

This is where we'll create the `asyncio.Event`, pass it to the agent, and wait for it to be set. This replaces the `await asyncio.Future()` line, which waits forever.

In `cagent.py`, update the `entrypoint` function:

```python
# cagent.py

async def entrypoint(ctx: JobContext):
    # ... (setup code and validation logic is unchanged)
    # ...
    
    # --- Start of the "Success Case" logic ---

    # This code runs only if the validation passes
    else:
        logging.info("PERSONA_USE=local: Skipping validation checks, allowing all calls to proceed")
    
    # NEW: Create the hangup event (our digital flag)
    hangup_event = asyncio.Event()

    # MODIFIED: Pass the hangup_event to the Assistant
    agent = Assistant(custom_instructions=agent_instructions, hangup_event=hangup_event)
    logging.info(f"Created agent with persona instructions for: {persona_name}")

    # ... (getting instances and creating AgentSession is unchanged)
    # ...
    session = AgentSession(...)

    # ... (attaching persona and setting up SessionManager is unchanged)
    # ...
    
    await session.start(...)
    
    # ... (logging, starting history watcher is unchanged)
    # ...

    if session_instructions:
        initial_instruction = session_instructions
        logging.info(f"Using persona session instructions for: {persona_name}")
    else:
        initial_instruction = SESSION_INSTRUCTION
        logging.info("Using default session instruction")
    
    # Start the conversation
    await session.generate_reply(instructions=initial_instruction)
    
    # --- REPLACEMENT FOR asyncio.Future() ---
    logging.info("Agent is running, waiting for hangup signal...")
    await hangup_event.wait() # This will pause here until the end_call tool is used
    logging.info("Hangup signal received.")

    # --- HANGUP SEQUENCE ---
    # Play the pre-defined closing message from the persona config
    if closing_message:
        logging.info(f"Playing closing message: {closing_message}")
        await session.say(closing_message)
    
    await hangup_call()
    logging.info("Call has been successfully terminated.")
    # No need for return, the function will end naturally
```

## Step 4: Update the Agent's Instructions

Finally, you must tell the LLM *when* to use its new tool. This is the most important part for making the AI behave correctly.

In your `prompts.py` file (or wherever you define `AGENT_INSTRUCTION`), add a clear rule:

```python
# prompts.py

AGENT_INSTRUCTION = """
You are a helpful voice assistant... (your existing instructions)

**Ending the Conversation:**
When the user indicates the conversation is over (e.g., by saying "goodbye," "thank you for your time," "hang up," etc.) or when you have fulfilled their request and there is nothing else to discuss, you MUST use the `end_call` tool to terminate the conversation. Do not say goodbye yourself; the system will handle the closing message after you call the tool.
"""
```

## How It All Works Together 🏁

1. The `entrypoint` starts, creates the `hangup_event` flag, and gives it to the `Assistant`.
2. The code reaches `await hangup_event.wait()` and pauses, keeping the call active.
3. You and the agent have a conversation.
4. You say, "Okay, thank you for your help, goodbye."
5. The LLM, following its instructions, sees this as a trigger to end the call.
6. It calls the `end_call` tool.
7. The `end_call` function in `tools.py` is executed, which calls `hangup_event.set()`. This raises the flag 🚩.
8. The `await hangup_event.wait()` line in your `entrypoint` immediately unblocks.
9. The code proceeds to the hangup sequence: it plays your `closing_message`, calls `hangup_call()`, and the script finishes.
