# Smart Document Finder 2.0 — Upgrade Notes

## Critical regressions fixed

1. `ResultCard` no longer contains `MainWindow` initialization, window sizing, search state or voice state.
2. `MainWindow` owns the single `VoiceAssistant` instance and its signal handlers.
3. Result cards use a Qt signal instead of replacing `mouseReleaseEvent` with a lambda.
4. Hard-coded result-card window sizing was removed.

## Search correctness

- Exact word/phrase matching replaces unsafe substring matching.
- Specific attributes such as 10th/12th, semester and year are retained as query constraints.
- CamelCase filenames such as `12thMarksheet.pdf` are normalized for ranking.
- Search returns up to five ranked results.
- SQLite FTS5 improves recall for larger libraries.
- Hindi/Unicode text is preserved during normalization.
- Common Hindi/Hinglish document terms are mapped to canonical search terms.

## Indexing

- Open Folder actually indexes the selected folder.
- Scanning is recursive by default.
- Incremental indexing skips unchanged files using size/modified-time checks.
- SHA-256 is stored for indexed files for future integrity/duplicate workflows.
- Live file watching triggers a debounced incremental refresh.
- Stale records from a previously selected root are removed.
- Extraction failures are stored instead of silently disappearing.

## Document support

- PDF embedded text is extracted page-by-page.
- Scanned/low-text PDF pages can fall back to OCR individually.
- DOCX paragraphs, tables, headers and footers are indexed.
- XLSX is indexed from worksheet cells.
- XLS is supported through `xlrd`.
- Images are OCR indexed.
- Office/text files have a text preview fallback in the viewer.

## UI/viewer

- Modern responsive PySide6 layout.
- No application state is hidden inside result cards.
- Recent Documents now means recently opened documents.
- PDF page navigation and zoom controls are state-aware.
- Save, Reveal and Open actions work from the viewer.
- Qt standard icons are used instead of font-dependent symbol glyphs.

## Deployment changes

The distribution ZIP intentionally excludes:

- `.venv`
- `venv`
- `__pycache__`
- the personal `data/documents.db`
- local editor files

The first run creates a fresh local index when you select your folder.
