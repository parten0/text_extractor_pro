import csv
import os

class CSVWriter:
    def __init__(self, path):
        self.path = path

    def write(self, data):
        """
        Write invoice data to CSV file.
        Data structure: {filename: {"metadata": {...}}, ...}
        CSV structure: filename, Date, VAT, Invoice Number, Customer, USD, Zig
        """
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        
        if not data:
            # Create empty CSV file with headers
            with open(self.path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["filename", "Date", "VAT", "Invoice Number", "Customer", "USD", "Zig"])
            return

        # Define the column headers and their corresponding metadata keys
        columns = [
            ("filename", None),  # Special handling for filename
            ("Date", "Date-Special"),
            ("VAT", "spec_vat"),
            ("Invoice Number", "invoice_number_1_variant"),
            ("Customer", "spec_customer_4"),
            ("USD", "invoice_total"),  # Special handling for invoice_total
            ("Zig", "invoice_total"),  # Special handling for invoice_total
        ]
        
        # Create CSV with specific columns
        with open(self.path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            
            # Write header
            header = [col[0] for col in columns]
            writer.writerow(header)
            
            # Write data rows
            for filename, invoice_data in sorted(data.items()):
                row = []
                metadata = invoice_data.get("metadata", {})
                
                for col_name, metadata_key in columns:
                    if col_name == "filename":
                        row.append(filename)
                    elif col_name in ["USD", "Zig"]:
                        # Special handling for invoice_total - split into USD and Zig
                        invoice_total = metadata.get("invoice_total", "")
                        invoice_total_str = str(invoice_total) if invoice_total is not None else ""
                        
                        if col_name == "USD":
                            # If invoice_total starts with "USD", extract the value
                            if invoice_total_str.upper().startswith("USD"):
                                # Remove "USD" prefix and any whitespace, keep the rest
                                value = invoice_total_str[3:].strip()
                                row.append(value)
                            else:
                                row.append("")
                        elif col_name == "Zig":
                            # If invoice_total starts with "ZWG", extract the value
                            if invoice_total_str.upper().startswith("ZWG"):
                                # Remove "ZWG" prefix and any whitespace, keep the rest
                                value = invoice_total_str[3:].strip()
                                row.append(value)
                            else:
                                row.append("")
                    else:
                        # Regular field mapping
                        value = metadata.get(metadata_key, "")
                        row.append(str(value) if value is not None else "")
                
                writer.writerow(row)

