from core.extractor_service import ExtractorService
from config.settings import INVOICES_FOLDER

if __name__ == "__main__":
    service = ExtractorService(INVOICES_FOLDER)
    service.run()
