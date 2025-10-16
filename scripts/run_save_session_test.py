from transcript_logger import save_conversation_session

print('Invoking save_conversation_session with empty items to fetch from DB')
res = save_conversation_session([], metadata={'invoked_by':'test_script'})
print('Result:', res)
