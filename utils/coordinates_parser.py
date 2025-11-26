import re
import os

class CoordinatesParser:
    def __init__(self, coordinates_file):
        self.coordinates_file = coordinates_file
        self.coordinates = {}
    
    def parse(self):
        """Parse coordinates.txt file and return a dictionary of bounding boxes"""
        if not os.path.exists(self.coordinates_file):
            print(f"Warning: {self.coordinates_file} not found. Using full page extraction.")
            return {}
        
        with open(self.coordinates_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse JavaScript object format
        # Extract field definitions: fieldname_TL: { x: num, y: num, page: num }
        pattern = r'(\w+)_(TL|TR|BL|BR):\s*\{\s*x:\s*(\d+),\s*y:\s*(\d+),\s*page:\s*(\d+)\s*\}'
        matches = re.findall(pattern, content)
        
        # Group coordinates by field name
        fields = {}
        for match in matches:
            field_name = match[0]  # e.g., "customer", "invoicenumber"
            corner = match[1]  # TL, TR, BL, BR
            x = int(match[2])
            y = int(match[3])
            page = int(match[4])
            
            if field_name not in fields:
                fields[field_name] = {}
            if page not in fields[field_name]:
                fields[field_name][page] = {}
            
            fields[field_name][page][corner] = (x, y)
        
        # Convert to bounding boxes (x0, top, x1, bottom) for pdfplumber
        # pdfplumber uses (x0, top, x1, bottom) where (0,0) is bottom-left
        # We'll store the raw coordinates and convert using page height at extraction time
        bounding_boxes = {}
        
        for field_name, pages in fields.items():
            for page_num, corners in pages.items():
                if 'TL' in corners and 'BR' in corners:
                    # Get bounding box coordinates (assuming top-left origin in file)
                    x0 = min(corners['TL'][0], corners['BR'][0])
                    x1 = max(corners['TL'][0], corners['BR'][0])
                    y_top = max(corners['TL'][1], corners['BR'][1])  # Top in file's coordinate system
                    y_bottom = min(corners['TL'][1], corners['BR'][1])  # Bottom in file's coordinate system
                    
                    key = f"{field_name}_page_{page_num}"
                    bounding_boxes[key] = {
                        'x0': x0,
                        'x1': x1,
                        'y_top': y_top,  # Top coordinate (will convert using page height)
                        'y_bottom': y_bottom,  # Bottom coordinate (will convert using page height)
                        'page': page_num - 1,  # Convert to 0-indexed
                        'field': field_name
                    }
        
        return bounding_boxes

