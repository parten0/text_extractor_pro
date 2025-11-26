import pdfplumber

class PDFReader:
    def __init__(self, path):
        self.path = path
        self.pdf = None

    def __enter__(self):
        self.pdf = pdfplumber.open(self.path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.pdf:
            self.pdf.close()

    def pages(self):
        if self.pdf is None:
            self.pdf = pdfplumber.open(self.path)
        return self.pdf.pages
