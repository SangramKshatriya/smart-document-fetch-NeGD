# Smart Document Finder 3.1 — Indic Multilingual Edition

A local-first PySide6 desktop document finder with OCR, FTS5 search, live indexing, recent-document history and an Indian-language service layer.

## What this version adds

- Language selector with Auto Detect plus English and the 22 scheduled Indian languages.
- Provider abstraction: `sarvam`, `bhashini`, or `none/local`.
- Sarvam REST integration for language identification, translation, speech-to-text and text-to-speech. Transliteration remains available for non-critical UI/voice use.
- Generic BHASHINI pipeline adapter with service IDs kept in environment variables.
- Strict multilingual document flow: detect → translate to English → extract document name only → search/fetch.
- Code-mix friendly voice path when the Sarvam provider is configured.
- Indic-script detection fallback when remote language detection is unavailable.
- Safer multilingual OCR configuration that uses only Tesseract language packs actually installed.
- Asynchronous search/language processing so remote API calls do not block the PySide6 UI.
- Provider/API smoke-test scripts and a setup checker.
- Minimal search-first UI: no folder picker, no speak-result control, and a collapsible Recent panel.
- The document folder is supplied in the terminal when starting the app.

## Provider choice

### Recommended first setup: Sarvam

Set in `.env`:

```text
LANGUAGE_PROVIDER=sarvam
SARVAM_API_KEY=your_key
```

Sarvam currently documents REST endpoints for:

- `POST /text-lid` for language identification
- `POST /translate` for translation
- `POST /transliterate` for script conversion
- `POST /speech-to-text` for speech recognition
- `POST /text-to-speech` for speech output

The provider layer uses these endpoints and keeps API keys out of source code.

### BHASHINI

Set:

```text
LANGUAGE_PROVIDER=bhashini
BHASHINI_API_KEY=your_key
```

Then fill in the service IDs discovered from your selected BHASHINI pipelines:

```text
BHASHINI_TRANSLATION_SERVICE_ID=
BHASHINI_ASR_SERVICE_ID=
BHASHINI_TTS_SERVICE_ID=
BHASHINI_LID_SERVICE_ID=
BHASHINI_TRANSLITERATION_SERVICE_ID=
```

Do not copy service IDs from an old tutorial blindly; choose the current pipeline/model from the BHASHINI developer portal.

## Windows setup

1. Install Python 3.11.
2. Install Tesseract OCR and the Indic language packs you intend to OCR.
3. Open the extracted project folder in VS Code.
4. Create the environment:

```powershell
py -3.11 -m venv .venv
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

5. Copy `.env.example` to `.env`.
6. Add your provider API key.
7. Run the setup check:

```powershell
python scripts/check_setup.py
```

8. Start the app. The terminal will ask for the document folder:

```powershell
python app.py
```

Or supply the folder directly:

```powershell
python app.py "C:\Users\YourName\Documents"
```

For a full rebuild of the index:

```powershell
python app.py "C:\Users\YourName\Documents" --reindex
```

`run.ps1` and `run.bat` forward the same arguments to `app.py`. The desktop UI intentionally does not contain a folder picker.

## Tesseract

The application reads `TESSERACT_CMD` and `OCR_LANGUAGES` from `.env`.
Only languages installed in your local Tesseract installation are used. For a first Indic rollout, install English, Hindi, Marathi, Gujarati, Tamil, Telugu, Kannada, Malayalam, Bengali, Punjabi, Odia and Assamese packs and configure:

```text
OCR_LANGUAGES=eng+hin+mar+guj+tam+tel+kan+mal+ben+pan+ori+asm
```

## API smoke test

After adding your key:

```powershell
python scripts/test_remote_language_services.py
```

This tests LID, translation, transliteration and TTS. Voice STT requires a real microphone recording, so test it through the application or with your own audio fixture.

## Search flow

A document request now follows one strict path:

```text
user text / voice
    ↓
language detection
    ↓
translate the request to English
    ↓
extract ONLY the document name (plus grade/year constraints)
    ↓
match that document against local files and, when configured, DigiLocker issued documents
    ↓
fetch/open only the matched document
```

For DigiLocker, the app searches the authenticated user's already-issued-document list and downloads only the selected URI. It does not invent issuer-specific identifiers.

The document itself is not translated just to make search work. Original OCR/text remains local; translation is primarily used to normalize the user's request. This avoids sending an entire personal document library to a translation service.

## DigiLocker configuration

DigiLocker access is optional and requires an approved Requester integration plus a valid user OAuth access token. Put the token in `DIGILOCKER_ACCESS_TOKEN`. Issuer/document metadata discovery also requires `DIGILOCKER_CLIENT_ID` and `DIGILOCKER_CLIENT_SECRET`.

The app supports the documented issued-document list and file-by-URI flow. Pulling a new document is deliberately separate because DigiLocker issuers can require different parameters and explicit user consent. The project exposes discovery/pull methods but does not guess identity fields.

## Important production note

For a desktop prototype, `.env` is convenient. For a product distributed to many users, do not embed provider or DigiLocker client secrets in the executable. Put credentialed calls behind a backend or a properly registered OAuth desktop integration, and apply user-level authentication, rate limits and audit logging.

## Tests

```powershell
pytest -q
```

## UI behavior

- Search Results are hidden when the app starts.
- A successful search automatically opens the results drawer.
- The `Recent` button toggles the results drawer; clicking it again hides the drawer.
- `Speak Result`, `Open Folder`, and `Rebuild Index` are intentionally removed from the UI.
- Document-folder selection is terminal-only to keep the UI focused on search.

## Main folders

```text
language/     language codes, script detection, query preparation
services/     provider adapters and speech services
ui/           PySide6 interface and voice handling
extraction/  document extraction/OCR helpers
storage/      SQLite data layer
scripts/      setup and API smoke tests
data/         generated local index (not distributed)
```
