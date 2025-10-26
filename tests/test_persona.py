import asyncio
from cagent import load_persona_from_dialed_number

async def test():
    result = await load_persona_from_dialed_number('8655054859')
    agent_instructions, session_instructions, closing_message, persona_name, full_config = result
    print('Success!')
    print(f'Persona Name: {persona_name}')
    print(f'Agent Instructions preview: {agent_instructions[:300]}...')
    if 'You are Imran' in agent_instructions:
        print('✅ Found API personality!')
    else:
        print('❌ API personality not found')

asyncio.run(test())