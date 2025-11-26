# 📄 Doc Extractor Pro

> *Because manually reading invoices is so 2020...* 🚀

## 🎯 Project Description

Picture this: A client had a folder full of invoices and needed to extract specific information from each one. Time was ticking, deadlines were looming, and manually opening each PDF was about as fun as watching paint dry. 

Enter **Doc Extractor Pro** - your friendly neighborhood invoice extraction superhero! 🦸‍♂️

My brain went: *"PYTHON!"* (because when doesn't it?) and I decided to vibe code a solution that would save the day. Armed with [`pdfplumber`](https://github.com/jsvine/pdfplumber) (a genuinely good library, I must say) and some geometric wizardry, I pinpointed the exact text needed using coordinates. But here's the plot twist - sometimes coordinates just wouldn't cooperate because text positions changed like a chameleon on a disco floor. So I brought in the big guns: fuzzy search with specific text patterns. Because when geometry fails, regex saves! 💪

**The Flow:**
1. 📁 `pdfplumber` reads each PDF from the `invoices/` folder
2. 🎯 Extracts text using coordinate-based extraction (with fuzzy search as backup)
3. 📝 Writes the extracted data to `output.json`
4. 📊 Converts JSON to a beautiful CSV (`output.csv`) for easy analysis
5. 🎉 Client gets their data, you get the credit, everyone wins!

## 🚀 Quick Start

### Prerequisites

- Python 3.7 or higher
- A folder full of invoices (or at least one, we're not picky)

### Installation

1. Clone this repository (or download it, we're flexible):
```bash
git clone <your-repo-url>
cd doc_extractor_pro
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

That's it! No complicated setup, no 47-step installation process. Just good old `pip install` and you're ready to rock! 🎸

### Configuration

Before running, make sure you have:

1. **Invoices folder**: Create an `invoices/` folder in the project root and place your PDF files there
2. **Coordinates file**: The `coordinates.txt` file should be in the project root (already included)
   - This file defines the bounding boxes for text extraction
   - Format: JavaScript object with field coordinates

### Running the Application

Simply run:
```bash
python app.py
```

That's it! No flags, no complicated commands. Just `python app.py` and watch the magic happen! ✨

The application will:
- Process all PDFs in the `invoices/` folder
- Extract data based on coordinates defined in `coordinates.txt`
- Search for "INVOICETOTAL:" using fuzzy matching
- Generate `output.json` with all extracted data
- Create `output.csv` with a nice tabular format

## 📁 Project Structure

```
doc_extractor_pro/
├── app.py                 # Main entry point
├── config/
│   └── settings.py        # Configuration settings
├── core/
│   ├── extractor_service.py  # Main extraction logic
│   ├── json_writer.py        # JSON output handler
│   └── csv_writer.py         # CSV output handler
├── models/
│   └── invoice_model.py     # Invoice data model
├── parsers/
│   └── kv_parser.py          # Key-value parser
├── readers/
│   └── pdf_reader.py          # PDF reading wrapper
├── utils/
│   └── coordinates_parser.py  # Coordinate parsing logic
├── invoices/               # Place your PDFs here (gitignored)
├── coordinates.txt        # Coordinate definitions
├── output.json            # Generated JSON output (gitignored)
├── output.csv             # Generated CSV output (gitignored)
└── requirements.txt       # Python dependencies
```

## ⚙️ How It Works

### Coordinate-Based Extraction

The application uses `coordinates.txt` to define specific regions on the PDF where text should be extracted. Each field has:
- Top-left (TL) and bottom-right (BR) coordinates
- Page number
- Field name

### Fuzzy Search Fallback

For fields that can't be pinned down with coordinates (like "INVOICETOTAL:" which moves around like a cat avoiding bath time), the app uses regex pattern matching to find and extract the value.

### Output Format

**JSON (`output.json`):**
```json
{
  "invoice1.pdf": {
    "metadata": {
      "customer": "...",
      "invoicenumber": "...",
      "vatnum": "...",
      "date": "...",
      "invoice_total": "ZWG500.00"
    }
  }
}
```

**CSV (`output.csv`):**
- First column: `filename`
- Subsequent columns: All metadata keys
- One row per invoice

## 🛠️ Customization

### Adding New Fields

1. Add coordinates to `coordinates.txt`:
```javascript
newfield_TL: { x: 100, y: 200, page: 1 },
newfield_BR: { x: 300, y: 250, page: 1 },
```

2. The application will automatically extract and include it in the output!

### Modifying Search Patterns

Edit the `_extract_invoice_total()` method in `core/extractor_service.py` to add or modify fuzzy search patterns.

## 📝 Notes

- The `invoices/` folder, `output.json`, and `output.csv` are gitignored (because who wants to commit generated files?)
- Make sure your PDFs are readable and not corrupted (we're good, but we're not miracle workers)
- Coordinate system uses top-left origin (0,0 at top-left corner)

## 🤝 Contributing

Found a bug? Have an idea? Want to add more features? Feel free to open an issue or submit a PR! We're all about that collaborative coding vibe! 🎨

## 📄 License

MIT License - Do whatever you want with it. Use it, modify it, sell it, make it dance. Just don't blame us if something goes wrong (though we're pretty sure it won't). 😎

See [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [`pdfplumber`](https://github.com/jsvine/pdfplumber) - For being an awesome PDF library
- Python - For existing (seriously, where would we be without it?)
- Coffee - For keeping developers awake during late-night coding sessions ☕

---

*Made with ❤️ and a healthy dose of Python magic*

