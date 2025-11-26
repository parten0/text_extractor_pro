class KVParser:
    def parse(self, text):
        data = {}
        for line in text.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                if key.strip() and value.strip():
                    data[key.strip()] = value.strip()
        return data
