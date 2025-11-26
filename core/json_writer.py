import json

class JSONWriter:
    def __init__(self, path):
        self.path = path

    def write(self, data):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
