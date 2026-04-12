import os
from datetime import datetime
with open('config/session-active.lock', 'w') as f:
    f.write(datetime.now().isoformat())
