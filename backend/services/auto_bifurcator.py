"""Intelligent Document Auto-Bifurcation & Auto-Configuration Engine.

Accepts multi-format uploaded documents (PDF, DOCX, XLSX, CSV, TXT, MD), parses their
contents, semantically bifurcates the information into:
  1. Brand & Profile Data (Name, Bot persona, Tagline, Tone, Contact, Hours, Vertical)
  2. WhatsApp Interactive Navigation Menu (Buttons/Drawers <= 24 title / 72 desc chars)
  3. Conversational Intents & Flow Triggers (Keywords, Utterances, Action Mappings)
  4. Offerings & Catalog Data (Products, Services, Packages, Properties with Pricing)
  5. Knowledge Base & FAQ Documents (Markdown articles, Chunks, Vector RAG Embeddings)

Automatically configures and publishes all components into the tenant configuration,
database tables, client pack (clients/<tenant_id>/config.json), and FAISS vector index,
eliminating manual data entry and configuration work.
"""

import csv
import io
import json
import logging
import os
import re
import shutil
import string
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import fitz  # PyMuPDF
from docx import Document
import openpyxl

from database import (
    get_db_context,
    list_products,
    record_admin_audit_event,
    save_admin_file,
    save_chunks,
    save_knowledge_base_chunks,
    save_product,
    update_product,
)  # save_chunks used for FAQ Q&A persistence
from shared.tenancy import cache as tenancy_cache
from shared.tenancy import loader as tenancy_loader
from shared.tenancy import schemas as tenancy_schemas
from shared.tenancy import store as tenancy_store
from shared.tenancy.defaults import get_vertical_defaults

logger = logging.getLogger("auto_bifurcator")

# Target vertical options supported by tenancy schema
VALID_VERTICALS = set(tenancy_schemas.VERTICALS)

# Brochure modules recognized by brochure_service (destination for
# brochure/profile/menu/price-list documents)
BROCHURE_MODULES = {
    "catalogue",
    "new_arrival",
    "product_brochure",
    "service_brochure",
    "company_profile",
    "technical_brochure",
    "pricing",
    "customer_case_study",
    "industry_brochure",
    "general",
}

# Document types the LLM/heuristics may assign; brochure-ish types are
# auto-registered as sendable brochure PDFs for the tenant.
BROCHURE_DOC_TYPES = {
    "brochure": "catalogue",
    "company_profile": "company_profile",
    "menu": "pricing",
    "price_list": "pricing",
    "catalog": "catalogue",
    "technical_brochure": "technical_brochure",
    "case_study": "customer_case_study",
}

# Public file host used to expose brochure PDFs over WhatsApp
CATBOX_API_URL = os.environ.get("CATBOX_API_URL", "https://catbox.moe/user/api.php")

# ──────────────────────────────────────────────────────────────────────────
# OCR setup (scanned / image-only PDFs and image files)
# ──────────────────────────────────────────────────────────────────────────
try:
    import pytesseract
    from PIL import Image
except ImportError:  # pragma: no cover - OCR optional
    pytesseract = None
    Image = None

TESSERACT_CMD = os.environ.get("TESSERACT_CMD") or shutil.which("tesseract")
if not TESSERACT_CMD:
    _default_windows_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(_default_windows_path):
        TESSERACT_CMD = _default_windows_path

if TESSERACT_CMD and pytesseract:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
    logger.info("OCR enabled | tesseract=%s", TESSERACT_CMD)
else:
    logger.warning(
        "OCR unavailable - scanned/image-only PDFs will yield little or no text. "
        "Set TESSERACT_CMD to the tesseract executable to enable OCR."
    )

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp")
MAX_OCR_PAGES = 20


def _clean_text(text: str) -> str:
    """Normalize whitespace and strip non-printable characters."""
    if not text:
        return ""
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _slugify(text: str) -> str:
    """Produce clean lowercase slug."""
    text = (text or "").lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-") or "item"


def _sanitize_business_hours(raw_hours: Any) -> Dict[str, Any]:
    """Normalize kit/LLM hours into BusinessHours schema fields (no ``raw``)."""
    if not isinstance(raw_hours, dict):
        raw_hours = {}
    hours = {
        "timezone": str(raw_hours.get("timezone") or "Asia/Kolkata"),
        "always_open": bool(raw_hours.get("always_open", False)),
        "open": str(raw_hours.get("open") or "09:30"),
        "close": str(raw_hours.get("close") or "18:30"),
        "open_days": list(raw_hours.get("open_days") or [0, 1, 2, 3, 4, 5]),
    }
    if raw_hours.get("out_of_hours_message"):
        hours["out_of_hours_message"] = str(raw_hours["out_of_hours_message"])

    # Parse free-text like "09:30 AM - 06:30 PM (Mon-Sat)" from kit tables
    raw_label = str(raw_hours.get("raw") or "").strip()
    if raw_label:
        times = re.findall(r"(\d{1,2}:\d{2})\s*(AM|PM)?", raw_label, flags=re.IGNORECASE)
        if len(times) >= 2:
            def _to_24(t: str, meridiem: str) -> str:
                hh, mm = t.split(":")
                h = int(hh)
                m = meridiem.upper() if meridiem else ""
                if m == "PM" and h < 12:
                    h += 12
                if m == "AM" and h == 12:
                    h = 0
                return f"{h:02d}:{mm}"

            hours["open"] = _to_24(times[0][0], times[0][1])
            hours["close"] = _to_24(times[1][0], times[1][1])
        low = raw_label.lower()
        if "mon-sat" in low or "mon – sat" in low or "monday-saturday" in low:
            hours["open_days"] = [0, 1, 2, 3, 4, 5]
        elif "24/7" in low or "always" in low:
            hours["always_open"] = True
    # Ensure open_days are ints 0..6
    clean_days = []
    for d in hours["open_days"]:
        try:
            di = int(d)
        except Exception:
            continue
        if 0 <= di <= 6:
            clean_days.append(di)
    hours["open_days"] = clean_days or [0, 1, 2, 3, 4, 5]
    return hours


def _is_placeholder_brand_value(key: str, value: Any, tenant_id: str) -> bool:
    """True when a brand field looks invented rather than extracted from docs."""
    if value is None:
        return True
    text = str(value).strip()
    if not text:
        return True
    lowered = text.lower()
    tid = (tenant_id or "").strip().lower()
    title_tid = tid.replace("-", " ").title()
    placeholders = {
        "name": {tid, tid.replace("-", " "), title_tid.lower()},
        "bot_name": {f"{tid} assistant", f"{title_tid.lower()} assistant"},
        "website": {
            f"https://www.{tid}.com",
            f"http://www.{tid}.com",
            f"www.{tid}.com",
            f"https://{tid}.com",
        },
        "support_email": {f"support@{tid}.com"},
        "support_phone": {"+91 9800000000", "+919800000000", "9800000000"},
        "signature": {
            f"{title_tid} — at your service.".lower(),
            f"{title_tid} - at your service.".lower(),
        },
        "tagline": set(),
    }
    known = placeholders.get(key, set())
    return lowered in known


class AutoBifurcator:
    """Core auto-bifurcation and auto-configuration pipeline."""

    def __init__(self, tenant_id: str, actor: Optional[dict] = None):
        self.tenant_id = tenant_id.strip().lower()
        self.actor = actor or {
            "username": "auto_bifurcator",
            "role": "super_admin",
            "tenant_id": self.tenant_id,
        }

    # ──────────────────────────────────────────────────────────────────────────
    # 1. Multi-Format Text & Table Extraction
    # ──────────────────────────────────────────────────────────────────────────

    def extract_file_content(self, filename: str, content: bytes) -> Dict[str, Any]:
        """Extract text and tables from PDF, DOCX, XLSX, CSV, TXT, MD."""
        ext = Path(filename).suffix.lower()
        extracted_text = ""
        tables_found: List[List[List[str]]] = []

        try:
            if ext == ".pdf":
                doc = fitz.open(stream=content, filetype="pdf")
                pages_text = []
                for pno in range(len(doc)):
                    page = doc[pno]
                    txt = page.get_text("text") or ""
                    if txt.strip():
                        pages_text.append(f"--- Page {pno + 1} ---\n{txt}")
                    try:
                        tabs = page.find_tables()
                        for tab in tabs:
                            extracted_tbl = tab.extract()
                            if extracted_tbl and len(extracted_tbl) > 1:
                                clean_tbl = [
                                    [str(c or "").strip().replace("\n", " ") for c in r]
                                    for r in extracted_tbl
                                ]
                                tables_found.append(clean_tbl)
                    except Exception as tab_err:
                        logger.debug("PDF find_tables page %d skipped: %s", pno, tab_err)
                extracted_text = "\n\n".join(pages_text)

            elif ext in (".docx", ".doc"):
                doc_file = io.BytesIO(content)
                doc = Document(doc_file)
                paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
                # Extract tables
                table_texts = []
                for table in doc.tables:
                    t_rows = []
                    for row in table.rows:
                        row_cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                        t_rows.append(row_cells)
                    if t_rows:
                        tables_found.append(t_rows)
                        table_texts.append("\n".join([" | ".join(r) for r in t_rows]))
                extracted_text = "\n\n".join(paragraphs + table_texts)

            elif ext in (".xlsx", ".xls"):
                wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
                sheet_texts = []
                for sheetname in wb.sheetnames:
                    sheet = wb[sheetname]
                    rows = []
                    for row in sheet.iter_rows(values_only=True):
                        cells = [str(c).strip() if c is not None else "" for c in row]
                        if any(cells):
                            rows.append(" | ".join(cells))
                    if rows:
                        sheet_texts.append(f"=== Sheet: {sheetname} ===\n" + "\n".join(rows))
                extracted_text = "\n\n".join(sheet_texts)

            elif ext == ".csv":
                text_stream = io.StringIO(content.decode("utf-8", errors="ignore"))
                reader = csv.reader(text_stream)
                rows = [" | ".join(row) for row in reader if any(row)]
                extracted_text = "\n".join(rows)

            else:
                # Text or Markdown fallback
                try:
                    extracted_text = content.decode("utf-8")
                except UnicodeDecodeError:
                    extracted_text = content.decode("latin-1", errors="ignore")

        except Exception as exc:
            logger.error("Failed extracting %s: %s", filename, exc)
            extracted_text = f"[Text extraction error: {exc}]"

        extracted_text = _clean_text(extracted_text)
        return {
            "filename": filename,
            "ext": ext,
            "size": len(content),
            "char_count": len(extracted_text),
            "text": extracted_text,
            "tables": tables_found,
            "has_tables": len(tables_found) > 0,
        }

    # ──────────────────────────────────────────────────────────────────────────
    # 2. LLM Semantic Bifurcation & Synthesis
    # ──────────────────────────────────────────────────────────────────────────

    def bifurcate_with_llm(self, doc_summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Send aggregated document contents to LLM to bifurcate into components."""
        # Concatenate text from all uploaded documents up to ~30,000 chars
        combined_chunks = []
        for doc in doc_summaries:
            txt = doc["text"]
            # Keep up to 12,000 chars per doc to give balanced coverage
            sample = txt[:12000]
            combined_chunks.append(f"================ DOCUMENT: {doc['filename']} ================\n{sample}")

        full_corpus = "\n\n".join(combined_chunks)
        if len(full_corpus) > 40000:
            full_corpus = full_corpus[:40000] + "\n...[Additional document content truncated]..."

        system_prompt = f"""You are an elite enterprise AI data architect and WhatsApp chatbot configurator.
Your mission is to read raw client documents (brochures, catalogs, FAQ sheets, company profiles) and automatically BIFURCATE and CONFIGURE the entire tenant chatbot system for tenant ID '{self.tenant_id}'.

You must output a strictly valid JSON object adhering to this structure:
{{
  "vertical": "real_estate" | "tours_travel" | "ecommerce" | "it_software" | "banking" | "finance" | "healthcare" | "generic",
  "brand": {{
    "name": "Official Company / Entity Name",
    "bot_name": "Friendly AI Assistant Name (e.g. Skyline Assistant, DLF Concierge)",
    "tagline": "1-2 sentence compelling value proposition",
    "website": "Valid URL (e.g. https://company.com or www.company.com)",
    "support_email": "Official support email address",
    "support_phone": "Official phone number with country code (e.g. +91 9876543210)",
    "signature": "Brand closing sign-off line"
  }},
  "business_hours": {{
    "timezone": "Asia/Kolkata",
    "open": "09:30",
    "close": "18:30",
    "open_days": [0, 1, 2, 3, 4, 5]
  }},
  "menu_items": [
    // 3 to 6 interactive WhatsApp menu options
    // CRITICAL META API CONSTRAINTS:
    // - "title" MUST BE <= 24 CHARACTERS (e.g. "Explore Properties", "Book Site Visit", "Pricing Plans", "Customer Support")
    // - "description" MUST BE <= 72 CHARACTERS
    // - "section" MUST BE <= 24 CHARACTERS (e.g. "Main Menu", "Explore", "Assistance")
    // - "action" should map to one of: "offerings", "get_quote", "book_callback", "raise_ticket", "faq"
    {{
      "id": "browse_offerings",
      "title": "Explore Offerings",
      "description": "Browse catalog, projects, or service offerings",
      "section": "Explore",
      "action": "offerings"
    }}
  ],
  "intents": [
    // 5 to 10 top customer conversational intents
    {{
      "name": "intent_slug_name",
      "description": "Brief description of customer purpose",
      "keywords": ["keyword1", "keyword2", "keyword3"],
      "examples": [
        "Example user question 1",
        "Example user question 2",
        "Example user question 3"
      ],
      "flow": "book_callback" | "get_quote" | "raise_ticket" | null
    }}
  ],
  "offerings": [
    // All individual products, services, properties, or packages extracted from documents
    {{
      "name": "Item or Package Name",
      "category": "Category or Segment",
      "price": "Price, starting rate, or range (e.g. '₹85 Lakhs' or '$499/mo' or 'Starting ₹25,000')",
      "short_description": "1 sentence punchy summary",
      "description": "Detailed features, inclusions, and specifications",
      "unit": "unit / package / license / flat / person",
      "media_url": "Public https image URL if present in the document (or empty string)",
      "media_type": "image",
      "attrs": {{
        "highlights": "Key bullet points",
        "specifications": "Extra details"
      }}
    }}
  ],
  "faqs": [
    // Explicit Q&A pairs found in the documents (policies, how-tos, support)
    {{
      "question": "What is the cancellation policy?",
      "answer": "Cancellations made 48 hours before arrival receive a full refund.",
      "category": "Policies"
    }}
  ],
  "knowledge_articles": [
    // Structured knowledge base documents formatted in Clean Markdown
    {{
      "title": "Company Overview & Profile",
      "category": "Company",
      "markdown_content": "# Company Overview\\n\\nDetailed background, history, certifications..."
    }},
    {{
      "title": "Booking Process, Policies & FAQs",
      "category": "FAQ",
      "markdown_content": "# Frequently Asked Questions\\n\\n### Q: ...\\nA: ..."
    }}
  ]
}}

CRITICAL INSTRUCTIONS:
1. Extract ALL tangible products/services/properties you find into the 'offerings' array.
2. Extract every clear question/answer pair into the 'faqs' array (do not leave FAQs only inside markdown articles).
3. Ensure 'menu_items' titles are UNDER 24 CHARACTERS (strictly enforced by WhatsApp API).
4. If phone or email is genuinely missing in the text, omit those brand fields or leave them empty — do NOT invent placeholder contacts.
5. Respond ONLY with the JSON object. Do not enclose in backticks or markdown if possible.
"""

        user_prompt = f"Please bifurcate and configure the chatbot system based on the following uploaded client collateral:\n\n{full_corpus}"

        response_json = self._call_llm_json(system_prompt, user_prompt)
        if not response_json:
            raise RuntimeError(
                "Bifurcation LLM unavailable: no provider (Ollama/Groq/Mistral) returned valid JSON."
            )

        return response_json

    def _call_llm_json(self, system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
        """Call local Ollama first, then Groq or Mistral as fallbacks.
        Keys are read from routing.config (the app's central config) with
        os.getenv() as a secondary fallback so the service works in both
        the production app and standalone test contexts.
        """
        import requests

        # ── Resolve API keys from routing.config first, then env ──────────────
        try:
            from routing import config as _cfg
            groq_key    = getattr(_cfg, "GROQ_API_KEY", None)    or os.getenv("GROQ_API_KEY", "")
            groq_url    = getattr(_cfg, "GROQ_API_URL", None)    or "https://api.groq.com/openai/v1/chat/completions"
            groq_model  = getattr(_cfg, "GROQ_MODEL", None)      or "openai/gpt-oss-120b"
            mistral_key = getattr(_cfg, "MISTRAL_API_KEY", None) or os.getenv("MISTRAL_API_KEY", "")
            mistral_url = getattr(_cfg, "MISTRAL_API_URL", None) or "https://api.mistral.ai/v1/chat/completions"
            mistral_mdl = getattr(_cfg, "MISTRAL_MODEL", None)   or "open-mistral-7b"
            ollama_base = getattr(_cfg, "OLLAMA_BASE_URL", None) or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            ollama_url  = getattr(_cfg, "OLLAMA_API_URL", None)  or (ollama_base.rstrip("/") + "/api/chat")
            ollama_mdl  = getattr(_cfg, "OLLAMA_MODEL", None)    or "qwen3:8b"
        except Exception:
            groq_key    = os.getenv("GROQ_API_KEY", "")
            groq_url    = "https://api.groq.com/openai/v1/chat/completions"
            groq_model  = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
            mistral_key = os.getenv("MISTRAL_API_KEY", "")
            mistral_url = "https://api.mistral.ai/v1/chat/completions"
            mistral_mdl = os.getenv("MISTRAL_MODEL", "open-mistral-7b")
            ollama_url  = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/chat")
            ollama_mdl  = os.getenv("OLLAMA_MODEL", "qwen3:8b")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # 1. Ollama (primary configured provider)
        try:
            payload = {
                "model": ollama_mdl,
                "messages": messages,
                "format": "json",
                "stream": False,
                "options": {"temperature": 0.1, "num_ctx": 8192},
            }
            ollama_headers = {
                "Content-Type": "application/json",
                "ngrok-skip-browser-warning": "true",
            }
            resp = requests.post(
                ollama_url,
                json=payload,
                headers=ollama_headers,
                timeout=float(os.getenv("OLLAMA_TIMEOUT", 180)),
            )
            if resp.status_code == 200:
                content = resp.json().get("message", {}).get("content", "")
                parsed = self._extract_json_block(content)
                if parsed:
                    logger.info("OLLAMA_BIFURCATION_SUCCESS | model=%s", ollama_mdl)
                    return parsed
                logger.warning("Ollama returned no usable JSON; trying hosted fallbacks.")
            else:
                logger.warning("Ollama bifurcation HTTP %s; trying hosted fallbacks.", resp.status_code)
        except Exception as e:
            logger.warning("Ollama bifurcation failed: %s", e)

        # 2. Groq (fast hosted inference — uses routing.config key)
        if groq_key:
            try:
                headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
                for model in (groq_model, "openai/gpt-oss-20b"):
                    if not model:
                        continue
                    payload = {
                        "model": model,
                        "messages": messages,
                        "response_format": {"type": "json_object"},
                        "temperature": 0.2,
                        "max_tokens": 4096,
                    }
                    resp = requests.post(groq_url, headers=headers, json=payload, timeout=45)
                    if resp.status_code == 200:
                        content = resp.json()["choices"][0]["message"]["content"]
                        parsed = self._extract_json_block(content)
                        if parsed:
                            logger.info("GROQ_BIFURCATION_SUCCESS | model=%s", model)
                            return parsed
            except Exception as e:
                logger.warning("Groq bifurcation failed: %s", e)
        else:
            logger.warning("Groq API key not configured — skipping Groq bifurcation.")

        # 3. Mistral (fallback — uses routing.config key)
        if mistral_key:
            try:
                headers = {"Authorization": f"Bearer {mistral_key}", "Content-Type": "application/json"}
                payload = {
                    "model": mistral_mdl,
                    "messages": messages,
                    "temperature": 0.2,
                    "max_tokens": 4096,
                }
                resp = requests.post(mistral_url, headers=headers, json=payload, timeout=45)
                if resp.status_code == 200:
                    content = resp.json()["choices"][0]["message"]["content"]
                    parsed = self._extract_json_block(content)
                    if parsed:
                        logger.info("MISTRAL_BIFURCATION_SUCCESS")
                        return parsed
            except Exception as e:
                logger.warning("Mistral bifurcation failed: %s", e)
        else:
            logger.warning("Mistral API key not configured — skipping Mistral bifurcation.")

        return None
        if mistral_key:
            try:
                headers = {"Authorization": f"Bearer {mistral_key}", "Content-Type": "application/json"}
                payload = {
                    "model": os.getenv("MISTRAL_MODEL", "open-mistral-7b"),
                    "messages": messages,
                    "temperature": 0.2,
                    "max_tokens": 4096,
                }
                resp = requests.post(
                    "https://api.mistral.ai/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=45,
                )
                if resp.status_code == 200:
                    content = resp.json()["choices"][0]["message"]["content"]
                    parsed = self._extract_json_block(content)
                    if parsed:
                        logger.info("MISTRAL_BIFURCATION_SUCCESS")
                        return parsed
            except Exception as e:
                logger.warning("Mistral bifurcation failed: %s", e)

        return None

    def _extract_json_block(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract and parse JSON safely from LLM output."""
        if not text:
            return None
        text = text.strip()
        # Direct parse
        try:
            return json.loads(text)
        except Exception:
            pass

        # Regex search for ```json ... ```
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass

        # Search for first { to last }
        first = text.find("{")
        last = text.rfind("}")
        if first != -1 and last != -1 and last > first:
            try:
                return json.loads(text[first : last + 1])
            except Exception:
                pass

        return None

    # ──────────────────────────────────────────────────────────────────────────
    # 2b. Section Partitioning & Kit Staging (deterministic [SECTION:] parse)
    # ──────────────────────────────────────────────────────────────────────────

    def partition_sections(self, extracted_docs: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:

        """Identify sections (Brand, Menu, Catalog, FAQs, Guardrails) across files."""

        combined_text = "\n\n".join(d["text"] for d in extracted_docs)

        all_tables = []

        for d in extracted_docs:

            all_tables.extend(d.get("tables", []))



        # Standard Section Patterns

        section_patterns = {

            "brand": r"\[SECTION:\s*BRAND(?:\s*&\s*PROFILE)?\]",

            "menu": r"\[SECTION:\s*WHATSAPP(?:\s*MENU)?\]",

            "catalog": r"\[SECTION:\s*CATALOG(?:\s*&\s*OFFERINGS)?\]",

            "faqs": r"\[SECTION:\s*FAQS(?:\s*&\s*POLICIES)?\]",

            "guardrails": r"\[SECTION:\s*BOT\s*PERSONA(?:\s*&\s*GUARDRAILS)?\]",

        }



        # Check if standardized section markers exist

        has_markers = any(re.search(pat, combined_text, re.IGNORECASE) for pat in section_patterns.values())



        sections: Dict[str, Dict[str, Any]] = {

            "brand": {"text": "", "tables": []},

            "menu": {"text": "", "tables": []},

            "catalog": {"text": "", "tables": []},

            "faqs": {"text": "", "tables": []},

            "guardrails": {"text": "", "tables": []},

        }



        if has_markers:

            # Split text along section headers

            splits = re.split(

                r"(\[SECTION:\s*[^\]]+\])",

                combined_text,

                flags=re.IGNORECASE,

            )

            current_sec = "brand"

            for part in splits:

                part = part.strip()

                if not part:

                    continue

                match_header = re.match(r"\[SECTION:\s*([^\]]+)\]", part, re.IGNORECASE)

                if match_header:

                    tag = match_header.group(1).upper()

                    if "BRAND" in tag:

                        current_sec = "brand"

                    elif "MENU" in tag:

                        current_sec = "menu"

                    elif "CATALOG" in tag or "OFFERING" in tag:

                        current_sec = "catalog"

                    elif "FAQ" in tag or "POLIC" in tag:

                        current_sec = "faqs"

                    elif "PERSONA" in tag or "GUARD" in tag:

                        current_sec = "guardrails"

                else:

                    sections[current_sec]["text"] += f"\n{part}"



            # Distribute tables to matching sections based on table headers

            for tbl in all_tables:

                if not tbl or not tbl[0]:

                    continue

                first_row_str = " ".join(str(c).lower() for c in tbl[0])

                if any(k in first_row_str for k in ("parameter", "company legal", "tenant id", "bot name")):

                    sections["brand"]["tables"].append(tbl)

                elif any(k in first_row_str for k in ("button title", "action mapping", "category section")):

                    sections["menu"]["tables"].append(tbl)

                elif any(k in first_row_str for k in ("property", "product", "sku", "service name", "package name", "bhk", "carpet area")):

                    sections["catalog"]["tables"].append(tbl)

                elif any(
                    k in first_row_str
                    for k in (
                        "knowledge article",
                        "article title",
                        "article content",
                        "markdown content",
                    )
                ):
                    sections["faqs"]["tables"].append(tbl)

                elif (

                    any(k in first_row_str for k in ("question", "frequently asked", "official answer", "verified answer"))

                    or str(tbl[0][0]).strip().endswith("?")

                    or (len(tbl[0]) == 3 and any(str(r[0]).strip().endswith("?") for r in tbl))

                ):

                    sections["faqs"]["tables"].append(tbl)

                elif any(k in first_row_str for k in ("guardrail", "tone & style", "never-do", "bot behavior", "persona", "configuration parameter")):

                    sections["guardrails"]["tables"].append(tbl)

                else:

                    # Generic fallback table

                    sections["catalog"]["tables"].append(tbl)

        else:

            # Fallback for unformatted/raw collateral

            sections["brand"]["text"] = combined_text[:6000]

            sections["catalog"]["text"] = combined_text

            sections["catalog"]["tables"] = all_tables

            sections["faqs"]["text"] = combined_text



        return sections



    # ──────────────────────────────────────────────────────────────────────────

    # 4. Section-Targeted Extractors

    # ──────────────────────────────────────────────────────────────────────────



    def extract_brand_section(self, sec_data: Dict[str, Any], default_vertical: str = "generic") -> Tuple[Dict[str, Any], Dict[str, Any], str]:

        """Extract Brand profile, hours, and vertical from Section 1."""

        text = sec_data.get("text", "")

        tables = sec_data.get("tables", [])



        # Step 1: Detect from table if available

        parsed_fields = {}

        for tbl in tables:

            for row in tbl:

                if len(row) >= 2:

                    k = row[0].strip().lower()

                    v = row[-1].strip()

                    if "tagline" in k or "proposition" in k:

                        parsed_fields["tagline"] = v

                    elif "whatsapp bot number" in k or "bot number" in k:

                        parsed_fields["bot_phone"] = v

                    elif "bot name" in k or "assistant name" in k:

                        parsed_fields["bot_name"] = v

                    elif "tenant id" in k or "tenant code" in k:

                        parsed_fields["tenant_id"] = v

                    elif "display name" in k or k == "brand name" or "brand / display" in k:

                        parsed_fields["brand_name"] = v

                    elif "company legal" in k or "company name" in k or "legal name" in k:

                        parsed_fields["legal_name"] = v

                    elif "website" in k or "url" in k:

                        parsed_fields["website"] = v

                    elif "email" in k or "support email" in k:

                        parsed_fields["support_email"] = v

                    elif "phone" in k or "helpline" in k or "mobile" in k:

                        parsed_fields["support_phone"] = v

                    elif "hours" in k or "schedule" in k:

                        parsed_fields["hours"] = v



        # Step 2: Detect vertical

        full_sample = (text + " " + json.dumps(parsed_fields)).lower()

        vertical = default_vertical

        if any(w in full_sample for w in ("property", "residence", "bhk", "villa", "penthouse", "real estate", "rera")):

            vertical = "real_estate"

        elif any(w in full_sample for w in ("flight", "tour", "travel", "vacation", "itinerary", "package")):

            vertical = "tours_travel"

        elif any(w in full_sample for w in ("software", "cloud", "devops", "tech stack", "fastapi", "react", "kubernetes")):

            vertical = "it_software"

        elif any(w in full_sample for w in ("product", "sku", "delivery", "cart", "warranty", "ecommerce", "retail")):

            vertical = "ecommerce"

        elif any(w in full_sample for w in ("clinic", "doctor", "specialty", "consultation fee", "hospital", "patient")):

            vertical = "healthcare"

        elif any(w in full_sample for w in ("account", "deposit", "credit card", "bank", "atm", "branch")):

            vertical = "banking"

        elif any(w in full_sample for w in ("tax", "audit", "gst", "itr", "wealth", "advisory", "accounting")):

            vertical = "finance"



        # Fallback values

        company_name = (

            parsed_fields.get("brand_name")

            or parsed_fields.get("legal_name")

            or self.tenant_id.replace("-", " ").replace("_", " ").title()

        )

        bot_name = parsed_fields.get("bot_name") or f"{company_name} Advisor"

        tagline = parsed_fields.get("tagline") or f"Official WhatsApp Concierge for {company_name}"

        website = parsed_fields.get("website") or f"https://www.{self.tenant_id}.com"

        email = parsed_fields.get("support_email") or f"support@{self.tenant_id}.com"

        phone = parsed_fields.get("support_phone") or "+91 9876543210"



        brand = {

            "name": company_name,

            "bot_name": bot_name,

            "tagline": tagline,

            "website": website,

            "support_email": email,

            "support_phone": phone,

            "signature": f"{company_name} — At your service.",

        }



        hours_str = parsed_fields.get("hours") or "09:30 AM - 06:30 PM (Mon-Sat)"

        business_hours = {

            "timezone": "Asia/Kolkata",

            "open": "09:30",

            "close": "18:30",

            "open_days": [0, 1, 2, 3, 4, 5],

            "raw": hours_str,

        }



        return brand, business_hours, vertical



    def extract_menu_section(self, sec_data: Dict[str, Any], vertical: str) -> List[Dict[str, Any]]:

        """Extract and validate WhatsApp interactive menu items (Meta 24/72 char limits)."""

        tables = sec_data.get("tables", [])

        menu_items = []



        for tbl in tables:

            # Check if this table has menu headers

            if len(tbl) > 1 and len(tbl[0]) >= 3:

                for row in tbl[1:]:

                    if not row or not row[0].strip():

                        continue

                    title = row[0].strip()[:24]

                    desc = (row[1].strip() if len(row) > 1 else title)[:72]

                    sec = (row[2].strip() if len(row) > 2 else "Explore")[:24]

                    action = (row[3].strip() if len(row) > 3 else "offerings").lower()



                    # Sanitize action

                    if "quote" in action or "price" in action:

                        action = "quote"

                    elif "call" in action or "visit" in action or "appoint" in action:

                        action = "book_callback"

                    elif "ticket" in action or "support" in action or "help" in action:

                        action = "raise_ticket"

                    elif "faq" in action or "info" in action:

                        action = "faq"

                    elif "detail" in action:

                        action = "offering_details"

                    else:

                        action = "offerings"



                    menu_items.append({

                        "id": _slugify(title),

                        "title": title,

                        "description": desc,

                        "section": sec,

                        "action": action,

                    })



        # If no items found, load vertical defaults

        if len(menu_items) < 3:

            v_defaults = get_vertical_defaults(vertical) or {}

            def_menu = v_defaults.get("menu", {}).get("buttons", [])

            for b in def_menu[:6]:

                menu_items.append({

                    "id": b.get("id", "menu_item"),

                    "title": b.get("title", "Explore")[:24],

                    "description": b.get("description", "View options")[:72],

                    "section": b.get("section", "Explore")[:24],

                    "action": b.get("flow") or b.get("requires_feature") or "offerings",

                })



        return menu_items[:8]



    def extract_catalog_section(self, sec_data: Dict[str, Any], vertical: str) -> List[Dict[str, Any]]:

        """Extract structured catalog offerings/properties with vertical-specific attributes."""

        tables = sec_data.get("tables", [])

        text = sec_data.get("text", "")

        offerings: List[Dict[str, Any]] = []



        for tbl in tables:

            if len(tbl) < 2:

                continue

            headers = [str(c).strip().lower() for c in tbl[0]]



            # Filter out brand or menu tables accidentally routed here

            if any(h in headers for h in ("button title", "parameter", "verified answer", "knowledge article")):

                continue



            for row in tbl[1:]:

                if not row or not any(row):

                    continue

                first_cell = str(row[0]).strip()

                if not first_cell or first_cell.startswith("[") or first_cell.lower() == "enter item":

                    continue



                row_dict = {}

                for idx, cell in enumerate(row):

                    if idx < len(headers):

                        row_dict[headers[idx]] = str(cell).strip()

                def _pick_media_url(rd: Dict[str, str]) -> str:
                    for key, val in rd.items():
                        kl = key.lower()
                        if any(tok in kl for tok in ("image url", "image", "media url", "media_url", "photo", "thumbnail")):
                            v = (val or "").strip()
                            if v and not v.startswith("[") and ("http://" in v.lower() or "https://" in v.lower()):
                                return v
                            if v and not v.startswith("["):
                                return v
                    return ""



                # Vertical-specific mapping

                if vertical == "real_estate":

                    name = row_dict.get("property name") or first_cell

                    prop_type = row_dict.get("type") or "Residential"

                    bhk = row_dict.get("configuration") or "2 & 3 BHK"

                    carpet = row_dict.get("carpet area (sqft)") or row_dict.get("carpet area") or ""

                    price = row_dict.get("price range") or row_dict.get("price") or "Price on Request"

                    loc = row_dict.get("location") or "Prime Location"

                    amenities = row_dict.get("key amenities") or row_dict.get("amenities") or ""

                    possession = row_dict.get("possession") or "Ready to Move"

                    rera = row_dict.get("rera id") or row_dict.get("rera number") or ""



                    short_desc = f"{bhk} in {loc}"

                    full_desc = f"{name}: {prop_type} with {bhk} ({carpet} sqft) located at {loc}. Amenities: {amenities}. Possession: {possession}. RERA: {rera}."

                    attrs = {

                        "type": prop_type,

                        "bhk": bhk,

                        "carpet_area": carpet,

                        "location": loc,

                        "amenities": amenities,

                        "possession": possession,

                        "rera_id": rera,

                    }



                elif vertical == "ecommerce":

                    name = row_dict.get("product name") or first_cell

                    sku = row_dict.get("sku") or _slugify(name).upper()

                    prop_type = row_dict.get("category") or "Accessories"

                    price = row_dict.get("discount price") or row_dict.get("price (₹)") or row_dict.get("price") or ""

                    specs = row_dict.get("key specifications / size") or row_dict.get("specifications") or ""

                    stock = row_dict.get("stock status") or "In Stock"

                    warranty = row_dict.get("warranty / returns") or row_dict.get("warranty") or "7-Day Return"



                    short_desc = specs[:100] or name

                    full_desc = f"{name} (SKU: {sku}) - {specs}. Stock: {stock}. Warranty: {warranty}."

                    attrs = {

                        "sku": sku,

                        "specifications": specs,

                        "stock_status": stock,

                        "warranty": warranty,

                    }



                else:

                    # General / IT / Travel / Healthcare

                    name = row_dict.get("service / offering") or row_dict.get("package name") or row_dict.get("specialty / department") or first_cell

                    prop_type = row_dict.get("category") or "Services"

                    price = row_dict.get("starting price / model") or row_dict.get("price per person") or row_dict.get("consultation fee") or "On Request"

                    desc = row_dict.get("scope & deliverables") or row_dict.get("highlights") or row_dict.get("services & treatments") or name

                    short_desc = desc[:90]

                    full_desc = desc

                    attrs = {
                        k: v for k, v in row_dict.items()
                        if k not in ("property name", "product name", "service / offering", "image url", "media url", "image", "photo")
                    }

                media_url = _pick_media_url(row_dict)
                media_type = "image"
                if media_url and media_url.lower().endswith(".pdf"):
                    media_type = "pdf"

                offering: Dict[str, Any] = {

                    "name": name,

                    "category": prop_type,

                    "price": price,

                    "short_description": short_desc,

                    "description": full_desc,

                    "unit": "unit",

                    "attrs": attrs,

                }
                if media_url:
                    offering["media_url"] = media_url
                    offering["media_type"] = media_type

                offerings.append(offering)



        # Fallback if no tables: regex extract lines with prices or bullets

        if not offerings and text:

            for line in text.splitlines():

                line = line.strip()

                if (line.startswith("•") or line.startswith("*") or line.startswith("-")) and len(line) > 10:

                    clean_l = line.lstrip("•*- ").strip()

                    parts = clean_l.split(":")

                    item_name = parts[0].strip()[:60]

                    item_desc = parts[1].strip() if len(parts) > 1 else clean_l

                    offerings.append({

                        "name": item_name,

                        "category": "General",

                        "price": "On Request",

                        "short_description": item_name,

                        "description": item_desc,

                        "unit": "unit",

                        "attrs": {},

                    })

                if len(offerings) >= 8:

                    break



        return offerings



    def extract_faq_section(self, sec_data: Dict[str, Any], brand_name: str, vertical: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Extract FAQs and knowledge articles from FAQS & POLICIES tables."""
        tables = sec_data.get("tables", [])
        text = sec_data.get("text", "")
        faqs: List[Dict[str, Any]] = []
        articles: List[Dict[str, Any]] = []

        def _header_blob(tbl: List[List[str]]) -> str:
            if not tbl or not tbl[0]:
                return ""
            return " ".join(str(c or "").lower() for c in tbl[0])

        def _is_kb_table(tbl: List[List[str]]) -> bool:
            h = _header_blob(tbl)
            return (
                "knowledge article" in h
                or ("article title" in h and "content" in h)
                or ("article content" in h)
                or (h.startswith("knowledge") and "title" in h)
            )

        def _is_faq_table(tbl: List[List[str]]) -> bool:
            if _is_kb_table(tbl):
                return False
            h = _header_blob(tbl)
            if "question" in h or "faq" in h or "answer" in h:
                return True
            # Data rows that look like Q&A
            sample = tbl[1][0].strip() if len(tbl) > 1 and tbl[1] else (tbl[0][0].strip() if tbl[0] else "")
            return sample.endswith("?") or "?" in sample

        for tbl in tables:
            if not tbl or len(tbl[0]) < 2:
                continue

            if _is_kb_table(tbl):
                for row in tbl[1:]:
                    if not row or not str(row[0]).strip():
                        continue
                    title = str(row[0]).strip()
                    if title.startswith("[") or title.lower().startswith("add "):
                        continue
                    # Title | Category | Content  OR  Title | Content
                    if len(row) >= 3:
                        cat = str(row[1]).strip() or "Knowledge"
                        body = str(row[2]).strip()
                    else:
                        cat = "Knowledge"
                        body = str(row[1]).strip()
                    if title and body:
                        articles.append({
                            "title": title,
                            "category": cat,
                            "markdown_content": body if body.lstrip().startswith("#") else f"# {title}\n\n{body}",
                        })
                continue

            if not _is_faq_table(tbl):
                continue

            is_q = str(tbl[0][0]).strip().endswith("?") or "?" in str(tbl[0][0])
            start_idx = 0 if is_q else 1
            for row in tbl[start_idx:]:
                if not row or not str(row[0]).strip():
                    continue
                q = str(row[0]).strip()
                if q.startswith("[") or q.lower().startswith("add question") or q.lower() == "customer question":
                    continue
                a = str(row[1]).strip() if len(row) > 1 else ""
                cat = str(row[2]).strip() if len(row) > 2 else "General"
                if q and a:
                    faqs.append({"question": q, "answer": a, "category": cat})

        if not faqs and text:
            qa_matches = re.findall(
                r"(?:Q|Question):\s*(.+?)\n+(?:A|Answer):\s*(.+?)(?=\n+(?:Q|Question):|\Z)",
                text,
                re.DOTALL | re.IGNORECASE,
            )
            for q, a in qa_matches:
                faqs.append({"question": q.strip(), "answer": a.strip(), "category": "General"})

        # Always include a compact company stub + rolled-up FAQ article for retrieval.
        articles.insert(0, {
            "title": f"About {brand_name}",
            "category": "Company",
            "markdown_content": (
                f"# About {brand_name}\n\n"
                f"Welcome to {brand_name}. We provide industry-leading {vertical.replace('_', ' ')} solutions.\n\n"
                "Our team is committed to transparency, excellence, and customer satisfaction. "
                "Use the FAQs and knowledge articles below for policies, processes, and support guidance."
            ),
        })

        if faqs:
            faq_md_lines = [f"# Frequently Asked Questions — {brand_name}\n"]
            for f in faqs:
                faq_md_lines.append(
                    f"### Q: {f['question']}\n**A:** {f['answer']}\n*(Category: {f['category']})*\n"
                )
            articles.append({
                "title": "Frequently Asked Questions & Customer Support",
                "category": "FAQ",
                "markdown_content": "\n".join(faq_md_lines),
            })

        return faqs, articles



    def extract_guardrails_section(self, sec_data: Dict[str, Any]) -> Dict[str, Any]:

        """Extract Bot Tone, Guardrails (Never-Do list), and Escalation Rules."""

        tables = sec_data.get("tables", [])

        guardrails = {

            "tone": "consultative, polished, and professional",

            "never_state": [

                "Never offer unauthorized discounts or unlisted pricing.",

                "Never promise delivery or possession dates outside official brochure.",

                "Never request passwords, OTPs, or credit card details.",

            ],

            "escalation_triggers": ["human", "agent", "manager", "dispute", "representative"],

        }



        for tbl in tables:

            for row in tbl:

                if len(row) >= 2:

                    k = str(row[0]).lower()

                    v = str(row[1]).strip()

                    if "tone" in k:

                        guardrails["tone"] = v

                    elif "guardrail" in k or "never" in k:

                        rules = [r.strip().lstrip("123456789.-* ") for r in v.split("\n") if r.strip()]

                        if rules:

                            guardrails["never_state"] = rules

                    elif "escalat" in k or "human" in k:

                        guardrails["escalation_rules"] = v



        return guardrails



    # ──────────────────────────────────────────────────────────────────────────

    # 5. Staging Pipeline (Review & Edit Before Publish)

    # ──────────────────────────────────────────────────────────────────────────



    def stage_files(self, files_data: List[Dict[str, Any]]) -> Dict[str, Any]:

        """Parse files section-by-section and return a reviewable staging draft without committing."""

        extracted_docs = []

        for f in files_data:

            fname = f.get("filename") or "onboarding_doc.docx"

            content = f.get("content") or b""

            if isinstance(content, str):

                import base64

                content = base64.b64decode(content)

            extracted_docs.append(self.extract_file_content(fname, content))



        # Partition sections

        sections = self.partition_sections(extracted_docs)



        # Extract components

        brand, business_hours, vertical = self.extract_brand_section(sections["brand"])

        menu_items = self.extract_menu_section(sections["menu"], vertical=vertical)

        offerings = self.extract_catalog_section(sections["catalog"], vertical=vertical)

        faqs, articles = self.extract_faq_section(sections["faqs"], brand_name=brand["name"], vertical=vertical)

        guardrails = self.extract_guardrails_section(sections["guardrails"])



        staged_draft = {

            "status": "staged",

            "tenant_id": self.tenant_id,

            "vertical": vertical,

            "brand": brand,

            "business_hours": business_hours,

            "menu_items": menu_items,

            "offerings": offerings,

            "faqs": faqs,

            "knowledge_articles": articles,

            "guardrails": guardrails,

            "source_files": [d["filename"] for d in extracted_docs],

            "stats": {

                "offerings_count": len(offerings),

                "menu_items_count": len(menu_items),

                "faqs_count": len(faqs),

                "articles_count": len(articles),

            },

        }

        return staged_draft



    # ──────────────────────────────────────────────────────────────────────────
    # 3. Auto-Configuration & Application Engine
    # ──────────────────────────────────────────────────────────────────────────

    def apply_bifurcation(
        self,
        bifurcation: Dict[str, Any],
        raw_files: List[Dict[str, Any]],
        auto_publish: bool = True,
        careful_brand_merge: bool = False,
        source_file: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Apply extracted data across database tables, profile draft, and knowledge base.

        When ``careful_brand_merge`` is True (per-upload auto-route), brand / menu /
        intents are only written when the LLM returned real non-placeholder values,
        so a FAQ PDF cannot wipe an existing tenant profile with invented defaults.
        """
        tenant_id = self.tenant_id
        kb_source = source_file or "auto_bifurcated_docs.md"
        summary: Dict[str, Any] = {
            "tenant_id": tenant_id,
            "vertical": bifurcation.get("vertical", "generic"),
            "brand": {},
            "menu_buttons_count": 0,
            "intents_count": 0,
            "offerings_created": 0,
            "offerings_sample": [],
            "faqs_saved": 0,
            "kb_chunks_indexed": 0,
            "brand_updated": False,
            "version": 0,
            "status": "configured",
        }

        # 3.1 Sanitize vertical
        vertical = bifurcation.get("vertical", "generic")
        if vertical not in VALID_VERTICALS:
            vertical = "generic"

        # 3.2 Sanitize Brand — keep raw signals separate from filled defaults
        brand_raw = bifurcation.get("brand", {}) or {}
        real_brand: Dict[str, str] = {}
        for key in ("name", "bot_name", "tagline", "website", "support_email", "support_phone", "signature"):
            raw_val = brand_raw.get(key)
            if raw_val and not _is_placeholder_brand_value(key, raw_val, tenant_id):
                real_brand[key] = str(raw_val).strip()

        clean_brand = {
            "name": real_brand.get("name") or tenant_id.replace("-", " ").title(),
            "bot_name": real_brand.get("bot_name") or f"{tenant_id.title()} Assistant",
            "tagline": real_brand.get("tagline") or "",
            "website": real_brand.get("website") or f"https://www.{tenant_id}.com",
            "support_email": real_brand.get("support_email") or f"support@{tenant_id}.com",
            "support_phone": real_brand.get("support_phone") or "+91 9800000000",
            "signature": real_brand.get("signature") or f"{tenant_id.title()} — At your service.",
        }
        if clean_brand["website"] and not clean_brand["website"].startswith("http"):
            clean_brand["website"] = "https://" + clean_brand["website"].lstrip("/")
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", clean_brand["support_email"]):
            clean_brand["support_email"] = f"support@{tenant_id}.com"

        summary["brand"] = clean_brand if not careful_brand_merge else (real_brand or clean_brand)
        has_real_brand = bool(real_brand.get("name") or real_brand.get("bot_name") or real_brand.get("support_email") or real_brand.get("support_phone"))

        # 3.3 Sanitize WhatsApp Menu Buttons (Meta Character Limitations)
        menu_items_raw = bifurcation.get("menu_items", []) or []
        menu_buttons = []
        for i, item in enumerate(menu_items_raw):
            b_id = _slugify(item.get("id") or item.get("title") or f"opt_{i}")
            title = (item.get("title") or f"Option {i+1}").strip()[:24]
            desc = (item.get("description") or "").strip()[:72]
            sec = (item.get("section") or "Explore").strip()[:24]
            action = str(item.get("action") or item.get("flow") or item.get("intent") or "faq").strip().lower()

            button_dict = {
                "id": b_id,
                "title": title,
                "description": desc,
                "section": sec,
                "sort_order": i + 1,
                "enabled": True if item.get("enabled", True) else False,
            }
            # Map kit "action" labels onto schema fields (MenuButton forbids "action")
            if action in ("offerings", "catalog", "offering_details", "products"):
                button_dict["intent"] = "offerings"
            elif action in ("quote", "get_quote", "pricing"):
                button_dict["flow"] = "get_quote"
            elif action in ("book_callback", "callback", "enquire", "inquire", "appointment"):
                button_dict["flow"] = "book_callback"
            elif action in ("raise_ticket", "support", "ticket", "help"):
                button_dict["flow"] = "raise_ticket"
            elif action in ("faq", "info"):
                button_dict["intent"] = "faq" if b_id == "faq" else b_id
            elif item.get("flow"):
                button_dict["flow"] = str(item["flow"])
            elif item.get("intent"):
                button_dict["intent"] = str(item["intent"])
            else:
                button_dict["intent"] = b_id

            menu_buttons.append(button_dict)

        has_real_menu = len(menu_buttons) > 0
        if not menu_buttons and not careful_brand_merge:
            menu_buttons = [
                {"id": "offerings", "title": "Explore Offerings"[:24], "description": "Browse catalog"[:72], "section": "Main"[:24], "intent": "offerings", "sort_order": 1, "enabled": True},
                {"id": "callback", "title": "Book Consultation"[:24], "description": "Request a callback"[:72], "section": "Main"[:24], "flow": "book_callback", "sort_order": 2, "enabled": True},
                {"id": "support", "title": "Customer Help"[:24], "description": "Ask questions"[:72], "section": "Main"[:24], "flow": "raise_ticket", "sort_order": 3, "enabled": True},
            ]
        summary["menu_buttons_count"] = len(menu_buttons)

        # 3.4 Sanitize Intents
        intents_raw = bifurcation.get("intents", []) or []
        clean_intents = []
        for intent in intents_raw:
            i_name = _slugify(intent.get("name") or "custom_intent")
            examples = [ex.strip() for ex in intent.get("examples", []) if ex.strip()][:5]
            keywords = [kw.strip() for kw in intent.get("keywords", []) if kw.strip()][:10]
            clean_intents.append({
                "name": i_name,
                "examples": examples,
                "keywords": keywords,
                "flow": intent.get("flow") or None,
                "enabled": True,
            })
        summary["intents_count"] = len(clean_intents)

        # 3.5 Update Tenant Profile Draft (careful mode skips placeholder overwrites)
        draft = tenancy_store.get_draft(tenant_id) or {}
        existing_brand = dict(draft.get("brand") or {})
        should_touch_profile = (
            not careful_brand_merge
            or has_real_brand
            or has_real_menu
            or bool(clean_intents)
            or ("business_hours" in bifurcation and bifurcation.get("business_hours"))
        )

        if should_touch_profile:
            draft["tenant_id"] = tenant_id
            if not careful_brand_merge or vertical != "generic" or not draft.get("vertical"):
                draft["vertical"] = vertical

            if careful_brand_merge:
                merged_brand = {**existing_brand}
                for k, v in real_brand.items():
                    merged_brand[k] = v
                if merged_brand.get("website") and not str(merged_brand["website"]).startswith("http"):
                    merged_brand["website"] = "https://" + str(merged_brand["website"]).lstrip("/")
                draft["brand"] = merged_brand or existing_brand
                if real_brand.get("name"):
                    draft["display_name"] = real_brand["name"]
                summary["brand"] = draft.get("brand") or {}
                summary["brand_updated"] = bool(real_brand)
            else:
                draft["display_name"] = clean_brand["name"]
                draft["brand"] = clean_brand
                summary["brand_updated"] = True

            if has_real_menu or not careful_brand_merge:
                brand_for_menu = draft.get("brand") or clean_brand
                draft["menu"] = {
                    "key": "kb_main",
                    "header": brand_for_menu.get("name") or clean_brand["name"],
                    "body": "Welcome! How can we assist you today?",
                    "footer": "Select an option or type your query directly",
                    "button_text": "Select Option",
                    "buttons": menu_buttons,
                }

            if clean_intents:
                existing_intents = {i["name"]: i for i in draft.get("intents", []) if isinstance(i, dict) and i.get("name")}
                for ci in clean_intents:
                    existing_intents[ci["name"]] = ci
                draft["intents"] = list(existing_intents.values())

            if "business_hours" in bifurcation and bifurcation.get("business_hours"):
                draft["business_hours"] = _sanitize_business_hours(bifurcation["business_hours"])

            bot_name = (draft.get("brand") or {}).get("bot_name") or clean_brand["bot_name"]
            if "flows" not in draft or not draft["flows"]:
                draft["flows"] = [
                    {"name": "book_callback", "success_message": f"Thank you! Your consultation request has been scheduled with {bot_name}."},
                    {"name": "get_quote", "success_message": "Thank you! Our specialist will prepare a customized quote and follow up promptly."},
                    {"name": "raise_ticket", "success_message": "Your request has been logged. A support ticket has been created and an executive will assist you."},
                ]

            with get_db_context() as conn:
                tenancy_store.save_draft(tenant_id, draft, updated_by=self.actor.get("username", "admin"), conn=conn)
                if auto_publish:
                    try:
                        version = tenancy_store.publish_version(
                            tenant_id, draft, published_by=self.actor.get("username", "admin"), conn=conn
                        )
                        summary["version"] = version
                        tenancy_cache.purge(tenant_id)
                        logger.info("AUTO_BIFURCATION_PUBLISHED | tenant=%s | v=%s", tenant_id, version)
                    except Exception as pub_exc:
                        logger.warning("Could not auto-publish version directly: %s", pub_exc)

            try:
                tenancy_loader.write_client_config_file(tenant_id, draft)
            except Exception as file_exc:
                logger.warning("Could not sync client config file: %s", file_exc)

        # 3.6 Insert Offerings into Catalog (products table) — always live (is_active=1)
        offerings_raw = bifurcation.get("offerings", []) or []
        existing_products = {p.get("name", "").lower(): p for p in list_products(tenant_id=tenant_id, active_only=False)}
        inserted_count = 0

        for off in offerings_raw:
            name = (off.get("name") or "").strip()
            if not name:
                continue
            cat = (off.get("category") or "General").strip()
            price = (str(off.get("price") or "")).strip() or None
            short_desc = (off.get("short_description") or name).strip()
            desc = (off.get("description") or short_desc).strip()
            attrs = off.get("attrs") or {}
            slug = _slugify(name)
            media_url = (off.get("media_url") or "").strip() or None
            if not media_url and isinstance(attrs, dict):
                for k in ("media_url", "image_url", "image", "photo"):
                    v = attrs.get(k)
                    if isinstance(v, str) and v.strip():
                        media_url = v.strip()
                        break
            media_type = (off.get("media_type") or "image").strip() or "image"
            if media_url and media_url.lower().endswith(".pdf"):
                media_type = "pdf"

            if name.lower() in existing_products:
                prod_id = existing_products[name.lower()]["id"]
                update_kwargs = dict(
                    tenant_id=tenant_id,
                    price=price,
                    description=desc,
                    short_description=short_desc,
                    category=cat,
                    attrs_json=attrs,
                    is_active=1,
                )
                if media_url:
                    update_kwargs["media_url"] = media_url
                    update_kwargs["media_type"] = media_type
                update_product(prod_id, **update_kwargs)
            else:
                save_product(
                    name=name,
                    slug=slug,
                    category=cat,
                    price=price,
                    short_description=short_desc,
                    description=desc,
                    attrs_json=attrs,
                    media_url=media_url,
                    media_type=media_type,
                    tenant_id=tenant_id,
                    actor=self.actor,
                    is_active=1,
                )
                inserted_count += 1
                if len(summary["offerings_sample"]) < 5:
                    summary["offerings_sample"].append(name)

        summary["offerings_created"] = inserted_count

        # 3.6b Persist FAQ Q&A pairs into faq_dataset (live index)
        faqs_raw = bifurcation.get("faqs", []) or []
        faqs_saved = self._save_faq_pairs(faqs_raw, source_file=kb_source)
        summary["faqs_saved"] = faqs_saved

        # 3.7 Write Knowledge Base Markdown Files & Build Vector Embeddings
        knowledge_dir = Path("clients") / tenant_id / "knowledge"
        knowledge_dir.mkdir(parents=True, exist_ok=True)

        articles = bifurcation.get("knowledge_articles", []) or []
        all_chunks_to_index: List[str] = []

        for idx, art in enumerate(articles):
            title = art.get("title", f"Knowledge Article {idx+1}")
            md_content = art.get("markdown_content", "")
            file_slug = f"{idx+1:02d}_{_slugify(title)}.md"
            target_path = knowledge_dir / file_slug
            try:
                target_path.write_text(md_content, encoding="utf-8")
            except Exception as e:
                logger.warning("Could not write knowledge file %s: %s", target_path, e)

            sections = md_content.split("\n## ")
            for sec in sections:
                if sec.strip():
                    all_chunks_to_index.append(sec.strip())

        for rf in raw_files:
            txt = rf.get("text", "")
            if txt:
                paragraphs = [p.strip() for p in txt.split("\n\n") if len(p.strip()) > 80]
                all_chunks_to_index.extend(paragraphs[:50])

        if all_chunks_to_index:
            try:
                formatted_chunks = [
                    {"content": ch, "source_file": kb_source}
                    for ch in all_chunks_to_index
                ]
                save_knowledge_base_chunks(
                    chunks=formatted_chunks,
                    source_file=kb_source,
                    tenant_id=tenant_id,
                )
                try:
                    from kb.services.rag import (
                        build_chunks_for_kb,
                        generate_missing_embeddings,
                        rebuild_faiss_index,
                    )
                    build_chunks_for_kb()
                    generate_missing_embeddings()
                    rebuild_faiss_index()
                    logger.info("VECTOR_RAG_INDEX_REBUILT | tenant=%s | chunks=%d", tenant_id, len(all_chunks_to_index))
                except Exception as rag_err:
                    logger.warning("RAG vector rebuild error: %s", rag_err)

                summary["kb_chunks_indexed"] = len(all_chunks_to_index)
            except Exception as chunk_err:
                logger.error("Failed storing knowledge base chunks: %s", chunk_err)

        try:
            with get_db_context() as conn:
                record_admin_audit_event(
                    conn,
                    action="tenant_auto_bifurcated",
                    actor=self.actor,
                    resource_type="tenant",
                    resource_id=tenant_id,
                    tenant_id=tenant_id,
                    details={
                        "vertical": vertical,
                        "brand": (summary.get("brand") or {}).get("name"),
                        "offerings_count": inserted_count,
                        "faqs_saved": faqs_saved,
                        "menu_buttons_count": len(menu_buttons),
                        "intents_count": len(clean_intents),
                        "chunks_count": summary["kb_chunks_indexed"],
                        "careful_brand_merge": careful_brand_merge,
                        "source_file": kb_source,
                    },
                )
        except Exception:
            pass

        return summary

    def _save_faq_pairs(self, faqs: List[Dict[str, Any]], source_file: str) -> int:
        """Persist extracted Q&A into faq_dataset and rebuild the FAQ index."""
        if not faqs:
            return 0
        saved = 0
        try:
            chunks = []
            for f in faqs:
                q = (f.get("question") or "").strip()
                a = (f.get("answer") or "").strip()
                if not q or not a:
                    continue
                chunks.append({
                    "source_file": source_file,
                    "content_type": "qa",
                    "content": f"Q: {q}\nA: {a}",
                    "page_number": 1,
                })
            if not chunks:
                return 0
            save_chunks(chunks, module="faq", tenant_id=self.tenant_id)
            saved = len(chunks)
            try:
                from faq.service import faq_index
                faq_index.build(force=True)
            except Exception as idx_err:
                logger.warning("FAQ index rebuild after bifurcation failed: %s", idx_err)
            logger.info("FAQ_PAIRS_SAVED | tenant=%s | count=%d | source=%s", self.tenant_id, saved, source_file)
        except Exception as exc:
            logger.error("Failed saving FAQ pairs: %s", exc)
        return saved

    def process_document_bytes(
        self,
        filename: str,
        content: bytes,
        auto_publish: bool = True,
        careful_brand_merge: bool = True,
    ) -> Dict[str, Any]:
        """Extract + bifurcate a single already-saved upload without re-writing the file."""
        doc_data = self.extract_file_content(filename, content)
        bifurcation = self.bifurcate_with_llm([doc_data])
        result = self.apply_bifurcation(
            bifurcation=bifurcation,
            raw_files=[doc_data],
            auto_publish=auto_publish,
            careful_brand_merge=careful_brand_merge,
            source_file=filename,
        )
        result["files_processed"] = [filename]
        return result

    # ──────────────────────────────────────────────────────────────────────────
    # 4. High-Level Coordinator
    # ──────────────────────────────────────────────────────────────────────────

    def process_files(
        self,
        files_data: List[Dict[str, Any]],
        auto_publish: bool = True,
    ) -> Dict[str, Any]:
        """End-to-end extraction, bifurcation, and system configuration."""
        extracted_docs = []

        # Ensure upload directory exists
        upload_dir = os.path.join("backend", "uploaded_files", "kb")
        os.makedirs(upload_dir, exist_ok=True)

        for f in files_data:
            filename = f.get("filename") or "document.pdf"
            content = f.get("content") or b""
            if isinstance(content, str):
                import base64
                content = base64.b64decode(content)

            # Save uploaded raw file to disk
            filepath = os.path.join(upload_dir, filename)
            try:
                with open(filepath, "wb") as disk_file:
                    disk_file.write(content)
                ext = Path(filename).suffix.lstrip(".")
                save_admin_file(
                    filename,
                    ext,
                    "kb",
                    len(content),
                    file_path=filepath,
                    tenant_id=self.tenant_id,
                    actor=self.actor,
                )
            except Exception as write_err:
                logger.warning("Could not save admin file %s: %s", filename, write_err)

            # Extract content
            doc_data = self.extract_file_content(filename, content)
            extracted_docs.append(doc_data)

        # Run LLM semantic bifurcation
        bifurcation = self.bifurcate_with_llm(extracted_docs)

        # Apply bifurcation across all components (full reconfigure — not careful merge)
        primary_source = extracted_docs[0]["filename"] if extracted_docs else "auto_bifurcated_docs.md"
        result_summary = self.apply_bifurcation(
            bifurcation=bifurcation,
            raw_files=extracted_docs,
            auto_publish=auto_publish,
            careful_brand_merge=False,
            source_file=primary_source,
        )

        result_summary["files_processed"] = [d["filename"] for d in extracted_docs]
        return result_summary
