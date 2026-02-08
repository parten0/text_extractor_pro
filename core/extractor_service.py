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
    def __init__(self, invoices_folder, coordinates_file=None, progress_callback=None):
        self.invoices_folder = invoices_folder
        self.kv_parser = KVParser()
        self.progress_callback = progress_callback  # Optional callback for progress updates
        
        # Create invoices folder if it doesn't exist
        os.makedirs(self.invoices_folder, exist_ok=True)
        
        # Load coordinates if provided
        if coordinates_file is None:
            # Default to coordinates.txt in project root
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            coordinates_file = os.path.join(project_root, "coordinates.txt")
        
        self.coordinates_parser = CoordinatesParser(coordinates_file)
        self.coordinates = self.coordinates_parser.parse()
        
        # Create outputs directory at project root (no subfolders)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.outputs_folder = os.path.join(project_root, "outputs")
        self.json_folder = self.outputs_folder  # Same as outputs folder
        self.csv_folder = self.outputs_folder   # Same as outputs folder
        os.makedirs(self.outputs_folder, exist_ok=True)

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

    def _extract_date_special(self, page):
        """Extract Date-Special: Find line containing both 'Date:' and 'Order', extract the date"""
        # Extract full page text to search for Date-Special
        full_text = page.extract_text()
        
        if not full_text:
            return None
        
        # Split text into lines
        lines = full_text.split('\n')
        
        for line in lines:
            # Check if line contains both "Date:" (case-insensitive) and "Order" (case-insensitive)
            if re.search(r'Date\s*:', line, re.IGNORECASE) and re.search(r'Order', line, re.IGNORECASE):
                # Extract the date value after "Date:" and before "Order"
                # Pattern: Date: <date> ... Order
                # The date can be in various formats: "01/15/2024", "2024-01-15", "Jan 15, 2024", etc.
                # Match everything after "Date:" until we hit "Order" (case-insensitive) or end of line
                # Use positive lookahead to stop at "Order" without consuming it
                match = re.search(r'Date\s*:\s*(.*?)(?=\s*Order|$)', line, re.IGNORECASE)
                if match:
                    date_value = match.group(1).strip()
                    # Clean up: remove any trailing punctuation, whitespace, or common separators
                    date_value = date_value.rstrip('.,;: \t')
                    if date_value:
                        return date_value
        
        return None

    def _clean_customer_field(self, text):
        """Remove 'Invoice to:' prefix from customer field if present"""
        if not text:
            return text
        
        # Remove "Invoice to:" prefix (case-insensitive, with optional colon)
        # Handle both single-line and multi-line cases
        # Pattern matches "Invoice to:" or "Invoice to" at the start, optionally followed by newline
        text = re.sub(r'^Invoice\s+to\s*:\s*\n?', '', text, flags=re.IGNORECASE | re.MULTILINE)
        
        return text.strip()

    def _extract_special_customer(self, page):
        """Extract special customer: Find 'Invoice to:' and take 3 lines below it at the same indentation level"""
        # Extract full page text
        full_text = page.extract_text()
        
        if not full_text:
            return None
        
        # Split text into lines
        lines = full_text.split('\n')
        
        # Find line containing "Invoice to:"
        for i, line in enumerate(lines):
            if re.search(r'Invoice\s+to\s*:', line, re.IGNORECASE):
                # Get the indentation level (leading whitespace) of the "Invoice to:" line
                invoice_to_indent = len(line) - len(line.lstrip())
                
                # Look for 3 lines below at the same indentation level
                customer_lines = []
                lines_found = 0
                
                for j in range(i + 1, min(i + 4, len(lines))):
                    current_line = lines[j]
                    current_indent = len(current_line) - len(current_line.lstrip())
                    
                    # Check if indentation matches (allow small tolerance of ±2 spaces)
                    if abs(current_indent - invoice_to_indent) <= 2:
                        customer_lines.append(current_line.strip())
                        lines_found += 1
                        if lines_found >= 3:
                            break
                    else:
                        # If we hit a line with different indentation, stop
                        break
                
                if customer_lines:
                    customer_text = '\n'.join(customer_lines).strip()
                    if customer_text:
                        return customer_text
        
        return None

    def _extract_spec_customer_1_from_special_customer(self, special_customer_text):
        """Extract spec_customer_1 from special_customer by removing 'Vat No: <text>\\n' and '\\nTin No: <text>' patterns"""
        if not special_customer_text:
            return None
        
        # Remove "Vat No: <some text>\n" pattern (case-insensitive)
        text = re.sub(r'Vat\s+No\s*:\s*[^\n]+\n', '', special_customer_text, flags=re.IGNORECASE)
        
        # Remove "\nTin No: <some text>" pattern (case-insensitive)
        text = re.sub(r'\nTin\s+No\s*:\s*[^\n]+', '', text, flags=re.IGNORECASE)
        
        # Clean up any extra whitespace/newlines and return
        text = text.strip()
        
        return text if text else None

    def _extract_spec_customer_2_from_spec_customer_1(self, spec_customer_1_text):
        """Extract spec_customer_2 from spec_customer_1 by removing 'CUSTOMER: ' prefix"""
        if not spec_customer_1_text:
            return None
        
        # Remove "CUSTOMER: " prefix (case-insensitive)
        text = re.sub(r'^CUSTOMER\s*:\s*', '', spec_customer_1_text, flags=re.IGNORECASE)
        
        # Clean up any extra whitespace and return
        text = text.strip()
        
        return text if text else None

    def _extract_spec_customer_3_from_spec_customer_2(self, spec_customer_2_text):
        """Extract spec_customer_3 from spec_customer_2: if 'CUSTOMER:' found, take text after it, otherwise use spec_customer_2"""
        if not spec_customer_2_text:
            return None
        
        # Search for "CUSTOMER:" in the text (case-insensitive)
        match = re.search(r'CUSTOMER\s*:\s*(.+)', spec_customer_2_text, re.IGNORECASE)
        if match:
            # If found, extract text after "CUSTOMER:"
            text = match.group(1).strip()
            return text if text else None
        else:
            # If not found, return the original spec_customer_2 value
            return spec_customer_2_text.strip() if spec_customer_2_text.strip() else None

    def _extract_spec_customer_4_from_spec_customer_3(self, spec_customer_3_text):
        """Extract spec_customer_4 from spec_customer_3: if 'FISCAL TAX INVOICE' found at beginning, take text after it, otherwise use spec_customer_3"""
        if not spec_customer_3_text:
            return None
        
        # Search for "FISCAL TAX INVOICE" at the beginning of the text (case-insensitive)
        # Pattern matches "FISCAL TAX INVOICE" followed by a space and then captures the rest
        match = re.match(r'FISCAL\s+TAX\s+INVOICE\s+(.+)', spec_customer_3_text, re.IGNORECASE)
        if match:
            # If found, extract text after "FISCAL TAX INVOICE" (space is the delimiter)
            text = match.group(1).strip()
            return text if text else None
        else:
            # If not found, return the original spec_customer_3 value
            return spec_customer_3_text.strip() if spec_customer_3_text.strip() else None

    def _extract_spec_vat(self, page):
        """Extract spec_vat: Search for 'Vat No:' or 'CUSTOMER VAT:' and get text in front of it on same line"""
        # Extract full page text
        full_text = page.extract_text()
        
        if not full_text:
            return None
        
        # Split text into lines
        lines = full_text.split('\n')
        
        # First try: Search for exact "Vat No:" and get any text on the same line
        # Collect all matches - need at least 2 matches, then take the last one
        vat_matches = []
        
        for line in lines:
            # Try pattern: text before "Vat No:" (exact match)
            match = re.search(r'(.+?)\s+Vat\s+No\s*:', line, re.IGNORECASE)
            if match:
                vat_number = match.group(1).strip()
                # Make sure we actually captured something meaningful (not just whitespace)
                if vat_number and len(vat_number) > 0:
                    vat_matches.append(vat_number)
            
            # Try pattern: text after "Vat No:" (exact match) on the same line
            match = re.search(r'Vat\s+No\s*:\s*(.+)', line, re.IGNORECASE)
            if match:
                vat_number = match.group(1).strip()
                if vat_number:
                    vat_matches.append(vat_number)
        
        # Only return if we have 2 or more matches, then take the last one
        if len(vat_matches) >= 2:
            return vat_matches[-1]
        
        # Fallback: Search for exact "CUSTOMER VAT:" and get text AFTER it on the same line
        for line in lines:
            # Pattern: "CUSTOMER VAT:" (exact match) followed by any text on the same line
            match = re.search(r'CUSTOMER\s+VAT\s*:\s*(.+)', line, re.IGNORECASE)
            if match:
                vat_number = match.group(1).strip()
                if vat_number:
                    return vat_number
        
        return None

    def _extract_invoice_numbers(self, page):
        """Extract invoice_number_1 and invoice_number_2: Find all 'Invoice No:' occurrences and extract text that follows, stopping at 3 consecutive spaces"""
        # Extract full page text
        full_text = page.extract_text()
        
        if not full_text:
            return None, None
        
        # Split text into lines
        lines = full_text.split('\n')
        
        invoice_numbers = []
        
        for line in lines:
            # Search for all "Invoice No:" occurrences (case-insensitive)
            # Pattern: Match "Invoice No:" followed by any text, stopping at 3 consecutive spaces or end of line
            matches = re.finditer(r'Invoice\s+No\s*:\s*(.+?)(?:\s{3,}|$)', line, re.IGNORECASE)
            for match in matches:
                invoice_text = match.group(1).strip()
                # Remove any trailing spaces that might have been captured
                invoice_text = invoice_text.rstrip()
                if invoice_text:
                    invoice_numbers.append(invoice_text)
        
        # Return first and second match (or None if not found)
        invoice_number_1 = invoice_numbers[0] if len(invoice_numbers) > 0 else None
        invoice_number_2 = invoice_numbers[1] if len(invoice_numbers) > 1 else None
        
        return invoice_number_1, invoice_number_2

    def _process_pdf(self, pdf_path):
        """Process a single PDF file and return invoice data"""
        invoice = InvoiceModel()
        
        # Collect invoice numbers across all pages first
        all_invoice_numbers = []

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
                        
                        # Clean customer field: remove "Invoice to:" prefix if present
                        if field_name == "customer":
                            text = self._clean_customer_field(text)
                        
                        # Always store under the coordinate field name
                        # Also try to parse key-value pairs and add them separately if found
                        invoice.add_metadata({field_name: text})
                        
                        # Additionally, parse key-value pairs from the text and add them
                        # This allows fields like "Invoiceto:" to also be accessible
                        parsed = self.kv_parser.parse(text)
                        if parsed:
                            # Clean customer field if it comes from parsed data
                            if "customer" in parsed:
                                parsed["customer"] = self._clean_customer_field(parsed["customer"])
                            # Also check for "Invoice to" key and clean it
                            for key in list(parsed.keys()):
                                if "invoice" in key.lower() and "to" in key.lower():
                                    # This might be "Invoice to" key, move to customer and clean
                                    if "customer" not in parsed:
                                        parsed["customer"] = self._clean_customer_field(parsed[key])
                                    del parsed[key]
                            invoice.add_metadata(parsed)
                else:
                    # Fallback: full page extraction
                    invoice.add_metadata(self.kv_parser.parse(extracted_data))
                
                # Extract INVOICE TOTAL from the page (searches full page text)
                invoice_total = self._extract_invoice_total(page)
                if invoice_total:
                    invoice.add_metadata({"invoice_total": invoice_total})
                
                # Extract Date-Special from the page (searches for line with both "Date:" and "Order")
                date_special = self._extract_date_special(page)
                if date_special and "Date-Special" not in invoice.metadata:
                    invoice.add_metadata({"Date-Special": date_special})
                
                # Extract special customer (3 lines below "Invoice to:" at same indentation)
                special_customer = self._extract_special_customer(page)
                if special_customer and "special_customer" not in invoice.metadata:
                    invoice.add_metadata({"special_customer": special_customer})
                    # Extract spec_customer_1 from special_customer
                    spec_customer_1 = self._extract_spec_customer_1_from_special_customer(special_customer)
                    if spec_customer_1:
                        invoice.add_metadata({"spec_customer_1": spec_customer_1})
                        # Extract spec_customer_2 from spec_customer_1 by removing "CUSTOMER: " prefix
                        spec_customer_2 = self._extract_spec_customer_2_from_spec_customer_1(spec_customer_1)
                        if spec_customer_2:
                            invoice.add_metadata({"spec_customer_2": spec_customer_2})
                            # Extract spec_customer_3 from spec_customer_2
                            spec_customer_3 = self._extract_spec_customer_3_from_spec_customer_2(spec_customer_2)
                            if spec_customer_3:
                                invoice.add_metadata({"spec_customer_3": spec_customer_3})
                                # Extract spec_customer_4 from spec_customer_3
                                spec_customer_4 = self._extract_spec_customer_4_from_spec_customer_3(spec_customer_3)
                                if spec_customer_4:
                                    invoice.add_metadata({"spec_customer_4": spec_customer_4})
                
                # Extract spec_vat (text before "Vat No:" or "CUSTOMER VAT:" on same line)
                spec_vat = self._extract_spec_vat(page)
                if spec_vat and "spec_vat" not in invoice.metadata:
                    invoice.add_metadata({"spec_vat": spec_vat})
                
                # Collect invoice numbers from this page
                invoice_number_1, invoice_number_2 = self._extract_invoice_numbers(page)
                if invoice_number_1:
                    all_invoice_numbers.append(invoice_number_1)
                if invoice_number_2:
                    all_invoice_numbers.append(invoice_number_2)
            
            # Add invoice_number_1 and invoice_number_2 from all collected matches
            if len(all_invoice_numbers) > 0:
                invoice.add_metadata({"invoice_number_1": all_invoice_numbers[0]})
                # Extract invoice_number_1_variant (text before first space)
                invoice_number_1_variant = all_invoice_numbers[0].split()[0] if all_invoice_numbers[0] else None
                if invoice_number_1_variant:
                    invoice.add_metadata({"invoice_number_1_variant": invoice_number_1_variant})
            if len(all_invoice_numbers) > 1:
                invoice.add_metadata({"invoice_number_2": all_invoice_numbers[1]})

        return invoice.to_dict()

    def run(self):
        """Process all PDFs in subfolders of the invoices folder"""
        print("Starting invoice processing...")
        
        # Get all subfolders in the invoices folder
        if not os.path.exists(self.invoices_folder):
            print(f"Error: Invoices folder '{self.invoices_folder}' not found")
            return
        
        # Get all subdirectories in invoices folder
        subfolders = [f for f in os.listdir(self.invoices_folder) 
                     if os.path.isdir(os.path.join(self.invoices_folder, f))]
        
        if not subfolders:
            print(f"No subfolders found in {self.invoices_folder}")
            return
        
        # Process each subfolder
        for folder_name in sorted(subfolders):
            folder_path = os.path.join(self.invoices_folder, folder_name)
            
            # Get all PDF files in this subfolder
            pdf_pattern = os.path.join(folder_path, "*.pdf")
            pdf_files = sorted(glob.glob(pdf_pattern))
            
            if not pdf_files:
                continue
            
            # Process each PDF in the folder
            invoices_data = {}
            for idx, pdf_path in enumerate(pdf_files, 1):
                filename = os.path.basename(pdf_path)
                try:
                    # Call progress callback if provided
                    if self.progress_callback:
                        self.progress_callback(idx, len(pdf_files))
                    
                    invoice_data = self._process_pdf(pdf_path)
                    invoices_data[filename] = invoice_data
                except Exception as e:
                    continue
            
            # Generate JSON and CSV for this folder
            if invoices_data:
                # Generate JSON file in json subfolder
                json_filename = f"{folder_name}.json"
                json_path = os.path.join(self.json_folder, json_filename)
                json_writer = JSONWriter(json_path)
                json_writer.write(invoices_data)
                
                # Generate CSV file in csv subfolder
                csv_filename = f"{folder_name}.csv"
                csv_path = os.path.join(self.csv_folder, csv_filename)
                csv_writer = CSVWriter(csv_path)
                csv_writer.write(invoices_data)
                print(f"Processed folder '{folder_name}': {len(invoices_data)} invoice(s) -> json/{json_filename}, csv/{csv_filename}")
        
        print("Processing complete.")