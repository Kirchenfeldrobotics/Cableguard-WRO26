import json
import os
from pathlib import Path

class Outbox:
    def __init__(self, path="outbox.jsonl"): 
        self._path  = Path(path)
        self._sent = 0

    def add_msg(self, msg): 
        with open (self._path, "a") as f: 
            f.write(json.dumps(msg) + "\n")
            f.flush()
            os.fsync(f.fileno())

    def pending(self): 
        if not self.path.exists(): 
            return []
        lines = self._path.read_text().splitlines()
        return [json.loads(l) for l in lines[self._sent:]]

    def mark_sent(self, count): 
        self._sent += count