import csv
import os

class CSVWriter:
    def __init__(self, path):
        self.path = path

    def write(self, data):
        """
        Write invoice data to CSV file.
        Data structure: {filename: {"metadata": {...}}, ...}
        CSV structure: filename column + all metadata keys as columns
        """
        if not data:
            # Create empty CSV file
            with open(self.path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["filename"])
            return

        # Collect all unique keys across all invoices
        all_keys = set()
        for invoice_data in data.values():
            if "metadata" in invoice_data:
                all_keys.update(invoice_data["metadata"].keys())
        
        # Filter out date columns except "Date-Special"
        # Also exclude vatnum and invoicenumber
        # Common date field names to exclude (case-insensitive check)
        date_keywords = ['date']
        excluded_fields = ['vatnum', 'invoicenumber']
        filtered_keys = []
        for key in all_keys:
            key_lower = key.lower()
            # Exclude vatnum and invoicenumber
            if key_lower in excluded_fields:
                continue
            # Keep "Date-Special" but exclude other date fields
            if key == "Date-Special":
                filtered_keys.append(key)
            elif any(keyword in key_lower for keyword in date_keywords):
                # Skip this date column (it's not Date-Special)
                continue
            else:
                filtered_keys.append(key)
        
        # Sort keys for consistent column order
        all_keys = sorted(filtered_keys)
        
        # Create CSV with filename as first column, then all metadata keys
        with open(self.path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            
            # Write header: filename + all metadata keys
            header = ["filename"] + all_keys
            writer.writerow(header)
            
            # Write data rows
            for filename, invoice_data in sorted(data.items()):
                row = [filename]
                metadata = invoice_data.get("metadata", {})
                
                # Add values for each key (empty string if key not present)
                for key in all_keys:
                    value = metadata.get(key, "")
                    # Convert to string and handle None values
                    row.append(str(value) if value is not None else "")
                
                writer.writerow(row)

