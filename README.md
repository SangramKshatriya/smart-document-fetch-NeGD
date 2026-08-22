# smart-document-fetch-NeGD



# Smart Document Fetch

A local, intelligent document retrieval and preview application built with Python.

Smart Document Fetch allows users to provide a folder containing their documents and search for files using natural-language queries such as:

> "Give me my PAN card"

> "Find my Aadhaar"

> "Show my marksheet"

The application searches across filenames and extracted document content and displays relevant files. Images, PDFs, and text documents can be previewed directly inside the application.

---

## Features

* Recursive scanning of a user-selected document folder
* Search across files stored in subfolders
* Filename-based document retrieval
* Content-based document retrieval
* Natural-language-style search queries
* PDF text extraction
* DOCX text extraction
* XLSX spreadsheet content extraction
* TXT file extraction
* OCR support for JPG, JPEG, PNG, and scanned PDFs
* Image preprocessing using OpenCV before OCR
* Tesseract OCR integration
* Local SQLite document index
* Ranked search results
* In-application document preview
* Image zoom controls
* PDF page navigation
* PDF zoom controls
* Fit-to-page and fit-to-width modes
* Actual-size viewing
* Fullscreen document preview
* Local-first architecture without requiring cloud document storage

---

## Example

Suppose the configured folder contains:

```text
My_imp_docs/
│
├── adhaar.pdf
├── adhaar_front.jpg
├── adhaar_back.jpg
├── PAN_Card.pdf
├── Resume.docx
│
└── result/
    ├── sem1_res.pdf
    ├── sem2_res.pdf
    └── sem7_res.pdf
```

The user can enter:

```text
my adhaar
```

The application can return:

```text
1. adhaar.pdf
2. adhaar_back.jpg
3. adhaar_front.jpg
```

The user can then select a result and preview the document inside the application.

---

## Architecture

The application follows a modular pipeline:

```text
                    USER
                      │
                      ▼
                ┌───────────┐
                │   app.py  │
                └─────┬─────┘
                      │
                  User Query
                      │
                      ▼
             ┌─────────────────┐
             │ search_engine.py│
             └────────┬────────┘
                      │
                      ▼
               ┌─────────────┐
               │ SQLite Index│
               └──────┬──────┘
                      ▲
                      │
                ┌─────┴─────┐
                │ indexer.py│
                └─────┬─────┘
                      │
            ┌─────────┴──────────┐
            │                    │
            ▼                    ▼
      scanner.py        content_extractor.py
                               │
             ┌─────────────────┼─────────────────┐
             │                 │                 │
             ▼                 ▼                 ▼
          PyMuPDF         python-docx        openpyxl
             │
             ▼
        OCR fallback
             │
             ▼
      ocr_engine.py
             │
             ▼
        Tesseract OCR
```

---

## Project Structure

```text
smart-document-fetch/
│
├── app.py
├── config.py
├── scanner.py
├── content_extractor.py
├── ocr_engine.py
├── database.py
├── indexer.py
├── search_engine.py
├── query_processor.py
├── file_watcher.py
├── preview.py
├── requirements.txt
├── .gitignore
│
└── data/
    └── documents.db
```

### `app.py`

Main PySide6 desktop application.

Responsible for:

* GUI creation
* Search input
* Search result display
* Document selection
* Document preview
* Image/PDF viewing controls
* Zooming
* Fullscreen mode
* PDF page navigation

### `config.py`

Stores configuration values such as:

* Supported file extensions
* Database location
* Data directory

### `scanner.py`

Recursively scans the selected folder and identifies supported files.

It collects metadata such as:

* Filename
* Full path
* File extension
* File size
* Modification time

### `content_extractor.py`

Extracts searchable text from supported document formats.

Supported extraction includes:

* PDF
* DOCX
* XLSX
* TXT
* Images through OCR
* Scanned PDFs through OCR fallback

### `ocr_engine.py`

Provides OCR functionality using:

* Tesseract
* pytesseract
* Pillow
* OpenCV
* PyMuPDF

Image preprocessing is applied before OCR to improve recognition quality.

### `database.py`

Creates and manages the local SQLite database used for document indexing.

### `indexer.py`

Connects the scanner and content extractor to the database.

The indexing process is:

```text
Scan files
    ↓
Extract metadata
    ↓
Extract document content
    ↓
Store/update database
```

### `search_engine.py`

Processes user queries and searches the indexed documents.

The current retrieval approach uses keyword matching and weighted scoring.

Filename matches receive stronger relevance than content matches.

### `query_processor.py`

Reserved for query-processing functionality and future improvements to natural-language interpretation.

### `file_watcher.py`

Reserved for filesystem monitoring.

It can be used to detect:

* New files
* Modified files
* Deleted files
* Renamed files

and update the document index automatically.

### `preview.py`

Contains preview-related utilities and file-type handling.

---

## Supported File Types

The current system supports or is designed to support:

| File Type | Processing                     |
| --------- | ------------------------------ |
| PDF       | Text extraction + OCR fallback |
| JPG       | OCR + image preview            |
| JPEG      | OCR + image preview            |
| PNG       | OCR + image preview            |
| DOCX      | Text/table extraction          |
| XLSX      | Cell extraction                |
| XLS       | Planned/partial support        |
| TXT       | Text extraction                |

---

## OCR Pipeline

Scanned documents require OCR because they may contain images rather than machine-readable text.

The OCR pipeline is:

```text
Scanned PDF / Image
        ↓
Render / Load Image
        ↓
Grayscale conversion
        ↓
Noise reduction
        ↓
Contrast enhancement
        ↓
Thresholding
        ↓
Image upscaling
        ↓
Tesseract OCR
        ↓
Extracted text
        ↓
SQLite index
```

For PDFs, the application first attempts normal text extraction.

If no embedded text is found, OCR is automatically used.

```text
PDF
 ↓
Normal text extraction
 ↓
Text found?
 ├── Yes → Store extracted text
 │
 └── No  → Render page → OCR → Store text
```

---

## Search Workflow

When the user enters:

```text
give me my adhaar
```

the system performs roughly:

```text
User query
    ↓
Normalize query
    ↓
Remove unnecessary stop words
    ↓
Generate useful search terms
    ↓
Search indexed documents
    ↓
Calculate relevance score
    ↓
Sort results
    ↓
Display matching files
```

Example:

```text
"give me my adhaar"
```

can become:

```text
adhaar
```

and the application can return files such as:

```text
adhaar.pdf
adhaar_front.jpg
adhaar_back.jpg
```

---

## Search Ranking

The current search implementation uses a simple weighted scoring approach.

Conceptually:

```text
Filename match  → higher score
Content match   → lower score
```

This allows a filename such as:

```text
PAN_Card.pdf
```

to receive a stronger ranking for a query such as:

```text
PAN card
```

while also allowing documents whose extracted content contains relevant words to appear in the results.

---

## Document Preview

The application includes an integrated document viewer.

### Images

Supported:

```text
JPG
JPEG
PNG
```

Features include:

* Zoom in
* Zoom out
* Actual size
* Fit page
* Fit width
* Fullscreen

### PDF

Features include:

* PDF page rendering
* Previous page
* Next page
* Page counter
* Zoom in/out
* Fit page
* Fit width
* Actual size
* Fullscreen

### Text

Text documents can be displayed in a scrollable viewer with adjustable text size.

---

## Technologies Used

### Programming Language

* Python

### GUI

* PySide6

### Document Processing

* PyMuPDF
* python-docx
* openpyxl
* Pillow

### OCR

* Tesseract OCR
* pytesseract
* OpenCV

### Database

* SQLite

### File Monitoring

* watchdog

### Version Control

* Git
* GitHub

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/smart-document-fetch.git
```

Move into the project:

```bash
cd smart-document-fetch
```

### 2. Create a virtual environment

Windows:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.venv\Scripts\activate
```

### 3. Install Python dependencies

```powershell
pip install -r requirements.txt
```

### 4. Install Tesseract OCR

Tesseract OCR must be installed separately because `pytesseract` is the Python interface to the Tesseract OCR engine.

Typical Windows installation path:

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
```

The application can be configured to use this executable.

---

## Running the Application

### Build the document index

Run:

```powershell
python indexer.py
```

Enter the folder containing your documents.

Example:

```text
D:\a_Document\Highly important\My_imp_docs
```

The indexer scans the folder recursively, extracts content, performs OCR when necessary, and stores the results in SQLite.

### Start the application

Run:

```powershell
python app.py
```

Then enter a natural-language query such as:

```text
give me my adhaar
```

or:

```text
find my marksheet
```

or:

```text
show my PAN card
```

---

## Privacy

This application is designed primarily as a local document retrieval system.

Documents remain on the user's local machine during normal operation.

The application indexes local files into a local SQLite database.

### Important

The local database may contain extracted document content. Therefore:

* Do not commit `data/documents.db` to Git.
* Do not commit personal PAN/Aadhaar files.
* Do not commit OCR debug images.
* Do not commit the Python virtual environment.

These items should be excluded using `.gitignore`.

---

## Current Limitations

The current implementation has several areas that can be improved.

### 1. Keyword-based retrieval

The current search engine mainly relies on keyword matching and weighted scoring.

It does not yet provide full semantic understanding.

For example, a query such as:

```text
show my tax identification document
```

may not always understand that the user is referring to a PAN card.

### 2. OCR accuracy

OCR may produce incorrect characters when documents have:

* complex backgrounds
* low resolution
* unusual fonts
* multiple languages
* logos
* security patterns

### 3. Large-scale indexing

The current SQLite-based implementation is suitable for a personal/local document collection but is not designed as a large-scale search infrastructure.

### 4. Advanced document previews

More complete DOCX and XLSX visual previews can be added.

### 5. Automatic file monitoring

Filesystem monitoring can be integrated so newly added or modified files are automatically indexed.

---

## Future Improvements

Possible future upgrades include:

### Semantic Search

Use embeddings to understand the meaning of queries instead of relying only on exact keywords.

Example:

```text
"tax identification document"
            ↓
       semantic search
            ↓
       PAN_Card.pdf
```

### Vector Database

Add a vector store for efficient semantic retrieval.

Possible technologies include:

* FAISS
* Chroma
* Qdrant

### Hybrid Search

Combine:

```text
Keyword Search
        +
Semantic Search
        +
Metadata filtering
```

for better retrieval accuracy.

### Automatic File Monitoring

Use `watchdog` to automatically detect:

```text
New file
Modified file
Deleted file
Renamed file
```

and update the index.

### More File Formats

Possible additions:

* PPTX
* CSV
* HTML
* RTF
* additional document formats

### Better OCR

Possible improvements include:

* multilingual OCR
* document-specific preprocessing
* automatic orientation detection
* OCR confidence scoring
* field extraction

### AI-based Query Understanding

A language model could interpret queries such as:

```text
"show me the document I use for income tax"
```

and identify:

```text
PAN card
```

without requiring the user to use the exact words.

---

## Example End-to-End Flow

```text
                 USER
                  │
                  │
          "Give me my PAN card"
                  │
                  ▼
             Query Parser
                  │
                  ▼
           Search Engine
                  │
                  ▼
           SQLite Index
                  │
       ┌──────────┴──────────┐
       │                     │
   Filename               Content
   Matching               Matching
       │                     │
       └──────────┬──────────┘
                  ▼
             Ranked Results
                  │
                  ▼
          ┌───────────────┐
          │ PAN_Card.pdf  │
          │ PAN.jpg       │
          └───────┬───────┘
                  │
                  ▼
           Document Viewer
                  │
           ┌──────┴───────┐
           │              │
          PDF           Image
           │              │
       PyMuPDF         QPixmap
           │              │
           └──────┬───────┘
                  ▼
             User Views
             Document
```

---

## Project Objective

The main objective of Smart Document Fetch is to provide a simple local interface for retrieving personal documents without requiring the user to remember exact filenames or manually browse through multiple folders.

Instead of asking the user to remember:

```text
D:\Documents\Important\Identity\PAN_2025_Final.pdf
```

the user can simply ask:

```text
give me pan card
```

and retrieve the relevant document through the application.

---

## License

This project can be licensed according to the requirements of the repository owner.

---

## Author

**Anshul Chaudhary**

Built as a Python-based intelligent document retrieval and preview project.
