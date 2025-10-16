import time
from transcript_logger import generate_session_id, log_event, flush_and_stop, get_log_path

# Generate a session id
sid = generate_session_id()
print('Generated session id:', sid)

# Log a couple of events
log_event({'role':'user','content':'Hello from test','timestamp':'2025-10-15T00:00:00Z'})
log_event({'role':'assistant','content':'Hi, this is a reply','timestamp':'2025-10-15T00:00:01Z'})

# Wait for worker to flush
time.sleep(1)

# Trigger flush and stop which should auto-save conversation if DB available
flush_and_stop()
print('Flush and stop invoked; check MongoDB and conversations directory for saved session')
