from core.extractor_service import ExtractorService
from config.settings import INVOICES_FOLDER, OUTPUT_JSON, OUTPUT_CSV

if __name__ == "__main__":
    service = ExtractorService(INVOICES_FOLDER, OUTPUT_JSON, OUTPUT_CSV)
    service.run()
