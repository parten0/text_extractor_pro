import json
import os

class JSONWriter:
    def __init__(self, path):
        self.path = path

    def write(self, data):
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
