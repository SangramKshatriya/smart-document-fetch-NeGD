"""Browser interface for Smart Document Finder.

The existing PySide6 desktop application remains available through app.py.
This module is the WSGI entry point used by Render: ``gunicorn web_app:app``.
"""
from __future__ import annotations

import hmac
import mimetypes
import os
import re
import secrets
import time
import unicodedata
import uuid
from functools import wraps
from pathlib import Path
from typing import Callable

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from werkzeug.exceptions import RequestEntityTooLarge
from dotenv import load_dotenv

# Load .env for local runs; Render environment variables take precedence.
load_dotenv()

from config import SUPPORTED_EXTENSIONS
from database import (
    end_session,
    get_all_documents,
    get_document_count,
    get_document_history,
    get_recent_documents,
    get_search_history,
    get_user_stats,
    get_or_create_user,
    initialize_database,
    log_audit_event,
    record_document_access,
    record_login_attempt,
    record_search_history,
    start_session,
)
from indexer import index_file, index_folder
from language.manager import LanguageManager
from query_processor import extract_constraints
from search_engine import search_documents_multilingual
from services.provider_factory import build_provider
from scanner import scan_folder

BASE_DIR = Path(__file__).resolve().parent
DOCUMENT_ROOT = Path(os.getenv("DOCUMENT_FOLDER", "/documents")).expanduser().resolve()
UPLOAD_ROOT = DOCUMENT_ROOT / "uploads"
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
ALLOWED_EXTENSIONS = set(SUPPORTED_EXTENSIONS)
LANGUAGE_OPTIONS = [
    ("", "Auto detect"),
    ("en-IN", "English"),
    ("hi-IN", "Hindi"),
    ("bn-IN", "Bengali"),
    ("gu-IN", "Gujarati"),
    ("kn-IN", "Kannada"),
    ("ml-IN", "Malayalam"),
    ("mr-IN", "Marathi"),
    ("or-IN", "Odia"),
    ("pa-IN", "Punjabi"),
    ("ta-IN", "Tamil"),
    ("te-IN", "Telugu"),
]


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.getenv("WEB_APP_SECRET_KEY") or os.getenv("SECRET_KEY") or secrets.token_hex(32)
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES + 1024 * 1024
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = (
        os.getenv("SESSION_COOKIE_SECURE", "true" if os.getenv("RENDER") else "false").lower()
        == "true"
    )

    @app.context_processor
    def inject_template_helpers():
        def csrf_token() -> str:
            token = session.get("_csrf_token")
            if not token:
                token = secrets.token_urlsafe(32)
                session["_csrf_token"] = token
            return token

        return {"csrf_token": csrf_token}

    @app.before_request
    def protect_post_requests():
        if request.method == "POST":
            expected = session.get("_csrf_token", "")
            supplied = request.form.get("_csrf_token", "")
            if not expected or not supplied or not hmac.compare_digest(expected, supplied):
                abort(400, description="The form expired or failed its security check. Refresh the page and try again.")

    def login_required(view: Callable):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("authenticated"):
                return redirect(url_for("login", next=request.path))
            return view(*args, **kwargs)
        return wrapped

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "Smart Document Finder"}, 200

    @app.route("/login", methods=["GET", "POST"])
    def login():
        access_password = os.getenv("WEB_APP_PASSWORD", "")
        if not access_password:
            return render_template("login.html", setup_required=True), 503

        if request.method == "POST":
            submitted_password = request.form.get("password", "")
            if not hmac.compare_digest(submitted_password, access_password):
                record_login_attempt(status="FAIL", reason="invalid_web_password")
                flash("The access password is incorrect.", "error")
                return render_template("login.html", setup_required=False), 401

            display_name = (request.form.get("display_name", "") or "Web user").strip()[:120]
            raw_username = (request.form.get("username", "") or display_name).strip().lower()
            username = re.sub(r"[^a-z0-9_.-]+", "_", raw_username).strip("_.-")[:40]
            username = username or f"web-{uuid.uuid4().hex[:10]}"
            user = get_or_create_user(username, display_name or username)
            session.clear()
            session["_csrf_token"] = secrets.token_urlsafe(32)
            session["authenticated"] = True
            session["username"] = user["username"]
            session["display_name"] = user["display_name"]
            try:
                session["session_id"] = start_session(user["username"], user["display_name"])
            except Exception:
                app.logger.exception("Unable to start activity session")
                session.clear()
                flash("Could not initialize activity history. Check the database configuration.", "error")
                return render_template("login.html", setup_required=False), 503
            record_login_attempt(
                username=user["username"], display_name=user["display_name"],
                status="PASS", reason="web_login",
            )
            log_audit_event(
                "WEB_LOGIN", username=user["username"], display_name=user["display_name"],
                session_id=session.get("session_id"), details={"method": "password"}, status="PASS",
            )
            return redirect(url_for("index"))

        return render_template("login.html", setup_required=False)

    @app.post("/logout")
    @login_required
    def logout():
        session_id = session.get("session_id")
        username = session.get("username", "")
        display_name = session.get("display_name", "")
        try:
            end_session(session_id, "web_logout")
            log_audit_event(
                "WEB_LOGOUT", username=username, display_name=display_name,
                session_id=session_id, details={"method": "password"}, status="PASS",
            )
        except Exception:
            app.logger.exception("Unable to record web logout")
        session.clear()
        flash("You have been logged out.", "success")
        return redirect(url_for("login"))

    @app.get("/")
    @login_required
    def index():
        try:
            count = get_document_count()
            recent = get_recent_documents(5)
        except Exception:
            app.logger.exception("Unable to read the document index")
            count, recent = 0, []
            flash("The document index could not be read. Check database and storage settings.", "error")
        return render_template(
            "index.html", document_count=count, recent_documents=recent,
            languages=LANGUAGE_OPTIONS, selected_language="", results=None,
            query="", canonical_query="", language_message="",
        )

    @app.post("/search")
    @login_required
    def search():
        query = (request.form.get("query", "") or "").strip()[:1000]
        preferred_language = (request.form.get("language", "") or "").strip()
        started = time.perf_counter()
        results = []
        canonical_query = ""
        language_message = ""
        prepared = None
        error_message = ""

        if not query:
            flash("Enter a document name or a query to search.", "error")
        else:
            try:
                provider = build_provider()
                manager = LanguageManager(provider)
                prepared = manager.prepare_query(query, preferred_language=preferred_language or None)
                canonical_query = prepared.canonical_english or query
                results = search_documents_multilingual(
                    prepared.original,
                    canonical_query=prepared.canonical_english,
                    transliterated_query=prepared.transliterated,
                    document_type=prepared.document_type,
                    constraints=extract_constraints(prepared.canonical_english or prepared.original),
                    limit=10,
                )
                language_message = (
                    f"Detected: {prepared.language_code or 'unknown'} · "
                    f"Search provider: {prepared.provider_used or 'local'}"
                )
                if prepared.provider_error:
                    language_message += f" · Language-service note: {prepared.provider_error}"
            except Exception as error:
                app.logger.exception("Search failed")
                error_message = str(error)
                flash("Search failed. Please check the server logs and language-service configuration.", "error")

        duration_ms = int((time.perf_counter() - started) * 1000)
        search_history_id = None
        try:
            search_history_id = record_search_history(
                username=session.get("username", "web-user"),
                display_name=session.get("display_name", "Web user"),
                session_id=session.get("session_id"),
                original_query=query,
                canonical_query=canonical_query,
                detected_language=(getattr(prepared, "language_code", None) or "") if prepared else "",
                preferred_language=preferred_language,
                input_mode="text",
                provider=(getattr(prepared, "provider_used", None) or "") if prepared else "",
                document_type=(getattr(prepared, "document_type", None) or "") if prepared else "",
                duration_ms=duration_ms,
                results_count=len(results),
                success=bool(results) and not error_message,
                error_message=error_message or (getattr(prepared, "provider_error", "") if prepared else ""),
            )
            log_audit_event(
                "WEB_SEARCH", username=session.get("username", "web-user"),
                display_name=session.get("display_name", "Web user"), session_id=session.get("session_id"),
                details={"query": query, "canonical_query": canonical_query,
                         "results_count": len(results), "duration_ms": duration_ms},
                status="PASS" if results and not error_message else "FAIL",
            )
        except Exception:
            app.logger.exception("Unable to write search history")

        return render_template(
            "index.html", document_count=get_document_count(), recent_documents=get_recent_documents(5),
            languages=LANGUAGE_OPTIONS, selected_language=preferred_language, results=results,
            query=query, canonical_query=canonical_query, language_message=language_message,
            search_history_id=search_history_id,
        )

    @app.post("/scan")
    @login_required
    def scan():
        try:
            DOCUMENT_ROOT.mkdir(parents=True, exist_ok=True)
            stats = index_folder(str(DOCUMENT_ROOT), force=False)
            flash(
                f"Scan complete: {stats['total']} files found, {stats['changed']} indexed/updated, "
                f"{stats['skipped']} unchanged, {stats['errors']} extraction errors.",
                "success" if stats["errors"] == 0 else "warning",
            )
            log_audit_event(
                "WEB_INDEX_SCAN", username=session.get("username", "web-user"),
                display_name=session.get("display_name", "Web user"), session_id=session.get("session_id"),
                details=stats, status="PASS" if stats["errors"] == 0 else "FAIL",
            )
        except Exception as error:
            app.logger.exception("Document scan failed")
            flash(f"Document scan failed: {error}", "error")
        return redirect(url_for("index"))

    @app.post("/upload")
    @login_required
    def upload():
        uploaded = request.files.get("file")
        if not uploaded or not uploaded.filename:
            flash("Choose a file first.", "error")
            return redirect(url_for("index"))

        # Strip client-supplied path components; retain readable Unicode names.
        raw_name = uploaded.filename.replace("\\", "/").split("/")[-1]
        safe_name = "".join(ch for ch in unicodedata.normalize("NFKC", raw_name) if ord(ch) >= 32)
        safe_name = safe_name.strip(" .")[:180]
        extension = Path(safe_name).suffix.lower()
        if not safe_name or extension not in ALLOWED_EXTENSIONS:
            flash("Unsupported file type. Upload PDF, JPG, PNG, DOCX, XLSX, XLS, or TXT files.", "error")
            return redirect(url_for("index"))
        if uploaded.content_length and uploaded.content_length > MAX_UPLOAD_BYTES:
            flash("Each file must be 25 MB or smaller.", "error")
            return redirect(url_for("index"))

        try:
            UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
            # A unique per-file directory prevents overwrites while preserving the document's name for search.
            destination_dir = UPLOAD_ROOT / uuid.uuid4().hex
            destination_dir.mkdir(parents=True, exist_ok=False)
            destination = destination_dir / safe_name
            uploaded.save(destination)
            if destination.stat().st_size > MAX_UPLOAD_BYTES:
                destination.unlink(missing_ok=True)
                destination_dir.rmdir()
                flash("Each file must be 25 MB or smaller.", "error")
                return redirect(url_for("index"))
            stat = destination.stat()
            index_info = {
                "name": destination.name,
                "path": str(destination.resolve()),
                "extension": destination.suffix.lower(),
                "size": stat.st_size,
                "modified_time": stat.st_mtime,
            }
            outcome = index_file(index_info, force=True)
            if outcome.get("error"):
                flash(f"Uploaded {safe_name}, but text extraction reported: {outcome['error']}", "warning")
            else:
                flash(f"Uploaded and indexed {safe_name}.", "success")
            log_audit_event(
                "WEB_UPLOAD", username=session.get("username", "web-user"),
                display_name=session.get("display_name", "Web user"), session_id=session.get("session_id"),
                details={"name": safe_name, "size": stat.st_size, "extension": extension}, status="PASS",
            )
        except Exception as error:
            app.logger.exception("Upload/index failed")
            flash(f"Upload failed: {error}", "error")
        return redirect(url_for("index"))

    @app.get("/documents/<int:document_id>")
    @login_required
    def view_document(document_id: int):
        row = next((item for item in get_all_documents() if int(item["id"]) == document_id), None)
        if row is None:
            abort(404)
        path = Path(row["path"]).resolve()
        root = DOCUMENT_ROOT.resolve()
        try:
            path.relative_to(root)
        except ValueError:
            abort(404)
        if not path.is_file() or path.suffix.lower() not in ALLOWED_EXTENSIONS:
            abort(404)
        mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        inline = path.suffix.lower() in {".pdf", ".jpg", ".jpeg", ".png"}
        try:
            record_document_access(
                username=session.get("username", "web-user"),
                display_name=session.get("display_name", "Web user"),
                session_id=session.get("session_id"), document_name=row["name"],
                document_path=str(path), document_id=document_id, source="local",
                action="view" if inline else "download", document_type=row["document_type"] or "",
                success=True,
            )
        except Exception:
            app.logger.exception("Unable to write document-access history")
        return send_file(path, mimetype=mime_type, as_attachment=not inline, download_name=path.name)

    @app.get("/history")
    @login_required
    def history():
        username = session.get("username", "web-user")
        try:
            searches = get_search_history(username, 30)
            accesses = get_document_history(username, 30)
            stats = get_user_stats(username)
        except Exception:
            app.logger.exception("Unable to read history")
            searches, accesses, stats = [], [], {}
            flash("History is temporarily unavailable. Check database configuration.", "error")
        return render_template("history.html", searches=searches, accesses=accesses, stats=stats)

    @app.errorhandler(RequestEntityTooLarge)
    def upload_too_large(_error):
        flash("Upload too large. The maximum file size is 25 MB.", "error")
        return redirect(url_for("index"))

    @app.errorhandler(400)
    def bad_request(error):
        return render_template("error.html", code=400, message=getattr(error, "description", "Bad request")), 400

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", code=404, message="The requested page or document was not found."), 404

    @app.errorhandler(503)
    def service_unavailable(error):
        return render_template("error.html", code=503, message=getattr(error, "description", "Service temporarily unavailable")), 503

    return app


app = create_app()

if __name__ == "__main__":
    # Local browser development: set WEB_APP_PASSWORD before starting.
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
