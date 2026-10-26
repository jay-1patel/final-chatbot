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


# ── Full-corpus helpers (kit-agnostic uploads) ──────────────────────────────
_CHUNK_CHARS = 14000
_CHUNK_OVERLAP = 600
_MAX_LLM_CHUNKS = 10
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(
    r"(?:\+?\d{1,3}[\s\-]?)?(?:\(?\d{2,5}\)?[\s\-]?)?\d{5,10}(?:[\s\-]?\d{3,6})?"
)
_URL_RE = re.compile(r"https?://[^\s\)\]\>\"']+|www\.[^\s\)\]\>\"']+", re.IGNORECASE)
_FAQ_BOLD_RE = re.compile(
    r"(?m)^\s*[-*]?\s*\*\*(.+?\?)\*\*\s*[-–—:]?\s*(.+?)(?=\n\s*[-*]?\s*\*\*|\n#{1,3}\s|\n---|\Z)",
    re.DOTALL,
)
_FAQ_QA_RE = re.compile(
    r"(?mi)^\s*(?:Q(?:uestion)?\s*[:.)]\s*)(.+?\?)\s*\n\s*(?:A(?:nswer)?\s*[:.)]\s*)(.+?)(?=\n\s*(?:Q(?:uestion)?\s*[:.)]|\n#{1,3}\s|\n---|\Z))",
    re.DOTALL,
)


def _chunk_text(text: str, size: int = _CHUNK_CHARS, overlap: int = _CHUNK_OVERLAP) -> List[str]:
    """Split long corpus into overlapping windows so nothing is dropped for the LLM."""
    text = text or ""
    if len(text) <= size:
        return [text] if text.strip() else []
    chunks: List[str] = []
    start = 0
    n = len(text)
    while start < n and len(chunks) < _MAX_LLM_CHUNKS:
        end = min(start + size, n)
        if end < n:
            # Prefer breaking on a paragraph / heading boundary
            window = text[start:end]
            br = max(window.rfind("\n## "), window.rfind("\n\n"), window.rfind("\n---"))
            if br > size // 3:
                end = start + br
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    # Tail remainder if we hit MAX_LLM_CHUNKS early — append a densified tail sample
    if chunks and start + overlap < n and len(chunks) >= _MAX_LLM_CHUNKS:
        tail = text[-size:].strip()
        if tail and tail not in chunks:
            chunks[-1] = chunks[-1] + "\n\n--- TAIL OF DOCUMENT ---\n" + tail
    return chunks


def _normalize_phone(raw: str) -> str:
    digits = re.sub(r"[^\d+]", "", raw or "")
    if digits.startswith("00"):
        digits = "+" + digits[2:]
    if len(re.sub(r"\D", "", digits)) < 10:
        return ""
    return raw.strip()


def _guess_vertical(text: str) -> str:
    sample = (text or "").lower()
    slug_hints = (
        ("it_software", "it_software"),
        ("software & it", "it_software"),
        ("cpaas", "it_software"),
        ("saas product", "it_software"),
        ("real_estate", "real_estate"),
        ("rera", "real_estate"),
        ("tours_travel", "tours_travel"),
        ("itinerary", "tours_travel"),
        ("ecommerce", "ecommerce"),
        ("add to cart", "ecommerce"),
        ("healthcare", "healthcare"),
        ("patient", "healthcare"),
        ("banking", "banking"),
        ("ifsc", "banking"),
        ("gst filing", "finance"),
        ("nbfc", "finance"),
    )
    for needle, slug in slug_hints:
        if needle in sample:
            return slug
    scores = {
        "it_software": sum(
            1
            for w in (
                "software", "devops", "tech stack", "fastapi", "react", "kubernetes",
                "flutter", "machine learning", "whatsapp business api", "cpaas", "saas",
            )
            if w in sample
        ),
        "real_estate": sum(1 for w in ("property", "bhk", "villa", "penthouse", "rera", "carpet area") if w in sample),
        "tours_travel": sum(1 for w in ("flight", "tour", "itinerary", "visa", "holiday") if w in sample),
        "ecommerce": sum(1 for w in ("sku", "cart", "warranty", "cod", "shipping") if w in sample),
        "healthcare": sum(1 for w in ("clinic", "doctor", "hospital", "consultation") if w in sample),
        "banking": sum(1 for w in ("credit card", "atm", "savings account", "loan emi") if w in sample),
        "finance": sum(1 for w in ("gst", "itr", "gold loan", "accounting") if w in sample),
    }
    best = max(scores.items(), key=lambda kv: kv[1])
    return best[0] if best[1] > 0 else "generic"


def _section_body(text: str, headings: Tuple[str, ...], max_chars: int = 4500) -> str:
    """Pull body text under the first matching markdown/plain heading."""
    if not text:
        return ""
    pattern = "|".join(re.escape(h) for h in headings)
    # Match: ## 4. Technologies / …  OR  ### Careers  OR  **Why choose…**
    # Stop only at next H2 (##) / H1 or thematic break — keep ### subsections.
    m = re.search(
        rf"(?im)^(?:#{{1,3}}\s*|\*\*)?(?:\d+[.)]\s*)?(?:{pattern})[^\n]*?(?:\*\*)?\s*$"
        rf"\n+(.*?)(?=\n##\s|\n#\s|\n---\s*\n|\Z)",
        text,
        flags=re.DOTALL,
    )
    if not m:
        return ""
    body = _clean_text(m.group(1))
    lines = []
    for line in body.splitlines():
        s = line.strip()
        if s.startswith("![") and "](" in s:
            continue
        lines.append(line)
    body = "\n".join(lines).strip()
    return body[:max_chars]


def _extract_markdown_table_rows(text: str) -> List[List[str]]:
    """Parse simple GitHub-flavored markdown tables into row lists."""
    rows: List[List[str]] = []
    for block in re.split(r"\n{2,}", text or ""):
        lines = [ln.strip() for ln in block.splitlines() if ln.strip().startswith("|")]
        if len(lines) < 2:
            continue
        parsed = []
        for ln in lines:
            if re.match(r"^\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?$", ln):
                continue
            cells = [c.strip() for c in ln.strip("|").split("|")]
            if cells:
                parsed.append(cells)
        if len(parsed) >= 2:
            rows.extend(parsed)
    return rows


def heuristic_extract_corpus(text: str, tenant_id: str = "") -> Dict[str, Any]:
    """Deterministic extraction from any free-form / scraped document (no kit needed)."""
    text = text or ""
    brand: Dict[str, str] = {}

    # Company name: first H1 or leading title line
    h1 = re.search(r"(?m)^#\s+(.+?)(?:\s*[–—-].*)?$", text)
    if h1:
        name = re.sub(r"\s*[–—:].*$", "", h1.group(1)).strip()
        name = re.sub(r"\b(website knowledge base|knowledge base|onboarding)\b", "", name, flags=re.I).strip(" –—-|")
        if name and len(name) > 2:
            brand["name"] = name[:80]

    tag = re.search(r"(?im)(?:tagline|motto)\s*[:\-–]\s*\*?([^*\n]{8,120})\*?", text)
    if tag:
        brand["tagline"] = tag.group(1).strip(" *")
    else:
        italic = re.search(r"(?m)^\s*\*([^*\n]{12,120})\*\s*$", text)
        if italic:
            brand["tagline"] = italic.group(1).strip()

    emails = _EMAIL_RE.findall(text)
    # Prefer sales/support/info over personal
    ranked_emails = sorted(
        set(emails),
        key=lambda e: (
            0 if re.search(r"^(sales|support|info|hello|contact|admin)@", e, re.I) else 1,
            len(e),
        ),
    )
    if ranked_emails:
        brand["support_email"] = ranked_emails[0]

    phones: List[str] = []
    for m in re.finditer(
        r"(?:\+91[\s\-]?)?(?:0)?[6-9]\d{9}|\+\d{1,3}[\s\-]?\d{6,14}",
        text,
    ):
        p = _normalize_phone(m.group(0))
        if p and p not in phones:
            phones.append(p)
    if phones:
        brand["support_phone"] = phones[0]

    urls = _URL_RE.findall(text)
    site = ""
    for u in urls:
        low = u.lower().rstrip(").,;")
        if any(x in low for x in ("facebook", "instagram", "linkedin", "twitter", "youtube", "wa.me")):
            continue
        if "/assets/" in low or low.endswith((".webp", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".avif")):
            continue
        site = u.rstrip(").,;")
        break
    if site:
        brand["website"] = site if site.startswith("http") else f"https://{site}"

    if brand.get("name"):
        brand["bot_name"] = f"{brand['name'].split()[0]} Assistant"
        brand["signature"] = f"{brand['name']} — At your service."

    # Hours
    hours_m = re.search(
        r"(?i)(?:business\s+hours|working\s+hours|office\s+hours|timing)\s*[:\-–]\s*([^\n]{6,80})",
        text,
    )
    always = bool(re.search(r"\b24\s*/\s*7\b|\balways\s+open\b", text, re.I))
    business_hours: Dict[str, Any] = {
        "timezone": "Asia/Kolkata",
        "open": "09:30",
        "close": "18:30",
        "open_days": [0, 1, 2, 3, 4, 5],
        "always_open": always,
    }
    if hours_m:
        business_hours["raw"] = hours_m.group(1).strip()

    # FAQs
    faqs: List[Dict[str, str]] = []
    seen_q: set = set()
    _faq_noise = re.compile(
        r"(?i)^(source|note|pages?|http|www\.|menu:|read more|click|image)",
    )

    def _add_faq(q: str, a: str, category: str = "General") -> None:
        q = _clean_text(q).strip(" *")
        a = _clean_text(a)
        if len(q) < 12 or len(a) < 8:
            return
        if not q.endswith("?"):
            return
        if _faq_noise.search(q) or "http" in q.lower():
            return
        if a.lower().startswith("http") and len(a) < 80:
            return
        key = q.lower()
        if key in seen_q:
            return
        seen_q.add(key)
        faqs.append({"question": q[:300], "answer": a[:2000], "category": category})

    for q, a in _FAQ_BOLD_RE.findall(text):
        _add_faq(q, a)
    for q, a in _FAQ_QA_RE.findall(text):
        _add_faq(q, a)
    for m in re.finditer(
        r"(?m)^\s*[-*]\s+\*\*(.+?\?)\*\*\s*(.+)$",
        text,
    ):
        _add_faq(m.group(1), m.group(2))

    # Info-page intents from common headings
    info_specs = [
        ("technologies", ("technologies", "tech stack", "our stack", "technologies / development")),
        ("projects", ("projects", "portfolio", "case studies", "our work", "trusted partners", "impact numbers")),
        ("careers", ("careers", "open positions", "hiring", "jobs", "life @ leeway", "life @")),
        ("benefits", ("why choose", "why us", "benefits", "why work with", "why choose leeway")),
    ]
    intents: List[Dict[str, Any]] = []
    for name, heads in info_specs:
        body = _section_body(text, heads)
        if body and len(body) > 40:
            intents.append({
                "name": name,
                "description": name.replace("_", " ").title(),
                "keywords": [name, name.replace("_", " ")],
                "examples": [f"tell me about {name}", f"what about your {name}"],
                "answer": body[:3500],
                "flow": None,
                "enabled": True,
            })

    # Offerings from markdown product/service tables and ### headings under Services
    offerings: List[Dict[str, Any]] = []
    seen_off: set = set()

    _offering_blocklist = {
        "need", "solutions", "category", "product", "role", "department", "office",
        "location", "client", "logo", "frontend", "backend", "ai & ml", "mobile",
        "databases and data platforms", "certified security and quality",
        "proven at scale", "government-grade trust", "true end-to-end delivery",
    }

    def _add_offering(name: str, category: str, desc: str, media: str = "") -> None:
        name = _clean_text(name).strip(" *")
        if len(name) < 3:
            return
        key = name.lower()
        if key in seen_off or key in _offering_blocklist or key.startswith("product"):
            return
        # Skip job-title / office-looking rows without a product signal
        if category and category.lower() in ("sales", "tester", "account", "hr", "manager", "design", "support", "mumbai", "bhavnagar", "delhi/ncr"):
            return
        seen_off.add(key)
        offerings.append({
            "name": name[:120],
            "category": (category or "Services")[:80],
            "price": "",
            "short_description": (desc or "")[:180],
            "description": (desc or name)[:2000],
            "unit": "package",
            "media_url": media or "",
            "media_type": "image" if media else "",
            "attrs": {},
        })

    def _skip_table_rows(start_idx: int) -> int:
        j = start_idx + 1
        header_words = {
            "product", "service", "name", "package", "role", "need", "client",
            "office", "category", "what it does",
        }
        while j < len(md_rows):
            first = (md_rows[j][0] if md_rows[j] else "").strip().lower()
            row_l = " ".join(c.lower() for c in md_rows[j])
            if first in header_words or (
                any(k in row_l for k in ("what it does", "department", "experience", "address"))
                and first in header_words.union({"product", "role", "office", "need"})
            ):
                break
            # New header if most cells look like labels
            if first in header_words:
                break
            j += 1
        return j

    md_rows = _extract_markdown_table_rows(text)
    i = 0
    while i < len(md_rows):
        row = md_rows[i]
        header_l = " ".join(c.lower() for c in row)
        first_h = (row[0] if row else "").strip().lower()
        is_career = "role" in header_l and ("department" in header_l or "experience" in header_l)
        is_need_matrix = first_h == "need" or ("need" in header_l and "solution" in header_l)
        is_logo_table = "client" in header_l and "logo" in header_l
        is_office_table = first_h == "office" or ("office" in header_l and "address" in header_l)
        is_tech_table = first_h == "category" and "technologies" in header_l
        is_productish = any(
            k in header_l for k in ("product", "what it does", "service name", "package name", "sku")
        )
        if is_career or is_need_matrix or is_logo_table or is_office_table or is_tech_table:
            i = _skip_table_rows(i)
            continue
        if is_productish:
            headers = [c.lower() for c in row]
            i += 1
            while i < len(md_rows):
                data = md_rows[i]
                first = (data[0] if data else "").strip().lower()
                if first in ("product", "service", "name", "package", "role", "need", "office", "category"):
                    break
                name = data[0] if data else ""
                desc = data[1] if len(data) > 1 else ""
                cat = "Services"
                if "category" in headers:
                    try:
                        ci = headers.index("category")
                        cat = data[ci] if ci < len(data) else cat
                    except Exception:
                        pass
                link = ""
                for cell in data:
                    um = _URL_RE.search(cell)
                    if um:
                        link = um.group(0).rstrip(").,;")
                        break
                if name and not str(name).lower().endswith("?"):
                    _add_offering(str(name), str(cat), str(desc), link)
                i += 1
            continue
        i += 1

    # Numbered service groups only (1. **Name** – desc) — skip why-choose / qualities lists
    for m in re.finditer(
        r"(?m)^\s*\d+\.\s+\*\*([^*]{3,80})\*\*\s*[–—:-]\s*(.+)$",
        text,
    ):
        title = m.group(1).strip()
        low = title.lower()
        if low in _offering_blocklist or low in ("source", "note", "headline"):
            continue
        # Prefer capability-style titles
        if any(w in low for w in ("cpaas", "marketing", "development", "hosting", "security", "ai", "mobile", "web", "growth", "communication", "software", "cloud", "data")):
            _add_offering(title, "Services", m.group(2))

    # Knowledge articles from ## sections
    articles: List[Dict[str, str]] = []
    for m in re.finditer(
        r"(?m)^(#{2,3})\s+(.+?)\s*$",
        text,
    ):
        title = m.group(2).strip()
        if re.match(r"(?i)pages still to scrape|source:|note:", title):
            continue
        start = m.end()
        nxt = re.search(r"(?m)^#{2,3}\s+", text[start:])
        end = start + nxt.start() if nxt else len(text)
        body = _clean_text(text[start:end])[:6000]
        if len(body) < 80:
            continue
        articles.append({
            "title": re.sub(r"^\d+\.\s*", "", title)[:120],
            "category": "Company",
            "markdown_content": f"# {title}\n\n{body}",
        })
        if len(articles) >= 20:
            break

    vertical = _guess_vertical(text)
    return {
        "vertical": vertical,
        "brand": brand,
        "business_hours": business_hours,
        "menu_items": [],
        "intents": intents,
        "offerings": offerings,
        "faqs": faqs,
        "knowledge_articles": articles,
    }


def _dedupe_key_offering(item: Dict[str, Any]) -> str:
    return _slugify(str(item.get("name") or ""))


def _dedupe_key_faq(item: Dict[str, Any]) -> str:
    return _slugify(str(item.get("question") or ""))[:80]


def _dedupe_key_intent(item: Dict[str, Any]) -> str:
    return str(item.get("name") or "").strip().lower()


def _dedupe_key_article(item: Dict[str, Any]) -> str:
    return _slugify(str(item.get("title") or ""))


def merge_bifurcation_results(*parts: Optional[Dict[str, Any]], tenant_id: str = "") -> Dict[str, Any]:
    """Union multiple bifurcation JSON blobs; prefer richer non-placeholder values."""
    merged: Dict[str, Any] = {
        "vertical": "generic",
        "brand": {},
        "business_hours": {},
        "menu_items": [],
        "intents": [],
        "offerings": [],
        "faqs": [],
        "knowledge_articles": [],
    }
    vertical_votes: Dict[str, int] = {}

    def _prefer_brand(dst: Dict[str, Any], src: Dict[str, Any]) -> None:
        for key, val in (src or {}).items():
            if not val:
                continue
            if _is_placeholder_brand_value(key, val, tenant_id):
                continue
            cur = dst.get(key)
            if not cur or _is_placeholder_brand_value(key, cur, tenant_id) or len(str(val)) > len(str(cur)):
                dst[key] = val

    def _extend(list_key: str, items: Any, key_fn) -> None:
        if not isinstance(items, list):
            return
        existing: Dict[str, int] = {}
        for i, x in enumerate(merged[list_key]):
            if isinstance(x, dict):
                ek = str(key_fn(x) or "").strip().lower()
                if ek:
                    existing[ek] = i
        for item in items:
            if not isinstance(item, dict):
                continue
            sk = str(key_fn(item) or "").strip().lower()
            if not sk:
                continue
            if sk in existing:
                cur = merged[list_key][existing[sk]]
                for field in ("answer", "description", "short_description", "markdown_content", "question"):
                    if len(str(item.get(field) or "")) > len(str(cur.get(field) or "")):
                        cur[field] = item[field]
                for field, val in item.items():
                    if val and (field not in cur or not cur.get(field)):
                        cur[field] = val
            else:
                existing[sk] = len(merged[list_key])
                merged[list_key].append(dict(item))

    for part in parts:
        if not part or not isinstance(part, dict):
            continue
        v = part.get("vertical")
        if v and v in VALID_VERTICALS:
            vertical_votes[v] = vertical_votes.get(v, 0) + 1
        _prefer_brand(merged["brand"], part.get("brand") or {})
        bh = part.get("business_hours")
        if isinstance(bh, dict) and (bh.get("raw") or bh.get("open") or bh.get("always_open")):
            if not merged["business_hours"] or bh.get("raw") or bh.get("always_open"):
                merged["business_hours"] = {**merged["business_hours"], **bh}
        _extend("menu_items", part.get("menu_items"), lambda x: _slugify(str(x.get("id") or x.get("title") or "")))
        _extend("intents", part.get("intents"), _dedupe_key_intent)
        _extend("offerings", part.get("offerings"), _dedupe_key_offering)
        _extend("faqs", part.get("faqs"), _dedupe_key_faq)
        _extend("knowledge_articles", part.get("knowledge_articles"), _dedupe_key_article)

    if vertical_votes:
        merged["vertical"] = max(vertical_votes.items(), key=lambda kv: kv[1])[0]
    elif merged.get("vertical") not in VALID_VERTICALS:
        merged["vertical"] = "generic"

    brand = merged["brand"]
    if brand.get("name") and not brand.get("bot_name"):
        brand["bot_name"] = f"{str(brand['name']).split()[0]} Assistant"
    if brand.get("name") and not brand.get("signature"):
        brand["signature"] = f"{brand['name']} — At your service."

    if len(merged["menu_items"]) < 3:
        v_defaults = get_vertical_defaults(merged["vertical"]) or {}
        for b in (v_defaults.get("menu", {}) or {}).get("buttons", [])[:6]:
            merged["menu_items"].append({
                "id": b.get("id", "menu_item"),
                "title": str(b.get("title", "Explore"))[:24],
                "description": str(b.get("description", "View options"))[:72],
                "section": str(b.get("section", "Explore"))[:24],
                "action": b.get("flow") or b.get("requires_feature") or b.get("intent") or "offerings",
            })

    return merged


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

    def _bifurcation_system_prompt(self, focus: str = "full") -> str:
        """Shared JSON schema prompt; ``focus`` narrows extraction for multi-pass."""
        focus_note = {
            "full": "Extract EVERYTHING: brand, menu, intents, offerings, faqs, knowledge_articles.",
            "brand": "Focus on brand profile, vertical, business_hours, and WhatsApp menu_items. Leave offerings/faqs thin if needed.",
            "catalog": "Focus on offerings (every product/service/package) and knowledge_articles. Keep brand minimal.",
            "faq_info": "Focus on faqs (every Q&A) and intents (technologies/projects/careers/benefits with full answer text). Keep brand minimal.",
        }.get(focus, "Extract all fields you can from this chunk.")

        return f"""You are an elite enterprise AI data architect and WhatsApp chatbot configurator.
Tenant ID: '{self.tenant_id}'.
Documents may be onboarding kits, website scrapes, PDFs, Markdown knowledge bases, or unstructured notes — treat all equally.
Pass focus: {focus_note}

Output a strictly valid JSON object:
{{
  "vertical": "real_estate" | "tours_travel" | "ecommerce" | "it_software" | "banking" | "finance" | "healthcare" | "generic",
  "brand": {{
    "name": "Official Company / Entity Name",
    "bot_name": "Friendly AI Assistant Name",
    "tagline": "1-2 sentence value proposition",
    "website": "Valid URL",
    "support_email": "Official support email",
    "support_phone": "Phone with country code",
    "signature": "Brand sign-off"
  }},
  "business_hours": {{
    "timezone": "Asia/Kolkata",
    "open": "09:30",
    "close": "18:30",
    "open_days": [0, 1, 2, 3, 4, 5],
    "always_open": false
  }},
  "menu_items": [
    {{
      "id": "browse_offerings",
      "title": "Explore Offerings",
      "description": "Browse catalog or services",
      "section": "Explore",
      "action": "offerings"
    }}
  ],
  "intents": [
    {{
      "name": "technologies",
      "description": "Tech stack and tools",
      "keywords": ["tech stack", "technologies"],
      "examples": ["what technologies do you use"],
      "answer": "• Real bullet content from the document…",
      "flow": null
    }}
  ],
  "offerings": [
    {{
      "name": "Item Name",
      "category": "Category",
      "price": "Price or empty string",
      "short_description": "One sentence",
      "description": "Details from document",
      "unit": "package",
      "media_url": "",
      "media_type": "image",
      "attrs": {{}}
    }}
  ],
  "faqs": [
    {{"question": "…?", "answer": "…", "category": "General"}}
  ],
  "knowledge_articles": [
    {{"title": "…", "category": "Company", "markdown_content": "# Title\\n\\nBody…"}}
  ]
}}

RULES:
1. Extract ALL products/services/properties into offerings — do not stop at a few examples.
2. Extract EVERY explicit Q&A into faqs.
3. For IT/software content fill intents technologies, projects, careers, benefits with real answer text when present.
4. menu_items titles MUST be <= 24 chars; descriptions <= 72. Map tech/projects/careers/benefits actions to those names.
5. NEVER invent phone, email, website, prices, or hours — omit if missing.
6. Respond ONLY with JSON (no markdown fences).
"""

    def bifurcate_with_llm(self, doc_summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Bifurcate any document type via heuristics + multi-pass LLM (full corpus)."""
        combined_chunks = []
        for doc in doc_summaries:
            txt = doc.get("text") or ""
            combined_chunks.append(
                f"================ DOCUMENT: {doc.get('filename', 'doc')} ================\n{txt}"
            )
        full_corpus = "\n\n".join(combined_chunks)

        # Always run deterministic heuristics on the COMPLETE text (no truncation)
        heuristic = heuristic_extract_corpus(full_corpus, tenant_id=self.tenant_id)
        logger.info(
            "HEURISTIC_EXTRACT | tenant=%s | brand_keys=%s | offerings=%s | faqs=%s | intents=%s | articles=%s",
            self.tenant_id,
            list((heuristic.get("brand") or {}).keys()),
            len(heuristic.get("offerings") or []),
            len(heuristic.get("faqs") or []),
            len(heuristic.get("intents") or []),
            len(heuristic.get("knowledge_articles") or []),
        )

        windows = _chunk_text(full_corpus)
        if not windows:
            return merge_bifurcation_results(heuristic, tenant_id=self.tenant_id)

        llm_parts: List[Dict[str, Any]] = []
        # Pass strategy: brand on first window; catalog/faq on every window
        for idx, window in enumerate(windows):
            if idx == 0:
                focuses = ("brand", "catalog", "faq_info")
            else:
                focuses = ("catalog", "faq_info")
            for focus in focuses:
                system_prompt = self._bifurcation_system_prompt(focus=focus)
                user_prompt = (
                    f"This is chunk {idx + 1} of {len(windows)} from uploaded client collateral.\n"
                    f"Extract per focus='{focus}'. Merge-safe partial JSON is OK.\n\n{window}"
                )
                try:
                    part = self._call_llm_json(system_prompt, user_prompt)
                except Exception as exc:
                    logger.warning("LLM bifurcate chunk=%s focus=%s failed: %s", idx, focus, exc)
                    part = None
                if part:
                    llm_parts.append(part)

        if not llm_parts:
            logger.warning(
                "Bifurcation LLM returned no parts — using heuristics only | tenant=%s",
                self.tenant_id,
            )
            return merge_bifurcation_results(heuristic, tenant_id=self.tenant_id)

        merged = merge_bifurcation_results(heuristic, *llm_parts, tenant_id=self.tenant_id)
        # Prefer heuristic vertical when LLM is generic but heuristics are specific
        if merged.get("vertical") == "generic" and heuristic.get("vertical") in VALID_VERTICALS:
            merged["vertical"] = heuristic["vertical"]
        return merged

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

            "info_pages": r"\[SECTION:\s*INFO\s*PAGES(?:\s*&\s*INTENTS)?\]",

            "guardrails": r"\[SECTION:\s*BOT\s*PERSONA(?:\s*&\s*GUARDRAILS)?\]",

        }



        # Check if standardized section markers exist

        has_markers = any(re.search(pat, combined_text, re.IGNORECASE) for pat in section_patterns.values())



        sections: Dict[str, Dict[str, Any]] = {

            "brand": {"text": "", "tables": []},

            "menu": {"text": "", "tables": []},

            "catalog": {"text": "", "tables": []},

            "faqs": {"text": "", "tables": []},

            "info_pages": {"text": "", "tables": []},

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

                    elif "INFO PAGE" in tag or "INFO PAGES" in tag or tag.strip() in (
                        "TECHNOLOGIES", "PROJECTS", "CAREERS", "BENEFITS",
                    ):
                        current_sec = "info_pages"

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

                elif any(
                    k in first_row_str
                    for k in (
                        "info page",
                        "page name",
                        "intent name",
                        "technologies",
                        "projects",
                        "careers",
                        "benefits",
                        "bot answer",
                    )
                ) and any(
                    k in first_row_str
                    for k in ("page", "intent", "answer", "content", "technologies", "projects", "careers", "benefits")
                ):
                    sections["info_pages"]["tables"].append(tbl)

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

            # Fallback for unformatted/raw collateral — feed full text to every
            # extractor so kit-less uploads still have something to parse.
            sections["brand"]["text"] = combined_text
            sections["catalog"]["text"] = combined_text
            sections["catalog"]["tables"] = all_tables
            sections["faqs"]["text"] = combined_text
            sections["info_pages"]["text"] = combined_text
            sections["menu"]["text"] = combined_text
            sections["guardrails"]["text"] = combined_text

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



        # Step 2: Detect vertical (prefer explicit slug / title, then keyword scores)
        full_sample = (text + " " + json.dumps(parsed_fields)).lower()
        vertical = default_vertical
        slug_hints = (
            ("it_software", "it_software"),
            ("software & it", "it_software"),
            ("real_estate", "real_estate"),
            ("real estate", "real_estate"),
            ("tours_travel", "tours_travel"),
            ("tours & travel", "tours_travel"),
            ("ecommerce", "ecommerce"),
            ("e-commerce", "ecommerce"),
            ("healthcare", "healthcare"),
            ("banking", "banking"),
            ("finance", "finance"),
            ("generic", "generic"),
        )
        for needle, slug in slug_hints:
            if needle in full_sample:
                vertical = slug
                break
        else:
            scores = {
                "real_estate": sum(1 for w in ("property", "bhk", "villa", "penthouse", "rera", "carpet area") if w in full_sample),
                "tours_travel": sum(1 for w in ("flight", "tour", "itinerary", "visa", "holiday") if w in full_sample),
                "it_software": sum(1 for w in ("software", "devops", "tech stack", "fastapi", "react", "kubernetes", "flutter") if w in full_sample),
                "ecommerce": sum(1 for w in ("sku", "cart", "warranty", "cod", "chikki") if w in full_sample),
                "healthcare": sum(1 for w in ("clinic", "doctor", "hospital", "patient", "consultation fee") if w in full_sample),
                "banking": sum(1 for w in ("credit card", "atm", "ifsc", "savings account") if w in full_sample),
                "finance": sum(1 for w in ("gst", "itr", "gold loan", "two-wheeler loan", "nbfc") if w in full_sample),
            }
            best = max(scores.items(), key=lambda kv: kv[1])
            if best[1] > 0:
                vertical = best[0]



        # Free-text contact scrape when kit tables are missing fields
        if text:
            heur_brand = (heuristic_extract_corpus(text, tenant_id=self.tenant_id).get("brand") or {})
            for src_key, dst_key in (
                ("name", "brand_name"),
                ("tagline", "tagline"),
                ("website", "website"),
                ("support_email", "support_email"),
                ("support_phone", "support_phone"),
                ("bot_name", "bot_name"),
            ):
                if heur_brand.get(src_key) and not parsed_fields.get(dst_key):
                    parsed_fields[dst_key] = heur_brand[src_key]
            if not vertical or vertical == default_vertical:
                guessed = _guess_vertical(text)
                if guessed != "generic":
                    vertical = guessed

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
                    action = action.replace(" ", "_").replace("-", "_")

                    # Preserve IT info-page intents and known flows; don't collapse them to offerings
                    info_page_actions = {
                        "technologies", "technology", "tech_stack", "projects", "project",
                        "careers", "career", "benefits", "benefit", "services", "service_enquiry",
                    }
                    if action in info_page_actions or action in (
                        "technologies", "projects", "careers", "benefits", "offerings",
                        "offering_details", "faq", "quote", "get_quote", "book_callback",
                        "raise_ticket", "track_order", "returns",
                    ):
                        if action in ("technology", "tech_stack"):
                            action = "technologies"
                        elif action == "project":
                            action = "projects"
                        elif action == "career":
                            action = "careers"
                        elif action == "benefit":
                            action = "benefits"
                    elif "quote" in action or "price" in action:
                        action = "quote"
                    elif "call" in action or "visit" in action or "appoint" in action:
                        action = "book_callback"
                    elif "ticket" in action or "support" in action or "help" in action:
                        action = "raise_ticket"
                    elif "faq" in action:
                        action = "faq"
                    elif "technolog" in action or "stack" in action:
                        action = "technologies"
                    elif "project" in action or "portfolio" in action or "case" in action:
                        action = "projects"
                    elif "career" in action or "hiring" in action or "job" in action:
                        action = "careers"
                    elif "benefit" in action or "why" in action:
                        action = "benefits"
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



    def extract_info_pages_section(self, sec_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract Technologies / Projects / Careers / Benefits intent answers."""
        INFO_DEFAULTS = {
            "technologies": {
                "keywords": ["technologies", "technology", "tech stack", "stack", "framework", "tools"],
                "examples": ["what technologies do you work with", "what is your tech stack"],
            },
            "projects": {
                "keywords": ["projects", "project", "portfolio", "case study", "case studies", "clients"],
                "examples": ["show me your work", "who have you built for"],
            },
            "careers": {
                "keywords": ["career", "careers", "job", "hiring", "vacancy", "internship", "open role"],
                "examples": ["are you hiring", "job openings at your company"],
            },
            "benefits": {
                "keywords": ["benefits", "why choose you", "why work with you", "advantages", "perks"],
                "examples": ["why should we work with you", "what are the benefits"],
            },
        }
        alias = {
            "technology": "technologies",
            "tech stack": "technologies",
            "tech_stack": "technologies",
            "stack": "technologies",
            "project": "projects",
            "portfolio": "projects",
            "case studies": "projects",
            "career": "careers",
            "hiring": "careers",
            "jobs": "careers",
            "benefit": "benefits",
            "why us": "benefits",
            "why choose us": "benefits",
        }
        found: Dict[str, Dict[str, Any]] = {}
        tables = sec_data.get("tables", []) or []
        text = sec_data.get("text", "") or ""

        for tbl in tables:
            if not tbl or len(tbl[0]) < 2:
                continue
            header = " ".join(str(c or "").lower() for c in tbl[0])
            start = 1
            # Single-page tables whose first header cell is the page name
            first_h = str(tbl[0][0]).strip().lower()
            if first_h in INFO_DEFAULTS or alias.get(first_h) in INFO_DEFAULTS:
                page = alias.get(first_h, first_h)
                body_parts = []
                for row in tbl[1:]:
                    cells = [str(c).strip() for c in row if str(c).strip()]
                    if cells:
                        body_parts.append(" • ".join(cells) if len(cells) > 1 else cells[0])
                answer = "\n".join(f"• {p}" if not p.startswith("•") else p for p in body_parts if p)
                if answer:
                    meta = INFO_DEFAULTS[page]
                    found[page] = {
                        "name": page,
                        "answer": answer,
                        "keywords": list(meta["keywords"]),
                        "examples": list(meta["examples"]),
                        "enabled": True,
                        "flow": None,
                    }
                continue

            if "page" in header or "intent" in header or "answer" in header or "content" in header:
                for row in tbl[start:]:
                    if not row or not str(row[0]).strip():
                        continue
                    raw_name = str(row[0]).strip().lower()
                    page = alias.get(raw_name, raw_name.replace(" ", "_"))
                    if page not in INFO_DEFAULTS:
                        continue
                    answer = str(row[1]).strip() if len(row) > 1 else ""
                    if len(row) > 2 and str(row[2]).strip():
                        answer = (answer + "\n" + str(row[2]).strip()).strip()
                    if not answer or answer.startswith("["):
                        continue
                    meta = INFO_DEFAULTS[page]
                    found[page] = {
                        "name": page,
                        "answer": answer,
                        "keywords": list(meta["keywords"]),
                        "examples": list(meta["examples"]),
                        "enabled": True,
                        "flow": None,
                    }

        # Text blocks like ### Technologies\n...
        if text and len(found) < 4:
            for page in INFO_DEFAULTS:
                if page in found:
                    continue
                m = re.search(
                    rf"(?:^|\n)\s*(?:#+?\s*)?{page}\s*[:\n]+(.+?)(?=\n\s*(?:#+?\s*)?(?:technologies|projects|careers|benefits)\b|\Z)",
                    text,
                    flags=re.IGNORECASE | re.DOTALL,
                )
                if m and m.group(1).strip():
                    meta = INFO_DEFAULTS[page]
                    found[page] = {
                        "name": page,
                        "answer": m.group(1).strip()[:4000],
                        "keywords": list(meta["keywords"]),
                        "examples": list(meta["examples"]),
                        "enabled": True,
                        "flow": None,
                    }

        return list(found.values())

    # ──────────────────────────────────────────────────────────────────────────
    # 5. Staging Pipeline (Review & Edit Before Publish)
    # ──────────────────────────────────────────────────────────────────────────

    def stage_files(self, files_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Parse files into a reviewable staging draft without committing.

        Kit files with ``[SECTION: …]`` markers use deterministic parsers.
        Any other collateral (website scrapes, MD/PDF/DOCX dumps) uses
        full-corpus heuristics + multi-pass LLM so bot details fill without a kit.
        """
        extracted_docs = []
        for f in files_data:
            fname = f.get("filename") or "onboarding_doc.docx"
            content = f.get("content") or b""
            if isinstance(content, str):
                import base64
                content = base64.b64decode(content)
            extracted_docs.append(self.extract_file_content(fname, content))

        combined_text = "\n\n".join(d.get("text") or "" for d in extracted_docs)
        has_kit_markers = bool(
            re.search(r"\[SECTION:\s*(BRAND|WHATSAPP|CATALOG|FAQS|INFO\s*PAGES|BOT\s*PERSONA)", combined_text, re.I)
        )

        if not has_kit_markers:
            # Kit-agnostic path: heuristics + multi-pass LLM over the full corpus
            try:
                draft = self.bifurcate_with_llm(extracted_docs)
            except Exception as exc:
                logger.warning("stage_files LLM path failed (%s); heuristics-only fallback", exc)
                draft = merge_bifurcation_results(
                    heuristic_extract_corpus(combined_text, tenant_id=self.tenant_id),
                    tenant_id=self.tenant_id,
                )
            brand = draft.get("brand") or {}
            if not brand.get("name"):
                brand["name"] = self.tenant_id.replace("-", " ").replace("_", " ").title()
            business_hours = _sanitize_business_hours(draft.get("business_hours") or {})
            menu_items = draft.get("menu_items") or []
            if len(menu_items) < 3:
                menu_items = self.extract_menu_section({"text": "", "tables": []}, vertical=draft.get("vertical") or "generic")
            offerings = draft.get("offerings") or []
            faqs = draft.get("faqs") or []
            articles = draft.get("knowledge_articles") or []
            intents = draft.get("intents") or []
            # Merge kit-style info-page regex hits if LLM missed a page
            extra_info = self.extract_info_pages_section({"text": combined_text, "tables": []})
            if extra_info:
                by_name = {i.get("name"): i for i in intents if isinstance(i, dict)}
                for item in extra_info:
                    name = item.get("name")
                    if not name:
                        continue
                    if name not in by_name or len(str(item.get("answer") or "")) > len(str(by_name[name].get("answer") or "")):
                        by_name[name] = item
                intents = list(by_name.values())
            vertical = draft.get("vertical") or _guess_vertical(combined_text)
            guardrails = {}
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
                "intents": intents,
                "guardrails": guardrails,
                "source_files": [d["filename"] for d in extracted_docs],
                "extraction_mode": "universal",
                "stats": {
                    "offerings_count": len(offerings),
                    "menu_items_count": len(menu_items),
                    "faqs_count": len(faqs),
                    "articles_count": len(articles),
                    "intents_count": len(intents),
                },
            }
            return staged_draft

        sections = self.partition_sections(extracted_docs)
        brand, business_hours, vertical = self.extract_brand_section(sections["brand"])
        # Enrich brand contacts from full corpus when kit tables omit them
        heur = heuristic_extract_corpus(combined_text, tenant_id=self.tenant_id)
        for key in ("support_email", "support_phone", "website", "tagline", "name"):
            hv = (heur.get("brand") or {}).get(key)
            if hv and (not brand.get(key) or _is_placeholder_brand_value(key, brand.get(key), self.tenant_id)):
                brand[key] = hv
        menu_items = self.extract_menu_section(sections["menu"], vertical=vertical)
        offerings = self.extract_catalog_section(sections["catalog"], vertical=vertical)
        faqs, articles = self.extract_faq_section(sections["faqs"], brand_name=brand["name"], vertical=vertical)
        intents = self.extract_info_pages_section(sections.get("info_pages") or {"text": "", "tables": []})
        # Soft-merge heuristic extras so kit uploads still gain scraped-style coverage
        if heur.get("offerings") and len(offerings) < 3:
            offerings = merge_bifurcation_results(
                {"offerings": offerings}, {"offerings": heur["offerings"]}, tenant_id=self.tenant_id
            ).get("offerings") or offerings
        if heur.get("faqs"):
            faqs = merge_bifurcation_results(
                {"faqs": faqs}, {"faqs": heur["faqs"]}, tenant_id=self.tenant_id
            ).get("faqs") or faqs
        if heur.get("intents"):
            intents = merge_bifurcation_results(
                {"intents": intents}, {"intents": heur["intents"]}, tenant_id=self.tenant_id
            ).get("intents") or intents
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
            "intents": intents,
            "guardrails": guardrails,
            "source_files": [d["filename"] for d in extracted_docs],
            "extraction_mode": "kit",
            "stats": {
                "offerings_count": len(offerings),
                "menu_items_count": len(menu_items),
                "faqs_count": len(faqs),
                "articles_count": len(articles),
                "intents_count": len(intents),
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
            if action in ("offerings", "catalog", "offering_details", "products", "services"):
                button_dict["intent"] = "offerings" if action != "services" else "services"
            elif action in ("technologies", "projects", "careers", "benefits"):
                button_dict["intent"] = action
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

        # 3.4 Sanitize Intents (preserve answer text for Technologies/Projects/Careers/Benefits)
        intents_raw = bifurcation.get("intents", []) or []
        clean_intents = []
        for intent in intents_raw:
            i_name = _slugify(intent.get("name") or "custom_intent")
            if i_name in ("technology", "tech_stack"):
                i_name = "technologies"
            elif i_name == "project":
                i_name = "projects"
            elif i_name == "career":
                i_name = "careers"
            elif i_name == "benefit":
                i_name = "benefits"
            examples = [ex.strip() for ex in intent.get("examples", []) if ex.strip()][:5]
            keywords = [kw.strip() for kw in intent.get("keywords", []) if kw.strip()][:10]
            answer = (intent.get("answer") or "").strip()
            entry = {
                "name": i_name,
                "examples": examples,
                "keywords": keywords,
                "flow": intent.get("flow") or None,
                "enabled": True if intent.get("enabled", True) else False,
            }
            if answer:
                entry["answer"] = answer
            clean_intents.append(entry)
        summary["intents_count"] = len(clean_intents)
        summary["info_pages_updated"] = [
            i["name"] for i in clean_intents
            if i["name"] in ("technologies", "projects", "careers", "benefits") and i.get("answer")
        ]

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

            # Company info-page intents (technologies/projects/careers/benefits)
            # are IT-only — never inject them into banking / ecommerce / etc.
            existing_intents = {
                i["name"]: dict(i)
                for i in draft.get("intents", [])
                if isinstance(i, dict) and i.get("name")
            }
            _IT_INFO = ("technologies", "projects", "careers", "benefits")
            try:
                from shared.tenancy.defaults import get_vertical_defaults
                if vertical == "it_software":
                    for di in (get_vertical_defaults(vertical).get("intents") or []):
                        name = di.get("name")
                        if name in _IT_INFO and name not in existing_intents:
                            existing_intents[name] = dict(di)
                else:
                    for name in _IT_INFO:
                        existing_intents.pop(name, None)
            except Exception:
                pass

            if clean_intents:
                for ci in clean_intents:
                    # Skip IT info pages when uploading kits for non-IT verticals
                    if vertical != "it_software" and ci.get("name") in _IT_INFO:
                        continue
                    prev = existing_intents.get(ci["name"], {})
                    merged = {**prev, **{k: v for k, v in ci.items() if v not in (None, "", [], {})}}
                    # Never wipe a prior answer with an empty one
                    if not ci.get("answer") and prev.get("answer"):
                        merged["answer"] = prev["answer"]
                    if not ci.get("examples") and prev.get("examples"):
                        merged["examples"] = prev["examples"]
                    if not ci.get("keywords") and prev.get("keywords"):
                        merged["keywords"] = prev["keywords"]
                    existing_intents[ci["name"]] = merged

            if clean_intents or existing_intents:
                try:
                    from shared.tenancy.defaults import (
                        ensure_company_info_page_intents,
                        strip_company_info_page_intents,
                    )
                    intent_list = list(existing_intents.values())
                    if vertical == "it_software":
                        draft["intents"] = ensure_company_info_page_intents(intent_list)
                    else:
                        draft["intents"] = strip_company_info_page_intents(intent_list)
                except Exception:
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
        """Extract + bifurcate a single already-saved upload for this tenant."""
        doc_data = self.extract_file_content(filename, content)
        bifurcation = self.bifurcate_with_llm([doc_data])
        # Guarantee vertical-aware menu when LLM/heuristics left it thin
        if len(bifurcation.get("menu_items") or []) < 3:
            bifurcation["menu_items"] = self.extract_menu_section(
                {"text": "", "tables": []},
                vertical=bifurcation.get("vertical") or "generic",
            )
        result = self.apply_bifurcation(
            bifurcation=bifurcation,
            raw_files=[doc_data],
            auto_publish=auto_publish,
            careful_brand_merge=careful_brand_merge,
            source_file=filename,
        )
        result["files_processed"] = [filename]
        result["tenant_id"] = self.tenant_id
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
