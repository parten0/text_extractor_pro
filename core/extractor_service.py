import os
import glob
import re
from readers.pdf_reader import PDFReader
from parsers.kv_parser import KVParser
from core.json_writer import JSONWriter
from core.csv_writer import CSVWriter
from models.invoice_model import InvoiceModel
from utils.coordinates_parser import CoordinatesParser


class ExtractorService:
    def __init__(self, invoices_folder, output_json_path, output_csv_path=None, coordinates_file=None):
        self.invoices_folder = invoices_folder
        self.kv_parser = KVParser()
        self.json_writer = JSONWriter(output_json_path)
        self.csv_writer = CSVWriter(output_csv_path) if output_csv_path else None
        
        # Load coordinates if provided
        if coordinates_file is None:
            # Default to coordinates.txt in project root
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            coordinates_file = os.path.join(project_root, "coordinates.txt")
        
        self.coordinates_parser = CoordinatesParser(coordinates_file)
        self.coordinates = self.coordinates_parser.parse()
        print(self.coordinates)

    def _extract_text_from_coordinates(self, page, page_index):
        """Extract text only from defined coordinate regions and return as dict with field names"""
        if not self.coordinates:
            # No coordinates defined, extract full page
            return page.extract_text()
        
        # Get page dimensions for coordinate conversion
        page_height = page.height
        
        # Collect text from all coordinate regions for this page, keyed by field name
        extracted_data = {}
        
        for key, coord_info in self.coordinates.items():
            if coord_info['page'] == page_index:
                # Convert coordinates: file uses top-left origin, pdfplumber uses bottom-left
                x0 = coord_info['x0']
                x1 = coord_info['x1']
                # Convert y coordinates: y_top in file -> bottom in pdfplumber, y_bottom in file -> top in pdfplumber
                bottom = page_height - coord_info['y_top']  # Top in file = bottom in pdfplumber
                top = page_height - coord_info['y_bottom']  # Bottom in file = top in pdfplumber
                
                # Extract text from this bounding box
                bbox = (x0, bottom, x1, top)
                cropped_page = page.crop(bbox)
                text = cropped_page.extract_text()
                
                field_name = coord_info['field']
                # Debug output
                print(f"Field: {field_name}, BBox: {bbox}, Text extracted: {repr(text[:100]) if text else 'EMPTY'}")
                
                # Store text with field name as key (even if empty, we'll handle it later)
                if field_name not in extracted_data:
                    extracted_data[field_name] = text if text else ""
                else:
                    # If field already exists, append with newline
                    extracted_data[field_name] += "\n" + (text if text else "")
        
        return extracted_data

    def _extract_invoice_total(self, page):
        """Extract INVOICE TOTAL value from the page text"""
        # Extract full page text to search for INVOICE TOTAL
        full_text = page.extract_text()
        
        if not full_text:
            return None
        
        # Pattern 1: Match "INVOICETOTAL:" (no space) - this is what appears in the PDF
        # Handles: "Date INVOICETOTAL: ZWG500.00" or just "INVOICETOTAL: ZWG500.00"
        pattern1 = r'INVOICETOTAL\s*:\s*([^\n\r]+)'
        match1 = re.search(pattern1, full_text, re.IGNORECASE)
        if match1:
            invoice_total = match1.group(1).strip()
            return invoice_total
        
        # Pattern 2: Match "INVOICE TOTAL:" (with space) - fallback
        pattern2 = r'INVOICE\s+TOTAL\s*:\s*([^\n\r]+)'
        match2 = re.search(pattern2, full_text, re.IGNORECASE)
        if match2:
            invoice_total = match2.group(1).strip()
            return invoice_total
        
        return None

    def _process_pdf(self, pdf_path):
        """Process a single PDF file and return invoice data"""
        invoice = InvoiceModel()

        with PDFReader(pdf_path) as reader:
            for page_index, page in enumerate(reader.pages()):
                # Extract text only from defined coordinates
                extracted_data = self._extract_text_from_coordinates(page, page_index)
                
                # Process extracted data: if it's a dict (from coordinates), use field names as keys
                # Otherwise, parse with KVParser (fallback for full page extraction)
                if isinstance(extracted_data, dict):
                    # For coordinate-based extraction, always use the coordinate field name as the key
                    for field_name, text in extracted_data.items():
                        text = text.strip() if text else ""
                        if not text:
                            continue
                        
                        # Always store under the coordinate field name
                        # Also try to parse key-value pairs and add them separately if found
                        invoice.add_metadata({field_name: text})
                        
                        # Additionally, parse key-value pairs from the text and add them
                        # This allows fields like "Invoiceto:" to also be accessible
                        parsed = self.kv_parser.parse(text)
                        if parsed:
                            invoice.add_metadata(parsed)
                else:
                    # Fallback: full page extraction
                    invoice.add_metadata(self.kv_parser.parse(extracted_data))
                
                # Extract INVOICE TOTAL from the page (searches full page text)
                invoice_total = self._extract_invoice_total(page)
                if invoice_total:
                    print(f"Found INVOICE TOTAL: {invoice_total}")
                    invoice.add_metadata({"invoice_total": invoice_total})
                else:
                    print("INVOICE TOTAL not found on this page")

        return invoice.to_dict()

    def run(self):
        """Process all PDFs in the invoices folder"""
        # Get all PDF files from the invoices folder
        pdf_pattern = os.path.join(self.invoices_folder, "*.pdf")
        pdf_files = sorted(glob.glob(pdf_pattern))

        if not pdf_files:
            print(f"No PDF files found in {self.invoices_folder} folder")
            self.json_writer.write({})
            if self.csv_writer:
                self.csv_writer.write({})
            return

        # Process each PDF and collect results with filename as key
        invoices_data = {}
        for pdf_path in pdf_files:
            filename = os.path.basename(pdf_path)
            print(f"Processing: {pdf_path}")
            try:
                invoice_data = self._process_pdf(pdf_path)
                invoices_data[filename] = invoice_data
            except Exception as e:
                print(f"Error processing {pdf_path}: {e}")
                continue

        # Write all invoices as an object with filenames as keys
        self.json_writer.write(invoices_data)
        print(f"Processed {len(invoices_data)} invoice(s) and saved JSON to {self.json_writer.path}")
        
        # Write CSV file if CSV writer is configured
        if self.csv_writer:
            self.csv_writer.write(invoices_data)
            print(f"Saved CSV to {self.csv_writer.path}")