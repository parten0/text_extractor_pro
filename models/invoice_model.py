class InvoiceModel:
    def __init__(self):
        self.metadata = {}

    def add_metadata(self, data):
        self.metadata.update(data)

    def to_dict(self):
        return {
            "metadata": self.metadata
        }
