"""Intelligent Document Auto-Bifurcation & Auto-Configuration Engine.

Accepts multi-format uploaded documents (PDF, DOCX, XLSX, CSV, TXT, MD), parses their
contents section-by-section, and semantically bifurcates the information into:
  1. Brand & Profile Data (Name, Bot persona, Tagline, Tone, Contact, Hours, Vertical)
  2. WhatsApp Interactive Navigation Menu (Buttons/Drawers <= 24 title / 72 desc chars)
  3. Conversational Intents & Flow Triggers (Keywords, Utterances, Action Mappings)
  4. Offerings & Catalog Data (Products, Services, Packages, Properties with Pricing & Attrs)
  5. Knowledge Base & FAQ Documents (Markdown articles, Chunks, Vector RAG Embeddings)
  6. Persona & Guardrails (Never-do list, escalation triggers, greeting)

Supports:
  - Staging Mode (stage_files): Extracts & parses into an editable preview draft for human review.
  - Publish Mode (publish_staged_draft): Automatically configures and publishes all components
    into tenant configuration, database tables (products, chunks), client pack (clients/<tenant_id>/config.json),
    and FAISS vector index.
  - Prioritized Local Ollama LLM with intelligent deterministic fallback.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import os
import re
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
)
from shared.tenancy import cache as tenancy_cache
from shared.tenancy import defaults as tenancy_defaults
from shared.tenancy import loader as tenancy_loader
from shared.tenancy import schemas as tenancy_schemas
from shared.tenancy import store as tenancy_store

logger = logging.getLogger("auto_bifurcator")

VALID_VERTICALS = set(tenancy_schemas.VERTICALS)


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
    # 1. Multi-Format Text & Table Extraction with Document Order
    # ──────────────────────────────────────────────────────────────────────────

    def extract_file_content(self, filename: str, content: bytes) -> Dict[str, Any]:
        """Extract ordered text, paragraphs, and tables from PDF, DOCX, XLSX, CSV, TXT."""
        ext = Path(filename).suffix.lower()
        extracted_text = ""
        tables_found: List[List[List[str]]] = []
        ordered_elements: List[Dict[str, Any]] = []

        try:
            if ext == ".pdf":
                doc = fitz.open(stream=content, filetype="pdf")
                pages_text = []
                for pno in range(len(doc)):
                    page = doc[pno]
                    txt = page.get_text("text") or ""
                    if txt.strip():
                        pages_text.append(f"--- Page {pno + 1} ---\n{txt}")
                    # Extract structured tables
                    try:
                        tabs = page.find_tables()
                        for tab in tabs:
                            extracted_tbl = tab.extract()
                            if extracted_tbl and len(extracted_tbl) > 1:
                                clean_tbl = [[str(c or "").strip().replace("\n", " ") for c in r] for r in extracted_tbl]
                                tables_found.append(clean_tbl)
                                ordered_elements.append({"type": "table", "rows": clean_tbl})
                    except Exception as tab_err:
                        logger.debug("PDF find_tables page %d skipped: %s", pno, tab_err)
                extracted_text = "\n\n".join(pages_text)

            elif ext in (".docx", ".doc"):
                doc_file = io.BytesIO(content)
                doc = Document(doc_file)
                paragraphs = []
                table_texts = []

                # Extract in document order
                for child in doc.element.body:
                    tag = child.tag.split("}")[-1]
                    if tag == "p":
                        text = child.text or ""
                        # Get full paragraph text from w:t elements
                        t_elems = child.xpath(".//w:t")
                        if t_elems:
                            text = "".join(t.text for t in t_elems if t.text)
                        text = text.strip()
                        if text:
                            paragraphs.append(text)
                            ordered_elements.append({"type": "paragraph", "text": text})
                    elif tag == "tbl":
                        # Table element
                        t_rows = []
                        for tr in child.xpath(".//w:tr"):
                            row_cells = []
                            for tc in tr.xpath(".//w:tc"):
                                cell_text = "".join(t.text for t in tc.xpath(".//w:t") if t.text).strip()
                                row_cells.append(cell_text)
                            if any(row_cells):
                                t_rows.append(row_cells)
                        if t_rows:
                            tables_found.append(t_rows)
                            ordered_elements.append({"type": "table", "rows": t_rows})
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
                            rows.append(cells)
                    if rows:
                        tables_found.append(rows)
                        ordered_elements.append({"type": "table", "sheet": sheetname, "rows": rows})
                        sheet_texts.append(f"=== Sheet: {sheetname} ===\n" + "\n".join(" | ".join(r) for r in rows))
                extracted_text = "\n\n".join(sheet_texts)

            elif ext == ".csv":
                text_stream = io.StringIO(content.decode("utf-8", errors="ignore"))
                reader = csv.reader(text_stream)
                rows = [row for row in reader if any(row)]
                if rows:
                    tables_found.append(rows)
                    ordered_elements.append({"type": "table", "rows": rows})
                extracted_text = "\n".join(" | ".join(r) for r in rows)

            else:
                # Plain Text or Markdown fallback
                try:
                    extracted_text = content.decode("utf-8")
                except UnicodeDecodeError:
                    extracted_text = content.decode("latin-1", errors="ignore")

        except Exception as exc:
            logger.error("Failed extracting %s: %s", filename, exc, exc_info=True)
            extracted_text = f"[Text extraction error: {exc}]"

        extracted_text = _clean_text(extracted_text)
        return {
            "filename": filename,
            "ext": ext,
            "size": len(content),
            "char_count": len(extracted_text),
            "text": extracted_text,
            "tables": tables_found,
            "ordered_elements": ordered_elements,
            "has_tables": len(tables_found) > 0,
        }

    # ──────────────────────────────────────────────────────────────────────────
    # 2. Section Partitioning & Specialized Extractors
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
                elif (
                    any(k in first_row_str for k in ("question", "frequently asked", "official answer", "verified answer"))
                    or str(tbl[0][0]).strip().endswith("?")
                    or (len(tbl[0]) == 3 and any(str(r[0]).strip().endswith("?") for r in tbl))
                ):
                    sections["faqs"]["tables"].append(tbl)
                elif any(k in first_row_str for k in ("guardrail", "tone & style", "never-do", "bot behavior", "persona")):
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
    # 3. LLM Semantic Call (Ollama First, with Fallback)
    # ──────────────────────────────────────────────────────────────────────────

    def _call_llm_json(self, system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
        """Call LLM with JSON output, prioritizing local Ollama server."""
        import requests

        # 1. Try Local Ollama (Priority 1)
        ollama_url = os.getenv("OLLAMA_API_URL") or "http://localhost:11434/api/chat"
        ollama_model = os.getenv("OLLAMA_MODEL") or "qwen2.5:7b"
        try:
            payload = {
                "model": ollama_model,
                "messages": [
                    {"role": "system", "content": system_prompt + "\nOUTPUT ONLY STRICT RAW JSON."},
                    {"role": "user", "content": user_prompt},
                ],
                "format": "json",
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "num_ctx": int(os.getenv("OLLAMA_NUM_CTX", 8192)),
                },
            }
            resp = requests.post(ollama_url, json=payload, timeout=20)
            if resp.status_code == 200:
                content = resp.json().get("message", {}).get("content", "")
                parsed = self._extract_json_block(content)
                if parsed:
                    logger.info("OLLAMA_BIFURCATION_SUCCESS | model=%s", ollama_model)
                    return parsed
        except Exception as e:
            logger.debug("Local Ollama not reachable or timed out: %s", e)

        # 2. Try Groq (Priority 2)
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            try:
                headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
                for model in ("openai/gpt-oss-120b", "openai/gpt-oss-20b"):
                    payload = {
                        "model": model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "response_format": {"type": "json_object"},
                        "temperature": 0.2,
                        "max_tokens": 4096,
                    }
                    resp = requests.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=30,
                    )
                    if resp.status_code == 200:
                        content = resp.json()["choices"][0]["message"]["content"]
                        parsed = self._extract_json_block(content)
                        if parsed:
                            logger.info("GROQ_BIFURCATION_SUCCESS | model=%s", model)
                            return parsed
            except Exception as e:
                logger.warning("Groq bifurcation failed: %s", e)

        # 3. Try Mistral (Priority 3)
        mistral_key = os.getenv("MISTRAL_API_KEY") or os.getenv("MISTRAL_API_BACKUP")
        if mistral_key:
            try:
                headers = {"Authorization": f"Bearer {mistral_key}", "Content-Type": "application/json"}
                payload = {
                    "model": os.getenv("MISTRAL_MODEL", "open-mistral-7b"),
                    "messages": [
                        {"role": "system", "content": system_prompt + "\nOUTPUT ONLY RAW JSON."},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.2,
                    "max_tokens": 4096,
                }
                resp = requests.post(
                    "https://api.mistral.ai/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30,
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

        first = text.find("{")
        last = text.rfind("}")
        if first != -1 and last != -1 and last > first:
            try:
                return json.loads(text[first : last + 1])
            except Exception:
                pass

        return None

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
            v_defaults = tenancy_defaults.get_vertical_defaults(vertical) or {}
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
            if any(h in headers for h in ("button title", "parameter", "verified answer")):
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
                    attrs = {k: v for k, v in row_dict.items() if k not in ("property name", "product name", "service / offering")}

                offerings.append({
                    "name": name,
                    "category": prop_type,
                    "price": price,
                    "short_description": short_desc,
                    "description": full_desc,
                    "unit": "unit",
                    "attrs": attrs,
                })

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
        """Extract FAQs and compose structured Markdown knowledge articles."""
        tables = sec_data.get("tables", [])
        text = sec_data.get("text", "")
        faqs: List[Dict[str, Any]] = []

        for tbl in tables:
            if len(tbl) >= 1 and len(tbl[0]) >= 2:
                # If first row looks like a question, include it
                is_q = str(tbl[0][0]).strip().endswith("?") or "?" in str(tbl[0][0])
                start_idx = 0 if is_q else 1
                for row in tbl[start_idx:]:
                    if not row or not row[0].strip():
                        continue
                    q = row[0].strip()
                    if q.startswith("[") or q.lower().startswith("add question") or q.lower() == "customer question":
                        continue
                    a = row[1].strip() if len(row) > 1 else ""
                    cat = row[2].strip() if len(row) > 2 else "General"
                    if q and a:
                        faqs.append({"question": q, "answer": a, "category": cat})

        # Fallback regex search for Q: ... A: ... in text
        if not faqs and text:
            qa_matches = re.findall(r"(?:Q|Question):\s*(.+?)\n+(?:A|Answer):\s*(.+?)(?=\n+(?:Q|Question):|\Z)", text, re.DOTALL | re.IGNORECASE)
            for q, a in qa_matches:
                faqs.append({"question": q.strip(), "answer": a.strip(), "category": "General"})

        # Compose Knowledge Base Articles
        articles: List[Dict[str, Any]] = []

        # Article 1: Company Profile
        articles.append({
            "title": f"About {brand_name}",
            "category": "Company",
            "markdown_content": f"# About {brand_name}\n\nWelcome to {brand_name}. We provide industry-leading {vertical.replace('_', ' ')} solutions.\n\nOur team is committed to transparency, excellence, and customer satisfaction.",
        })

        # Article 2: FAQs Guide
        if faqs:
            faq_md_lines = [f"# Frequently Asked Questions — {brand_name}\n"]
            for f in faqs:
                faq_md_lines.append(f"### Q: {f['question']}\n**A:** {f['answer']}\n*(Category: {f['category']})*\n")
            articles.append({
                "title": f"Frequently Asked Questions & Customer Support",
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
    # 6. Apply & Publish Bifurcated Configuration
    # ──────────────────────────────────────────────────────────────────────────

    def apply_bifurcation(
        self,
        bifurcation: Dict[str, Any],
        raw_files: List[Dict[str, Any]],
        auto_publish: bool = True,
    ) -> Dict[str, Any]:
        """Apply parsed bifurcation payload to database, client pack, and FAISS index."""
        tenant_id = self.tenant_id
        vertical = bifurcation.get("vertical", "generic")
        if vertical not in VALID_VERTICALS:
            vertical = "generic"

        summary = {
            "tenant_id": tenant_id,
            "vertical": vertical,
            "brand": bifurcation.get("brand", {}).get("name", tenant_id),
            "offerings_created": 0,
            "offerings_sample": [],
            "menu_buttons_count": 0,
            "intents_created": 0,
            "kb_chunks_indexed": 0,
            "published": auto_publish,
            "version": None,
        }

        clean_brand = bifurcation.get("brand", {})
        menu_buttons = bifurcation.get("menu_items", [])
        summary["menu_buttons_count"] = len(menu_buttons)

        # Update Tenant Profile Draft in Database
        draft = tenancy_store.get_draft(tenant_id) or {}
        draft["tenant_id"] = tenant_id
        draft["vertical"] = vertical
        draft["display_name"] = clean_brand.get("name", tenant_id)
        draft["brand"] = clean_brand
        draft["menu"] = {
            "key": "kb_main",
            "header": clean_brand.get("name", tenant_id),
            "body": f"Welcome to {clean_brand.get('name', tenant_id)}! How can we assist you today?",
            "footer": "Select an option or type your query directly",
            "button_text": "Select Option",
            "buttons": menu_buttons,
        }

        if "business_hours" in bifurcation:
            draft["business_hours"] = bifurcation["business_hours"]

        # Ensure flows exist
        if "flows" not in draft or not draft["flows"]:
            draft["flows"] = [
                {"name": "book_callback", "success_message": f"Thank you! Your request has been scheduled with {clean_brand.get('bot_name', 'Advisor')}."},
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
                    logger.warning("Could not publish version directly: %s", pub_exc)

        # Sync client config file clients/<tenant_id>/config.json
        try:
            from shared.tenancy.paths import CLIENTS_DIR
            client_dir_path = CLIENTS_DIR / tenant_id
            client_dir_path.mkdir(parents=True, exist_ok=True)
            cfg_path = client_dir_path / "config.json"
            if not cfg_path.exists():
                with open(cfg_path, "w", encoding="utf-8") as fh:
                    json.dump(draft, fh, ensure_ascii=False, indent=2)
            tenancy_loader.write_client_config_file(tenant_id, draft)
        except Exception as file_exc:
            logger.warning("Could not sync client config file: %s", file_exc)

        # Insert Offerings into Catalog (products table)
        offerings_raw = bifurcation.get("offerings", [])
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
            slug = f"{tenant_id}-{_slugify(name)}"

            if name.lower() in existing_products:
                prod_id = existing_products[name.lower()]["id"]
                update_product(
                    prod_id,
                    tenant_id=tenant_id,
                    price=price,
                    description=desc,
                    short_description=short_desc,
                    category=cat,
                    attrs_json=attrs,
                )
            else:
                try:
                    save_product(
                        name=name,
                        slug=slug,
                        category=cat,
                        price=price,
                        short_description=short_desc,
                        description=desc,
                        attrs_json=attrs,
                        tenant_id=tenant_id,
                        actor=self.actor,
                    )
                    inserted_count += 1
                    if len(summary["offerings_sample"]) < 5:
                        summary["offerings_sample"].append(name)
                except Exception as p_err:
                    logger.debug("Product save fallback for %s: %s", slug, p_err)
                    # Try with unique timestamp suffix
                    try:
                        import time
                        save_product(
                            name=name,
                            slug=f"{slug}-{int(time.time())}",
                            category=cat,
                            price=price,
                            short_description=short_desc,
                            description=desc,
                            attrs_json=attrs,
                            tenant_id=tenant_id,
                            actor=self.actor,
                        )
                        inserted_count += 1
                    except Exception:
                        pass

        summary["offerings_created"] = inserted_count

        # Write Knowledge Base Markdown Files & Build Vector Embeddings
        from shared.tenancy.paths import CLIENTS_DIR
        knowledge_dir = CLIENTS_DIR / tenant_id / "knowledge"
        knowledge_dir.mkdir(parents=True, exist_ok=True)

        articles = bifurcation.get("knowledge_articles", [])
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
                    {"content": ch, "source_file": "auto_bifurcated_docs.md"}
                    for ch in all_chunks_to_index
                ]
                save_knowledge_base_chunks(
                    chunks=formatted_chunks,
                    source_file="auto_bifurcated_docs.md",
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

        # Audit Event
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
                        "brand": clean_brand.get("name"),
                        "offerings_count": inserted_count,
                        "menu_buttons_count": len(menu_buttons),
                        "chunks_count": summary["kb_chunks_indexed"],
                    },
                )
        except Exception:
            pass

        return summary

    # ──────────────────────────────────────────────────────────────────────────
    # 7. High-Level Coordinator
    # ──────────────────────────────────────────────────────────────────────────

    def process_files(
        self,
        files_data: List[Dict[str, Any]],
        auto_publish: bool = True,
    ) -> Dict[str, Any]:
        """End-to-end extraction, section-by-section bifurcation, and optional auto-publish."""
        extracted_docs = []
        upload_dir = os.path.join("backend", "uploaded_files", "kb")
        os.makedirs(upload_dir, exist_ok=True)

        for f in files_data:
            filename = f.get("filename") or "document.pdf"
            content = f.get("content") or b""
            if isinstance(content, str):
                import base64
                content = base64.b64decode(content)

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

            doc_data = self.extract_file_content(filename, content)
            extracted_docs.append(doc_data)

        # Run Section-by-Section Targeted Bifurcation
        staged = self.stage_files(files_data)

        if not auto_publish:
            return staged

        # Apply bifurcation across all components
        result_summary = self.apply_bifurcation(
            bifurcation=staged,
            raw_files=extracted_docs,
            auto_publish=True,
        )
        result_summary["files_processed"] = [d["filename"] for d in extracted_docs]
        return result_summary
