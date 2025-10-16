from db_config import get_collection

def list_recent_sessions(limit=10):
    col = get_collection('conversation_sessions')
    docs = list(col.find().sort('created_at', -1).limit(limit))
    for d in docs:
        print('session_id:', d.get('session_id'), 'created_at:', d.get('created_at'))

def count_transcript_events():
    col = get_collection('transcript_events')
    print('transcript_events count:', col.count_documents({}))

if __name__ == '__main__':
    print('Conversation sessions:')
    list_recent_sessions()
    count_transcript_events()
