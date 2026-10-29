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
import string
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import fitz  # PyMuPDF
from docx import Document
import openpyxl

from database import (
    delete_product,
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
from shared.tenancy import loader as tenancy_loader
from shared.tenancy import schemas as tenancy_schemas
from shared.tenancy import store as tenancy_store

logger = logging.getLogger("auto_bifurcator")

# Target vertical options supported by tenancy schema
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


def _assign_button_icon(title: str, action: str = "", vertical: str = "") -> str:
    """Derive a context-aware emoji icon for a WhatsApp menu button based on vertical and content."""
    t = (title or "").lower().strip()
    a = (action or "").lower().strip()
    v = (vertical or "").lower().strip()

    # Generic action matches
    if any(k in t for k in ["callback", "call", "advisor", "expert", "talk to", "contact", "speak", "phone", "helpline", "human"]):
        return "📞"
    if any(k in t for k in ["support", "help", "ticket", "complaint", "issue", "care"]):
        return "🆘" if ("urgent" in t or "sos" in t) else "💬"
    if any(k in t for k in ["quote", "estimate", "pricing", "plans", "cost", "fee", "rate"]):
        return "💰"
    if any(k in t for k in ["brochure", "download", "pdf", "document", "spec", "terms", "rules"]):
        return "📄"
    if any(k in t for k in ["visit", "schedule", "book", "appointment", "calendar"]):
        return "📅"

    # Vertical-specific matches
    if "estate" in v or "property" in v:
        if any(k in t for k in ["villa", "plot", "land"]):
            return "🏡"
        if any(k in t for k in ["apartment", "flat", "residence", "commercial", "project", "ongoing", "property", "properties", "explore", "offerings"]):
            return "🏢"
        if any(k in t for k in ["rera", "legal", "sanction", "approval"]):
            return "⚖️"
        if any(k in t for k in ["loan", "emi", "bank", "payment"]):
            return "💳"
        return "🏢"

    if "bank" in v or "finance" in v:
        if any(k in t for k in ["account", "savings", "current", "deposit", "fd", "rd"]):
            return "🏦"
        if any(k in t for k in ["loan", "credit", "mortgage", "emi", "borrow"]):
            return "💳"
        if any(k in t for k in ["invest", "mutual fund", "stock", "wealth", "portfolio"]):
            return "📈"
        if any(k in t for k in ["fraud", "security", "block", "alert"]):
            return "🔒"
        return "🏦"

    if "travel" in v or "tour" in v:
        if any(k in t for k in ["destination", "place", "explore", "city"]):
            return "🗺️"
        if any(k in t for k in ["package", "holiday", "tour", "trip", "vacation"]):
            return "🌴"
        if any(k in t for k in ["itinerary", "custom", "plan"]):
            return "🧭"
        if any(k in t for k in ["visa", "passport", "immigration"]):
            return "🛂"
        if any(k in t for k in ["flight", "hotel", "cruise", "ticket"]):
            return "✈️"
        if any(k in t for k in ["policy", "cancellation", "refund"]):
            return "📋"
        return "🌴"

    if "software" in v or "it" in v:
        if any(k in t for k in ["service", "offering", "solution"]):
            return "💻"
        if any(k in t for k in ["tech", "stack", "tool", "framework"]):
            return "⚙️"
        if any(k in t for k in ["project", "portfolio", "case study", "client"]):
            return "🚀"
        if any(k in t for k in ["career", "job", "hiring", "role"]):
            return "💼"
        if any(k in t for k in ["benefit", "why", "choose"]):
            return "🌟"
        return "💻"

    if "ecom" in v or "retail" in v:
        if any(k in t for k in ["deal", "offer", "discount", "sale"]):
            return "🏷️"
        if any(k in t for k in ["cart", "checkout", "buy"]):
            return "🛒"
        if any(k in t for k in ["track", "order", "delivery", "shipping"]):
            return "📦"
        return "🛍️"

    if "health" in v or "clinic" in v:
        if any(k in t for k in ["doctor", "specialist", "physician"]):
            return "🩺"
        if any(k in t for k in ["test", "lab", "diagnostic"]):
            return "🔬"
        if any(k in t for k in ["medicine", "pharmacy", "drug"]):
            return "💊"
        return "🏥"

    return "✨"


def _is_offering_relevant_to_vertical(name: str, category: str = "", vertical: str = "generic") -> bool:
    """Validate that an offering is strictly relevant to the tenant's subject / vertical and not template noise.

    Prevents:
    1. Cross-vertical contamination (e.g. software/IT offerings appearing on a real estate tenant).
    2. Instruction text / template banner lines (e.g. 'paste a public https photo link per item').
    3. Truncated or noisy labels starting with punctuation or table dividers.
    """
    n = (name or "").strip().lower()
    c = (category or "").strip().lower()
    v = (vertical or "generic").strip().lower()

    if not n or len(n) < 3:
        return False

    # Discard table headers, instruction text, and parsing noise
    instruction_noise = [
        "paste a public", "stored on the offering", "image url",
        "service / offering", "service/offering", "project / property", "project/property",
        "scope & deliverables", "typical timeline", "tech stack", "model & tools",
        "configuration & sizes", "amenities & usps", "location / possession",
        "starting price", "confidential", "fill & upload", "customer question",
        "official verified answer", "knowledge article title", "category article content"
    ]
    if any(noise in n for noise in instruction_noise):
        return False
    if n.startswith(":") or n.startswith("·") or n.startswith("-") or n.startswith("*") or n.startswith("/"):
        return False

    # Real Estate subject guardrail
    if "estate" in v or "property" in v:
        banned_real_estate = [
            "full-stack", "mobile app", "ai chatbot", "cloud & dedicated",
            "cloud and dedicated", "devops", "software development", "custom software",
            "web app", "engineering pod", "react", "python", "flutter", "aws",
            "docker", "kubernetes", "fastapi", "next.js", "chikki", "jaggery",
            "peanut", "cart", "checkout", "return policy", "t-shirt", "shirt",
            "shoe", "flight booking", "holiday package", "savings account", "fixed deposit",
            "credit card", "air cargo", "ocean freight", "customs brokerage"
        ]
        if any(b in n or b in c for b in banned_real_estate):
            return False

    # IT / Software subject guardrail
    if "software" in v or "it" in v:
        banned_it = [
            "bhk", "villa plot", "sq.ft", "carpet area", "gated villa",
            "apartment for sale", "chikki", "jaggery", "flight booking",
            "savings account", "fixed deposit", "credit card", "home loan",
            "interest rate", "deposits", "scheme", "minimum balance",
            "tour package", "desert circuit", "backwaters", "honeymoon",
            "air cargo", "ocean freight", "customs brokerage", "warehousing",
            "plots", "apartments", "residence", "commercial office"
        ]
        if any(b in n or b in c for b in banned_it):
            return False

    # Banking / Finance subject guardrail
    if "bank" in v or "finance" in v:
        banned_banking = [
            "bhk", "villa plot", "sq.ft", "carpet area", "gated villa",
            "full-stack", "mobile app", "software development", "web app",
            "flight booking", "holiday package", "tour package", "cargo", "freight"
        ]
        if any(b in n or b in c for b in banned_banking):
            return False

    # Tours & Travel subject guardrail
    if "travel" in v or "tour" in v:
        banned_travel = [
            "bhk", "villa plot", "sq.ft", "carpet area", "gated villa",
            "full-stack", "mobile app", "software development",
            "savings account", "fixed deposit", "credit card", "home loan"
        ]
        if any(b in n or b in c for b in banned_travel):
            return False

    # Healthcare subject guardrail
    if "health" in v or "clinic" in v:
        banned_health = [
            "full-stack", "mobile app", "villa plot", "bhk", "apartment for sale",
            "savings account", "fixed deposit", "credit card", "home loan"
        ]
        if any(b in n or b in c for b in banned_health):
            return False

    return True


def _canonicalize_and_deduplicate_intents(
    raw_intents: List[Dict[str, Any]],
    vertical: str = "generic",
    menu_buttons: List[Dict[str, Any]] = None,
    max_intents: int = 7,
) -> List[Dict[str, Any]]:
    """Deduplicate, canonicalize, and limit intents to ONLY project-relevant topics.

    1. Discard template artifacts, generic keywords, or irrelevant cross-vertical topics.
    2. Cluster synonyms (e.g. 4 pricing variations -> 1 'pricing_plan', 3 site visit variations -> 1 'site_visit').
    3. Merge examples, keywords, and answers across duplicate topics.
    4. Ensure alignment with active menu buttons.
    5. Cap active intents at 4-7 strictly relevant to the project.
    """
    v = (vertical or "generic").lower()
    menu_buttons = menu_buttons or []

    junk_slugs = {
        "populates", "page", "page-name", "intent", "parameter", "section",
        "sample", "test", "note", "tip", "instruction", "template", "default",
        "overview", "undefined", "custom-intent", "item", "welcome", "greeting"
    }

    # Cross-vertical filters: if tenant is real estate, filter out IT/tech/e-com artifacts
    real_estate_banned = {
        "technologies", "careers", "benefits", "software", "devops", "coding",
        "web-apps", "products-schemes", "cart", "track-order", "checkout"
    }

    canonical_topics = [
        {
            "canonical": "site_visit" if ("estate" in v or "property" in v) else "book_appointment",
            "matches": ["site-visit", "site_visit", "visit", "tour", "appointment", "schedule-tour", "book-visit"],
            "default_flow": "book_callback",
            "default_examples": ["I want to schedule a site visit", "Can I view the property this weekend?", "Book a guided tour"],
            "default_keywords": ["site visit", "visit", "tour", "schedule", "appointment"],
        },
        {
            "canonical": "pricing_plan",
            "matches": ["pricing", "payment-plan", "price-quote", "quote", "cost", "cost-sheet", "booking-advance", "advance-payment", "rate", "emi", "payment"],
            "default_flow": "get_quote",
            "default_examples": ["What is the price?", "Send me the cost sheet", "What are the payment plans and EMI options?"],
            "default_keywords": ["price", "cost", "pricing", "payment plan", "quote", "rates"],
        },
        {
            "canonical": "brochure_request",
            "matches": ["brochure", "catalogue", "catalog", "floor-plan", "master-plan", "layout", "specifications", "spec", "download-brochure"],
            "default_flow": None,
            "default_examples": ["Send me the project brochure", "Download floor plans", "Can I see the master layout PDF?"],
            "default_keywords": ["brochure", "floor plan", "master plan", "pdf", "layout", "specifications"],
        },
        {
            "canonical": "property_listings" if ("estate" in v or "property" in v) else "explore_offerings",
            "matches": ["property", "properties", "flat", "flats", "apartment", "apartments", "villa", "villas", "unit", "units", "explore-offering", "offering", "offerings", "residence", "penthouse", "commercial"],
            "default_flow": None,
            "default_examples": ["Show me available properties", "What apartments do you have?", "Tell me about luxury villas"],
            "default_keywords": ["property", "flat", "apartment", "villa", "bhk", "residence", "commercial"],
        },
        {
            "canonical": "project_details",
            "matches": ["project-detail", "view-project", "location", "highlights", "connectivity", "specifications", "project"],
            "default_flow": None,
            "default_examples": ["Where is the project located?", "What are the key connectivity highlights?", "When is the possession date?"],
            "default_keywords": ["project", "location", "connectivity", "possession", "highlights"],
        },
        {
            "canonical": "rera_legal",
            "matches": ["rera", "legal", "sanction", "approval", "approvals", "clear-title", "title", "stamp-duty", "registration", "certification"],
            "default_flow": None,
            "default_examples": ["Is the project RERA approved?", "What is the RERA registration number?", "Are all legal clearances in place?"],
            "default_keywords": ["rera", "legal", "approval", "registration", "sanction", "clear title"],
        },
        {
            "canonical": "amenities",
            "matches": ["amenities", "amenity", "facility", "facilities", "clubhouse", "swimming-pool", "gym", "sports"],
            "default_flow": None,
            "default_examples": ["What amenities are provided?", "Is there a clubhouse and swimming pool?", "Gym and sports facilities"],
            "default_keywords": ["amenities", "clubhouse", "pool", "gym", "facilities", "sports", "park"],
        },
        {
            "canonical": "home_loans",
            "matches": ["home-loan", "loan", "loans", "bank-loan", "emi", "mortgage", "financing"],
            "default_flow": None,
            "default_examples": ["Do you provide home loan assistance?", "Which banks have approved this project?", "What are the loan EMI options?"],
            "default_keywords": ["home loan", "loan", "bank", "emi", "interest rate", "financing"],
        },
        {
            "canonical": "nri_desk",
            "matches": ["nri", "overseas", "international-buyer", "nri-purchase"],
            "default_flow": None,
            "default_examples": ["Can NRIs purchase property here?", "What documents are required for NRI purchase?", "NRI investment guidance"],
            "default_keywords": ["nri", "overseas", "international", "purchase", "repatriation"],
        },
        {
            "canonical": "possession_handover",
            "matches": ["possession", "handover", "handover-kit", "keys", "upgrade-unit"],
            "default_flow": None,
            "default_examples": ["When is the possession date?", "What is included in the handover kit?", "Key handover process"],
            "default_keywords": ["possession", "handover", "keys", "inspection"],
        },
        {
            "canonical": "customer_support",
            "matches": ["support", "complaint", "ticket", "human", "advisor", "contact", "agent", "post-sales", "help"],
            "default_flow": "raise_ticket",
            "default_examples": ["I need customer support", "Raise a complaint", "Speak to a human advisor"],
            "default_keywords": ["support", "help", "ticket", "complaint", "human", "contact", "advisor"],
        },
    ]

    canonical_map: Dict[str, Dict[str, Any]] = {}

    for raw in raw_intents:
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("name") or "").strip()
        slug = _slugify(name)
        if not slug or slug in junk_slugs or len(slug) < 3:
            continue
        if ("estate" in v or "property" in v) and slug in real_estate_banned:
            continue

        # Find matching canonical topic
        matched_canonical = None
        for topic in canonical_topics:
            if any(m in slug for m in topic["matches"]) or any(m in name.lower() for m in topic["matches"]):
                matched_canonical = topic
                break

        canonical_name = matched_canonical["canonical"] if matched_canonical else slug
        target_flow = raw.get("flow") or (matched_canonical.get("default_flow") if matched_canonical else None)

        examples = [ex.strip() for ex in raw.get("examples", []) if isinstance(ex, str) and ex.strip()]
        keywords = [kw.strip().lower() for kw in raw.get("keywords", []) if isinstance(kw, str) and kw.strip()]
        answer = raw.get("answer")

        if canonical_name in canonical_map:
            # Merge with existing canonical intent
            entry = canonical_map[canonical_name]
            combined_ex = list(dict.fromkeys(entry.get("examples", []) + examples))
            entry["examples"] = combined_ex[:5]
            combined_kw = list(dict.fromkeys(entry.get("keywords", []) + keywords))
            entry["keywords"] = combined_kw[:10]
            if target_flow and not entry.get("flow"):
                entry["flow"] = target_flow
            if answer and (not entry.get("answer") or len(str(answer)) > len(str(entry.get("answer")))):
                entry["answer"] = answer
        else:
            if matched_canonical and not examples:
                examples = list(matched_canonical.get("default_examples", []))
            if matched_canonical and not keywords:
                keywords = list(matched_canonical.get("default_keywords", []))
            entry = {
                "name": canonical_name,
                "examples": examples[:5],
                "keywords": keywords[:10],
                "flow": target_flow,
                "enabled": True,
            }
            if answer:
                entry["answer"] = answer
            canonical_map[canonical_name] = entry

    # Ensure intents for active menu buttons exist
    for btn in menu_buttons:
        if not isinstance(btn, dict) or btn.get("__remove__"):
            continue
        btn_flow = btn.get("flow")
        btn_action = btn.get("action")
        btn_title = (btn.get("title") or "").lower()

        target_name = None
        if btn_flow == "book_callback" or "visit" in btn_title or "consult" in btn_title:
            target_name = "site_visit" if ("estate" in v or "property" in v) else "book_appointment"
        elif btn_flow == "get_quote" or "price" in btn_title or "quote" in btn_title or "plan" in btn_title:
            target_name = "pricing_plan"
        elif btn_flow == "raise_ticket" or "support" in btn_title or "help" in btn_title:
            target_name = "customer_support"
        elif "brochure" in btn_title:
            target_name = "brochure_request"
        elif "properties" in btn_title or "explore" in btn_title or "projects" in btn_title:
            target_name = "property_listings" if ("estate" in v or "property" in v) else "explore_offerings"

        if target_name and target_name not in canonical_map:
            # Find default template for this canonical topic
            for topic in canonical_topics:
                if topic["canonical"] == target_name:
                    canonical_map[target_name] = {
                        "name": target_name,
                        "examples": list(topic.get("default_examples", []))[:5],
                        "keywords": list(topic.get("default_keywords", []))[:10],
                        "flow": topic.get("default_flow"),
                        "enabled": True,
                    }
                    break

    # Prioritize and cap intents to max_intents
    def _intent_priority(item: Dict[str, Any]) -> int:
        score = 0
        if item.get("flow"):
            score += 10
        if item.get("answer"):
            score += 5
        if item["name"] in {"property_listings", "site_visit", "pricing_plan", "explore_offerings", "customer_support"}:
            score += 8
        return score

    sorted_intents = sorted(canonical_map.values(), key=_intent_priority, reverse=True)
    return sorted_intents[:max_intents]


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
                    if len(txt.strip()) < 50:
                        try:
                            from backend.extract import ocr_page
                            ocr_txt = ocr_page(page)
                            if ocr_txt and ocr_txt.strip():
                                txt = ocr_txt
                        except Exception as ocr_err:
                            logger.debug("PDF OCR page %d fallback error: %s", pno + 1, ocr_err)
                    if txt.strip():
                        pages_text.append(f"--- Page {pno + 1} ---\n{txt}")
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
    // STRICTLY 4 to 6 top customer conversational intents RELEVANT ONLY TO THIS SPECIFIC PROJECT / COLLATERAL.
    // DO NOT invent generic intents or add cross-vertical topics (e.g. no IT/software topics for real estate).
    // Every intent must have a clear customer purpose directly related to the company's offerings and documentation.
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
    // All individual properties, units, floor plans, services, or catalog products
    {{
      "name": "Property, Project, Unit, or Service Name (e.g. '3 BHK Luxury Apartment', 'Skyline Villa Plot', 'Full-Stack Web App')",
      "category": "Segment or Type (e.g. 'Residential Apartments', 'Luxury Villas', 'Commercial', 'Custom Software')",
      "price": "Starting price or cost sheet rate (e.g. 'Starting ₹85 Lakhs', '₹1.45 Cr', 'Starting ₹4,00,000')",
      "short_description": "Punchy 1-sentence summary of configuration and size",
      "description": "Full specifications, super built-up area, carpet area, possession date, tech stack, and amenities",
      "image_url": "CRITICAL: Direct public HTTPS photo or image URL from the document (e.g. https://images.unsplash.com/... or public image URL if present, else empty string)",
      "unit": "flat / villa / unit / package / month / sqft",
      "attrs": {{
        "specifications": "BHK, dimensions, sq.ft, floor or tech stack",
        "timeline": "Possession timeline or delivery timeline",
        "highlights": "Key bullet points, amenities, or deliverables",
        "image_url": "Direct image URL"
      }}
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
1. Extract ALL tangible properties/projects/services/products into the 'offerings' array.
2. CRITICAL FOR IMAGE URLS: If any property, project, offering, or catalog item in the document has an image URL or photo link (such as Unsplash https://images.unsplash.com/... or public image links), you MUST extract the exact URL into the 'image_url' field. Never omit or invent URLs; copy them verbatim.
3. Ensure 'menu_items' titles are UNDER 24 CHARACTERS (strictly enforced by WhatsApp API).
4. If phone or email is missing in the text, provide a sensible default based on the tenant name (e.g. 'support@{self.tenant_id}.com' and '+91 9800000000').
5. Respond ONLY with the JSON object. Do not enclose in backticks or markdown if possible.
"""

        # Check for structured onboarding guide template first
        template_data = self._parse_onboarding_guide(full_corpus)
        if template_data and template_data.get("brand") and template_data.get("offerings"):
            logger.info("ONBOARDING_GUIDE_TEMPLATE_DETECTED | tenant=%s | offerings=%d", self.tenant_id, len(template_data.get("offerings", [])))
            return template_data

        user_prompt = f"Please bifurcate and configure the chatbot system based on the following uploaded client collateral:\n\n{full_corpus}"

        response_json = self._call_llm_json(system_prompt, user_prompt)
        if not response_json:
            logger.warning("LLM bifurcation returned empty or invalid JSON; applying heuristic fallback")
            response_json = self._heuristic_bifurcation(doc_summaries)

        if response_json and response_json.get("offerings"):
            self._enrich_offerings_with_images(response_json["offerings"], full_corpus)

        return response_json

    def _call_llm_json(self, system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
        """Call Groq (openai/gpt-oss-120b) or Mistral with JSON output."""
        # 1. Try Groq
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            try:
                import requests
                headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
                # Try gpt-oss-120b, then gpt-oss-20b
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
                        timeout=45,
                    )
                    if resp.status_code == 200:
                        content = resp.json()["choices"][0]["message"]["content"]
                        parsed = self._extract_json_block(content)
                        if parsed:
                            logger.info("GROQ_BIFURCATION_SUCCESS | model=%s", model)
                            return parsed
            except Exception as e:
                logger.warning("Groq bifurcation failed: %s", e)

        # 2. Try Mistral
        mistral_key = os.getenv("MISTRAL_API_KEY")
        if mistral_key:
            try:
                import requests
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

        # 3. Try Local Ollama if available
        try:
            import requests
            ollama_url = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/chat")
            ollama_model = os.getenv("OLLAMA_MODEL", "qwen3:8b")
            payload = {
                "model": ollama_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "format": "json",
                "stream": False,
            }
            resp = requests.post(ollama_url, json=payload, timeout=60)
            if resp.status_code == 200:
                content = resp.json().get("message", {}).get("content", "")
                parsed = self._extract_json_block(content)
                if parsed:
                    logger.info("OLLAMA_BIFURCATION_SUCCESS")
                    return parsed
        except Exception as e:
            logger.debug("Ollama bifurcation check skipped or failed: %s", e)

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

    def _enrich_offerings_with_images(self, offerings: List[dict], corpus: str) -> None:
        """Scan corpus for image URLs and ensure offerings get populated with their image URLs."""
        # Find all https image URLs in corpus
        image_urls = re.findall(r"https?://[^\s\|\]\)\>]+(?:unsplash\.com[^\s\|\]\)\>]*|\.jpg|\.jpeg|\.png|\.webp)", corpus, re.I)
        if not image_urls:
            image_urls = re.findall(r"https?://images\.[^\s\|\]\)\>]+", corpus, re.I)

        if not image_urls:
            return

        for idx, off in enumerate(offerings):
            if not off.get("image_url") and not off.get("media_url"):
                off_name = off.get("name", "")
                assigned_url = None
                if off_name and len(off_name) > 3:
                    pos = corpus.lower().find(off_name[:30].lower())
                    if pos != -1:
                        window = corpus[pos : pos + 1000]
                        w_urls = re.findall(r"https?://[^\s\|\]\)\>]+(?:unsplash\.com[^\s\|\]\)\>]*|\.jpg|\.jpeg|\.png|\.webp|[a-zA-Z0-9_\-\./\?=&]+)", window, re.I)
                        for u in w_urls:
                            if "http" in u and ("unsplash" in u or "image" in u or ".jpg" in u or ".png" in u):
                                assigned_url = u
                                break
                if not assigned_url and idx < len(image_urls):
                    assigned_url = image_urls[idx]
                if assigned_url:
                    off["image_url"] = assigned_url
                    off["media_url"] = assigned_url
                    off.setdefault("attrs", {})["image_url"] = assigned_url

    def _parse_onboarding_guide(self, text: str) -> Optional[Dict[str, Any]]:
        """Direct deterministic parser for standardized AI WhatsApp Chatbot Onboarding Guide templates."""
        if "[SECTION:" not in text and "Onboarding Guide" not in text:
            return None

        data = {}
        # 1. Vertical
        v_match = re.search(r"Vertical:\s*([^\(\n\r]+)(?:\(([a-z0-9_]+)\))?", text, re.I)
        if v_match:
            vert = (v_match.group(2) or v_match.group(1)).strip().lower().replace(" ", "_")
            if "estate" in vert or "property" in vert:
                vert = "real_estate"
            elif "software" in vert or "it" in vert:
                vert = "it_software"
            elif "travel" in vert or "tour" in vert:
                vert = "tours_travel"
            elif "ecom" in vert or "retail" in vert:
                vert = "ecommerce"
            elif "bank" in vert or "finance" in vert:
                vert = "finance"
            elif "health" in vert or "clinic" in vert:
                vert = "healthcare"
            data["vertical"] = vert if vert in VALID_VERTICALS else "generic"
        else:
            data["vertical"] = "generic"

        # 2. Brand & Profile
        brand = {}
        b_match = re.search(r"\[SECTION:\s*BRAND\s*&\s*PROFILE\](.*?)(?=\[SECTION:|$)", text, re.S | re.I)
        if b_match:
            b_txt = b_match.group(1)
            # Company Legal Name
            m = re.search(r"Company Legal Name\s*(?:Official registered entity name)?\s*([^\n\r]+)", b_txt, re.I)
            if m:
                brand["name"] = m.group(1).strip()

            # Brand Display Name
            m = re.search(r"Brand Display Name\s*(?:Name displayed on WhatsApp)?\s*([^\n\r]+)", b_txt, re.I)
            if m:
                brand["display_name"] = m.group(1).strip()
                if "name" not in brand:
                    brand["name"] = m.group(1).strip()

            # Bot Assistant Name
            m = re.search(r"AI Bot Assistant Name\s*(?:Bot assistant persona name)?\s*([^\n\r]+)", b_txt, re.I)
            if m:
                brand["bot_name"] = m.group(1).strip()

            # Brand Tagline
            m = re.search(r"Brand Tagline\s*(?:Value proposition sentence)?\s*([^\n\r]+(?:\n[^\n\r]+)?)", b_txt, re.I)
            if m:
                tag = m.group(1).replace("\n", " ").strip()
                tag = re.split(r"Official Website|Support Email|Support Phone", tag, flags=re.I)[0].strip()
                brand["tagline"] = tag

            # Website
            m = re.search(r"Official Website\s*(?:Company website URL)?\s*(https?://[^\s]+)", b_txt, re.I)
            if m:
                brand["website"] = m.group(1).strip()

            # Support Email
            m = re.search(r"Support Email\s*(?:Support desk inbox)?\s*([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", b_txt, re.I)
            if m:
                brand["support_email"] = m.group(1).strip()

            # Support Phone
            m = re.search(r"Support Phone\s*(?:Helpline number with country code)?\s*(\+?[0-9\s-]{10,18})", b_txt, re.I)
            if m:
                brand["support_phone"] = m.group(1).strip()

            # Working Hours
            m = re.search(r"Working Hours\s*(?:Operating schedule & days)?\s*([^\n\r]+)", b_txt, re.I)
            if m:
                brand["working_hours"] = m.group(1).strip()

        data["brand"] = brand

        # 3. WhatsApp Menu
        menu_items = []
        m_match = re.search(r"\[SECTION:\s*WHATSAPP\s*MENU\](.*?)(?=\[SECTION:|$)", text, re.S | re.I)
        if m_match:
            m_txt = m_match.group(1)
            for line in m_txt.splitlines():
                line = line.strip()
                if not line or "Button Title" in line or "Parameter" in line:
                    continue
                act_match = re.search(r"\b(offerings|catalog|quote|get_quote|book_callback|callback|raise_ticket|support|faq|[a-z0-9_-]+)$", line, re.I)
                if act_match:
                    action = act_match.group(1).lower()
                    prefix = line[: act_match.start()].strip()
                    sec_match = re.search(r"[·•\-|\t]\s*([A-Za-z0-9 &'-]{3,24})\s*$", prefix)
                    if sec_match:
                        section = sec_match.group(1).strip()
                        main_part = prefix[: sec_match.start()].strip()
                    else:
                        parts = prefix.split()
                        section = parts[-1] if parts else "Explore"
                        main_part = " ".join(parts[:-1])

                    words = main_part.split()
                    if len(words) >= 4:
                        title = " ".join(words[:2])[:24]
                        desc = " ".join(words[2:])[:72]
                    else:
                        title = main_part[:24]
                        desc = main_part[:72]

                    known_titles = [
                        "Our Services", "Technologies", "Projects", "Get a Quote", "Careers", "Benefits",
                        "Explore Properties", "Ongoing Projects", "Schedule Site Visit", "Pricing Plans",
                        "Price & Payment Plans", "Customer Support", "Talk to Advisor", "Book Site Visit",
                        "RERA & Legal", "Request a Callback", "Project Brochure"
                    ]
                    for kt in known_titles:
                        if main_part.lower().startswith(kt.lower()):
                            title = kt
                            desc = main_part[len(kt) :].strip()
                            break

                    btn_icon = _assign_button_icon(title, action, data.get("vertical", "generic"))
                    menu_items.append({
                        "id": re.sub(r"[^a-z0-9_]+", "_", title.lower()).strip("_"),
                        "title": title[:24],
                        "description": desc[:72],
                        "section": section[:24],
                        "action": action,
                        "icon": btn_icon,
                    })
        data["menu_items"] = menu_items

        # 4. Catalog & Offerings WITH Image URLs
        offerings = []
        cat_match = re.search(r"\[SECTION:\s*CATALOG\s*&\s*OFFERINGS\](.*?)(?=\[SECTION:|$)", text, re.S | re.I)
        if cat_match:
            c_txt = cat_match.group(1)
            url_matches = list(re.finditer(r"(https?://[^\s]+)", c_txt))
            if url_matches:
                prev_idx = 0
                for i, um in enumerate(url_matches):
                    img_url = um.group(1).strip()
                    block = c_txt[prev_idx : um.start()].strip()
                    prev_idx = um.end()
                    lines = [l.strip() for l in block.splitlines() if l.strip()]
                    lines = [
                        l for l in lines
                        if not any(h in l.lower() for h in [
                            "service / offering", "category", "starting price", "tech stack", "image url", "image url:"
                        ])
                    ]
                    if not lines:
                        continue
                    name = lines[0]
                    p_match = re.search(r"(?:Starting\s*)?[₹$·€£]\s*[0-9,.]+(?:\s*(?:Lakhs?|Cr|Crores?|k|/month|/project|/fixed|/T&M))?", block, re.I)
                    if p_match:
                        price = p_match.group(0).replace("·", "₹").strip()
                        before_price = block[: p_match.start()].strip()
                        after_price = block[p_match.end() :].strip()
                    else:
                        price = None
                        before_price = lines[0] if lines else ""
                        after_price = " ".join(lines[1:]) if len(lines) > 1 else ""

                    # Clean any table header noise and instructions from before_price
                    b_lines = [l.strip() for l in before_price.splitlines() if l.strip()]
                    b_lines = [
                        l for l in b_lines
                        if not any(h in l.lower() for h in [
                            "service / offering", "service/offering", "category", "starting price",
                            "tech stack", "image url", "project / property", "paste a public",
                            "stored on the offering", "scope & deliverables", "typical timeline",
                            "configuration & sizes", "location / possession", "amenities & usps"
                        ])
                    ]
                    before_price = " ".join(b_lines).strip()

                    category = "General"
                    name = before_price

                    known_categories = [
                        "Custom Software", "Mobile Engineering", "AI Engineering", "Cloud / Teams", "Cloud & Teams", "DevOps",
                        "Luxury Apartments", "Commercial Office", "Commercial Space", "Residential Apartments",
                        "Villas", "Plots", "Penthouse", "Retail Shops", "Holiday Packages", "Wellness", "Consulting", "Services"
                    ]
                    for kc in known_categories:
                        if kc.lower() in before_price.lower():
                            category = kc
                            idx_cat = before_price.lower().find(kc.lower())
                            candidate_name = before_price[:idx_cat].strip(" ·-–—|")
                            if candidate_name:
                                name = candidate_name
                            break
                    else:
                        b_lines = [l.strip() for l in before_price.splitlines() if l.strip()]
                        if len(b_lines) >= 2:
                            name = " ".join(b_lines[:-1])
                            category = b_lines[-1]

                    desc = after_price if after_price else " ".join(lines)
                    short_desc = desc.split("\n")[0][:120] if desc else name

                    clean_name = re.sub(r"^[:\s·•\-\*\/]+", "", name).strip()
                    clean_category = re.sub(r"^[:\s·•\-\*\/]+", "", category).strip() or "General"
                    if not _is_offering_relevant_to_vertical(clean_name, clean_category, data.get("vertical", "generic")):
                        continue

                    offerings.append({
                        "name": clean_name,
                        "category": clean_category,
                        "price": price or "On Request",
                        "short_description": short_desc[:120],
                        "description": desc.strip(),
                        "image_url": img_url,
                        "media_url": img_url,
                        "attrs": {
                            "image_url": img_url,
                            "raw_specs": desc[:200]
                        }
                    })
        data["offerings"] = offerings

        # 5. FAQs & Policies
        faq_articles = []
        faq_match = re.search(r"\[SECTION:\s*FAQS\s*&\s*POLICIES\](.*?)(?=\[SECTION:|$)", text, re.S | re.I)
        if faq_match:
            f_txt = faq_match.group(1)
            q_blocks = re.findall(r"([A-Za-z0-9][^\?\n]+\?)\s+([^\?\n]+?)(?=\s+[A-Za-z0-9][^\?\n]+\?|$)", f_txt, re.S)
            if q_blocks:
                faq_md = "# Frequently Asked Questions & Policies\n\n"
                for q, a in q_blocks:
                    faq_md += f"### Q: {q.strip()}\n{a.strip()}\n\n"
                faq_articles.append({
                    "title": "FAQs & Policies",
                    "category": "FAQ",
                    "markdown_content": faq_md
                })
        data["knowledge_articles"] = faq_articles

        # 6. Info Pages (Intents)
        intents = []
        info_match = re.search(r"\[SECTION:\s*INFO\s*PAGES\](.*?)(?=\[SECTION:|$)", text, re.S | re.I)
        if info_match:
            i_txt = info_match.group(1)
            for line in i_txt.splitlines():
                line = line.strip()
                clean_line = re.sub(r"^[•·\-\*\d\.\s]+", "", line).strip()
                if not clean_line or any(clean_line.lower().startswith(s) for s in ["populates", "page name", "note:", "tip:", "instruction:", "parameter:"]):
                    continue
                parts = clean_line.split(":", 1) if ":" in clean_line else clean_line.split(maxsplit=1)
                if len(parts) == 2:
                    raw_p_name = parts[0].strip()
                    p_slug = _slugify(raw_p_name)
                    if p_slug in {"populates", "page", "page-name", "intent", "parameter", "section", "note", "tip", "instruction"} or len(p_slug) < 3:
                        continue
                    p_content = parts[1].strip()
                    if not p_content:
                        continue
                    intents.append({
                        "name": p_slug,
                        "examples": [f"Tell me about {raw_p_name}", f"What is {raw_p_name}?", f"Information regarding {raw_p_name}"],
                        "keywords": [k.lower() for k in raw_p_name.split() if len(k) > 2],
                        "answer": p_content,
                        "flow": None
                    })
                    if len(intents) >= 5:
                        break
        data["intents"] = intents

        # 7. Bot Persona & Guardrails
        p_match = re.search(r"\[SECTION:\s*BOT\s*PERSONA\s*&\s*GUARDRAILS\](.*?)(?=\[SECTION:|$)", text, re.S | re.I)
        if p_match:
            p_txt = p_match.group(1)
            m = re.search(r"Welcome Greeting\s*([^\n\r]+)", p_txt, re.I)
            if m:
                data.setdefault("brand", {})["greeting"] = m.group(1).strip()
            m = re.search(r"Strict Guardrails\s*([^\n\r]+)", p_txt, re.I)
            if m:
                data.setdefault("brand", {})["guardrails"] = m.group(1).strip()

        return data if (data.get("brand") or data.get("offerings")) else None

    def _heuristic_bifurcation(self, doc_summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Deterministic rule-based fallback when LLM is unavailable."""
        combined_text = "\n\n".join(d["text"] for d in doc_summaries)
        display_name = self.tenant_id.replace("-", " ").replace("_", " ").title()

        # Detect email and phone
        emails = re.findall(r"[\w\.-]+@[\w\.-]+\.\w+", combined_text)
        phones = re.findall(r"\+?\d[\d -]{8,14}\d", combined_text)
        support_email = emails[0] if emails else f"support@{self.tenant_id}.com"
        support_phone = phones[0] if phones else "+91 9800000000"

        # Detect vertical keywords
        lower_txt = combined_text.lower()
        vertical = "generic"
        if any(w in lower_txt for w in ("property", "residence", "bhk", "villa", "floor", "real estate", "rera")):
            vertical = "real_estate"
        elif any(w in lower_txt for w in ("tour", "travel", "flight", "destination", "itinerary", "package")):
            vertical = "tours_travel"
        elif any(w in lower_txt for w in ("software", "cloud", "saas", "tech", "api", "developer")):
            vertical = "it_software"
        elif any(w in lower_txt for w in ("shop", "product", "sku", "delivery", "cart", "discount")):
            vertical = "ecommerce"
        elif any(w in lower_txt for w in ("loan", "interest", "finance", "tax", "wealth", "advisory")):
            vertical = "finance"
        elif any(w in lower_txt for w in ("clinic", "doctor", "health", "hospital", "patient")):
            vertical = "healthcare"

        # Extract headings or bullet items as offerings
        lines = [line.strip() for line in combined_text.splitlines() if line.strip()]
        offerings = []
        for i, line in enumerate(lines[:100]):
            if (line.startswith("#") or line.startswith("*") or line.startswith("-")) and len(line) < 60:
                clean_name = line.lstrip("#*- ").strip()
                if len(clean_name) > 3 and not clean_name.lower().startswith("page"):
                    offerings.append({
                        "name": clean_name[:60],
                        "category": "General",
                        "price": "Contact for pricing",
                        "short_description": clean_name,
                        "description": clean_name,
                        "unit": "unit",
                        "attrs": {},
                    })
            if len(offerings) >= 10:
                break

        return {
            "vertical": vertical,
            "brand": {
                "name": display_name,
                "bot_name": f"{display_name} Assistant",
                "tagline": f"Official WhatsApp Assistant for {display_name}",
                "website": f"https://www.{self.tenant_id}.com",
                "support_email": support_email,
                "support_phone": support_phone,
                "signature": f"{display_name} — At your service.",
            },
            "business_hours": {
                "timezone": "Asia/Kolkata",
                "open": "09:30",
                "close": "18:30",
                "open_days": [0, 1, 2, 3, 4, 5],
            },
            "menu_items": [
                {
                    "id": "browse_offerings",
                    "title": "Explore Offerings"[:24],
                    "description": "Browse our catalog and products"[:72],
                    "section": "Explore"[:24],
                    "action": "offerings",
                },
                {
                    "id": "book_callback",
                    "title": "Book Consultation"[:24],
                    "description": "Schedule a phone call with our specialists"[:72],
                    "section": "Actions"[:24],
                    "action": "book_callback",
                },
                {
                    "id": "get_quote",
                    "title": "Pricing & Quotes"[:24],
                    "description": "Request customized cost estimate"[:72],
                    "section": "Actions"[:24],
                    "action": "get_quote",
                },
                {
                    "id": "support",
                    "title": "Customer Support"[:24],
                    "description": "Ask questions or get help"[:72],
                    "section": "Support"[:24],
                    "action": "faq",
                },
            ],
            "intents": [
                {
                    "name": "explore_offerings",
                    "description": "Browse catalog",
                    "keywords": ["catalog", "offerings", "products", "services", "list"],
                    "examples": ["Show me your catalog", "What do you offer?", "Browse offerings"],
                    "flow": None,
                },
                {
                    "name": "pricing_inquiry",
                    "description": "Pricing questions",
                    "keywords": ["price", "cost", "rates", "quote", "charges"],
                    "examples": ["How much does it cost?", "Can I get a quote?", "What are the rates?"],
                    "flow": "get_quote",
                },
                {
                    "name": "book_appointment",
                    "description": "Book consultation or callback",
                    "keywords": ["callback", "consultation", "appointment", "schedule", "call me"],
                    "examples": ["Can you call me back?", "Schedule an appointment", "Book a call"],
                    "flow": "book_callback",
                },
            ],
            "offerings": offerings or [
                {
                    "name": f"{display_name} Standard Service",
                    "category": "General",
                    "price": "On Request",
                    "short_description": "Comprehensive customer offering",
                    "description": "Full specifications provided upon consultation.",
                    "unit": "package",
                    "attrs": {},
                }
            ],
            "knowledge_articles": [
                {
                    "title": "Company Profile & Information",
                    "category": "About",
                    "markdown_content": f"# {display_name}\\n\\n" + combined_text[:3000],
                }
            ],
        }

    # ──────────────────────────────────────────────────────────────────────────
    # 3. Auto-Configuration & Application Engine
    # ──────────────────────────────────────────────────────────────────────────

    def apply_bifurcation(
        self,
        bifurcation: Dict[str, Any],
        raw_files: List[Dict[str, Any]],
        auto_publish: bool = True,
    ) -> Dict[str, Any]:
        """Apply extracted data across database tables, profile draft, and knowledge base."""
        tenant_id = self.tenant_id
        summary: Dict[str, Any] = {
            "tenant_id": tenant_id,
            "vertical": bifurcation.get("vertical", "generic"),
            "brand": {},
            "menu_buttons_count": 0,
            "intents_count": 0,
            "offerings_created": 0,
            "offerings_sample": [],
            "kb_chunks_indexed": 0,
            "version": 0,
            "status": "configured",
        }

        # 3.1 Sanitize vertical
        vertical = bifurcation.get("vertical", "generic")
        if vertical not in VALID_VERTICALS:
            vertical = "generic"

        # 3.2 Sanitize Brand
        brand_raw = bifurcation.get("brand", {})
        clean_brand = {
            "name": brand_raw.get("name") or tenant_id.replace("-", " ").title(),
            "bot_name": brand_raw.get("bot_name") or f"{tenant_id.title()} Assistant",
            "tagline": brand_raw.get("tagline") or "",
            "website": brand_raw.get("website") or f"https://www.{tenant_id}.com",
            "support_email": brand_raw.get("support_email") or f"support@{tenant_id}.com",
            "support_phone": brand_raw.get("support_phone") or "+91 9800000000",
            "signature": brand_raw.get("signature") or f"{tenant_id.title()} — At your service.",
        }
        # Validate format
        if clean_brand["website"] and not clean_brand["website"].startswith("http"):
            clean_brand["website"] = "https://" + clean_brand["website"].lstrip("/")
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", clean_brand["support_email"]):
            clean_brand["support_email"] = f"support@{tenant_id}.com"

        summary["brand"] = clean_brand

        # 3.3 Sanitize WhatsApp Menu Buttons (Meta Character Limitations & Deduplication)
        menu_items_raw = bifurcation.get("menu_items", [])
        menu_buttons = []
        seen_b_ids = set()
        seen_b_titles = set()

        for i, item in enumerate(menu_items_raw):
            raw_title = (item.get("title") or "").strip()[:24]
            if not raw_title or raw_title.lower() in {"button title", "parameter", "action", "section", "none", "empty"}:
                continue
            clean_t = re.sub(r"[^\w\s]", " ", raw_title).strip().lower()
            clean_t = " ".join(clean_t.split())
            if clean_t in seen_b_titles:
                continue

            b_id = _slugify(item.get("id") or raw_title or f"opt_{i}")
            if not b_id or b_id in seen_b_ids:
                b_id = f"{b_id or 'opt'}_{len(menu_buttons) + 1}"
            seen_b_ids.add(b_id)
            seen_b_titles.add(clean_t)

            desc = (item.get("description") or "").strip()[:72]
            sec = (item.get("section") or "Explore").strip()[:24]
            action = item.get("action") or "faq"
            btn_icon = item.get("icon") or _assign_button_icon(raw_title, action, vertical)
            btn_image_url = item.get("image_url") or None

            button_dict = {
                "id": b_id,
                "title": raw_title,
                "description": desc,
                "section": sec,
                "icon": btn_icon,
                "image_url": btn_image_url,
                "sort_order": len(menu_buttons) + 1,
                "enabled": True,
            }
            if action in ("offerings", "catalog"):
                button_dict["intent"] = "offerings"
            elif action in ("book_callback", "get_quote", "raise_ticket"):
                button_dict["flow"] = action
            else:
                button_dict["intent"] = b_id

            menu_buttons.append(button_dict)
            if len(menu_buttons) >= 8:  # Keep menu clean and compact (avoid awkward grid wrap)
                break

        if not menu_buttons:
            # Fallback 3 default buttons with vertical-aware icons
            menu_buttons = [
                {"id": "offerings", "title": "Explore Offerings"[:24], "description": "Browse catalog"[:72], "section": "Main"[:24], "icon": _assign_button_icon("Explore Offerings", "offerings", vertical), "intent": "offerings", "sort_order": 1, "enabled": True},
                {"id": "callback", "title": "Book Consultation"[:24], "description": "Request a callback"[:72], "section": "Main"[:24], "icon": _assign_button_icon("Book Consultation", "book_callback", vertical), "flow": "book_callback", "sort_order": 2, "enabled": True},
                {"id": "support", "title": "Customer Help"[:24], "description": "Ask questions"[:72], "section": "Main"[:24], "icon": _assign_button_icon("Customer Help", "raise_ticket", vertical), "flow": "raise_ticket", "sort_order": 3, "enabled": True},
            ]
        summary["menu_buttons_count"] = len(menu_buttons)

        # 3.4 Sanitize & Canonicalize Intents (strictly project-relevant, cap at 4-7)
        intents_raw = bifurcation.get("intents", [])
        clean_intents = _canonicalize_and_deduplicate_intents(
            intents_raw,
            vertical=vertical,
            menu_buttons=menu_buttons,
            max_intents=7,
        )
        summary["intents_count"] = len(clean_intents)

        # 3.5 Update Tenant Profile Draft in Database
        draft = tenancy_store.get_draft(tenant_id) or {}
        draft["tenant_id"] = tenant_id
        draft["vertical"] = vertical
        draft["display_name"] = clean_brand["name"]
        draft["brand"] = clean_brand

        # Fetch vertical defaults and existing draft to tombstone non-selected buttons
        from shared.tenancy.defaults import get_vertical_defaults
        defaults = get_vertical_defaults(vertical)
        default_menu_buttons = defaults.get("menu", {}).get("buttons", [])
        default_ids = {
            b.get("id") for b in default_menu_buttons if isinstance(b, dict) and b.get("id")
        }
        old_draft_ids = {
            b.get("id") for b in draft.get("menu", {}).get("buttons", [])
            if isinstance(b, dict) and b.get("id") and not b.get("__remove__")
        }
        active_ids = {b["id"] for b in menu_buttons}

        final_menu_buttons = list(menu_buttons)
        tombstone_ids = (default_ids | old_draft_ids) - active_ids
        for tid in sorted(tombstone_ids):
            final_menu_buttons.append({"id": tid, "__remove__": True})

        draft["menu"] = {
            "key": "kb_main",
            "header": clean_brand["name"],
            "body": "Welcome! How can we assist you today?",
            "footer": "Select an option or type your query directly",
            "button_text": "Select Option",
            "buttons": final_menu_buttons,
        }

        # Tombstone unneeded default intents and stale draft intents
        default_intents = defaults.get("intents", [])
        default_intent_names = {
            i.get("name") for i in default_intents if isinstance(i, dict) and i.get("name")
        }
        old_draft_intent_names = {
            i.get("name") for i in draft.get("intents", [])
            if isinstance(i, dict) and i.get("name") and not i.get("__remove__")
        }
        active_intent_names = {i["name"] for i in clean_intents}

        final_clean_intents = list(clean_intents)
        tombstone_intent_names = (default_intent_names | old_draft_intent_names) - active_intent_names
        for tin in sorted(tombstone_intent_names):
            final_clean_intents.append({"name": tin, "__remove__": True})

        draft["intents"] = final_clean_intents

        if "business_hours" in bifurcation:
            draft["business_hours"] = bifurcation["business_hours"]

        # Ensure flows exist
        if "flows" not in draft or not draft["flows"]:
            draft["flows"] = [
                {"name": "book_callback", "success_message": f"Thank you! Your consultation request has been scheduled with {clean_brand['bot_name']}."},
                {"name": "get_quote", "success_message": f"Thank you! Our specialist will prepare a customized quote and follow up promptly."},
                {"name": "raise_ticket", "success_message": f"Your request has been logged. A support ticket has been created and an executive will assist you."}
            ]

        with get_db_context() as conn:
            tenancy_store.save_draft(tenant_id, draft, updated_by=self.actor.get("username", "admin"), conn=conn)

            # Auto-publish if requested
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

        # Sync client config file clients/<tenant_id>/config.json
        try:
            tenancy_loader.write_client_config_file(tenant_id, draft)
        except Exception as file_exc:
            logger.warning("Could not sync client config file: %s", file_exc)

        # 3.6 Insert Offerings into Catalog (products table)
        offerings_raw = bifurcation.get("offerings", [])
        clean_offerings = [
            off for off in offerings_raw
            if isinstance(off, dict) and _is_offering_relevant_to_vertical(
                off.get("name", ""), off.get("category", ""), vertical
            )
        ]
        existing_products_list = list_products(tenant_id=tenant_id, active_only=False)
        existing_by_name = {p.get("name", "").lower().strip(): p for p in existing_products_list if p.get("name")}
        existing_by_slug = {p.get("slug"): p for p in existing_products_list if p.get("slug")}
        inserted_count = 0
        upserted_ids = set()
        upserted_names = set()

        for off in clean_offerings:
            name = (off.get("name") or "").strip()
            name = re.sub(r"^[:\s·•\-\*\/]+", "", name).strip()
            if not name:
                continue
            cat = (off.get("category") or "General").strip()
            cat = re.sub(r"^[:\s·•\-\*\/]+", "", cat).strip() or "General"
            price = (str(off.get("price") or "")).strip() or None
            short_desc = (off.get("short_description") or name).strip()
            desc = (off.get("description") or short_desc).strip()
            attrs = off.get("attrs") or {}
            target_slug = _slugify(name)
            upserted_names.add(name.lower())

            # EXTRACT IMAGE / MEDIA URL
            media_url = (
                off.get("image_url")
                or off.get("media_url")
                or attrs.get("image_url")
                or attrs.get("media_url")
                or ""
            )
            if media_url and isinstance(media_url, str):
                media_url = media_url.strip()
                if not media_url.startswith("http"):
                    if "unsplash.com" in media_url or any(ext in media_url.lower() for ext in (".jpg", ".jpeg", ".png", ".webp")):
                        media_url = "https://" + media_url.lstrip("/")
                    else:
                        media_url = None
            else:
                media_url = None

            if media_url:
                attrs["image_url"] = media_url

            matched_prod = existing_by_name.get(name.lower()) or existing_by_slug.get(target_slug)
            if matched_prod:
                prod_id = matched_prod["id"]
                update_product(
                    prod_id,
                    tenant_id=tenant_id,
                    price=price,
                    description=desc,
                    short_description=short_desc,
                    category=cat,
                    media_url=media_url,
                    attrs_json=attrs,
                )
                upserted_ids.add(prod_id)
            else:
                # Check if target_slug is already used in products table globally
                final_slug = target_slug
                with get_db_context() as conn:
                    row = conn.execute("SELECT id, tenant_id FROM products WHERE slug = ?", (target_slug,)).fetchone()
                    if row:
                        if str(row["tenant_id"]) == str(tenant_id):
                            # Same tenant already has this slug, update the existing product
                            update_product(
                                row["id"],
                                tenant_id=tenant_id,
                                price=price,
                                description=desc,
                                short_description=short_desc,
                                category=cat,
                                media_url=media_url,
                                attrs_json=attrs,
                            )
                            upserted_ids.add(row["id"])
                            continue
                        else:
                            final_slug = f"{target_slug}-{tenant_id}"

                new_id = save_product(
                    name=name,
                    slug=final_slug,
                    category=cat,
                    price=price,
                    short_description=short_desc,
                    description=desc,
                    media_url=media_url,
                    media_type="image",
                    attrs_json=attrs,
                    tenant_id=tenant_id,
                    actor=self.actor,
                )
                upserted_ids.add(new_id)
                inserted_count += 1
                if len(summary["offerings_sample"]) < 5:
                    summary["offerings_sample"].append(name)

        # Prune any existing products that are cross-vertical, template noise, or outdated duplicates
        current_tenant_products = list_products(tenant_id=tenant_id, active_only=False)
        for p in current_tenant_products:
            p_id = p.get("id")
            p_name = (p.get("name") or "").strip()
            p_cat = (p.get("category") or "").strip()

            # 1. Unrelated to vertical or header noise -> delete immediately
            if not _is_offering_relevant_to_vertical(p_name, p_cat, vertical):
                logger.info("PRUNING_UNRELATED_PRODUCT | tenant=%s | id=%s | name=%s", tenant_id, p_id, p_name)
                delete_product(p_id, hard=True, tenant_id=tenant_id)
                continue

            # 2. Older duplicate of an upserted offering -> delete immediately
            if clean_offerings and p_id not in upserted_ids:
                is_dupe = any(
                    (clean_name in p_name.lower() or p_name.lower() in clean_name)
                    for clean_name in upserted_names
                )
                if is_dupe:
                    logger.info("PRUNING_DUPLICATE_PRODUCT | tenant=%s | id=%s | name=%s", tenant_id, p_id, p_name)
                    delete_product(p_id, hard=True, tenant_id=tenant_id)

        summary["offerings_created"] = inserted_count

        # 3.7 Write Knowledge Base Markdown Files & Build Vector Embeddings
        knowledge_dir = Path("clients") / tenant_id / "knowledge"
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

            # Chunk markdown content
            sections = md_content.split("\n## ")
            for sec in sections:
                if sec.strip():
                    all_chunks_to_index.append(sec.strip())

        # Also chunk raw text from uploaded files
        if raw_files:
            if isinstance(raw_files, (str, bytes)):
                raw_files = [{"text": str(raw_files)}]
            for rf in raw_files:
                if isinstance(rf, dict):
                    txt = rf.get("text", "")
                elif isinstance(rf, str):
                    txt = rf
                else:
                    txt = ""
                if txt:
                    paragraphs = [p.strip() for p in txt.split("\n\n") if len(p.strip()) > 80]
                    all_chunks_to_index.extend(paragraphs[:50])

        if all_chunks_to_index:
            try:
                # Format chunks as dicts for save_knowledge_base_chunks
                formatted_chunks = [
                    {"content": ch, "source_file": "auto_bifurcated_docs.md"}
                    for ch in all_chunks_to_index
                ]
                save_knowledge_base_chunks(
                    chunks=formatted_chunks,
                    source_file="auto_bifurcated_docs.md",
                    tenant_id=tenant_id,
                )
                # Rebuild FAISS & missing embeddings
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
                        "brand": clean_brand["name"],
                        "offerings_count": inserted_count,
                        "menu_buttons_count": len(menu_buttons),
                        "intents_count": len(clean_intents),
                        "chunks_count": summary["kb_chunks_indexed"],
                    },
                )
        except Exception:
            pass

        return summary

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

        # Apply bifurcation across all components
        result_summary = self.apply_bifurcation(
            bifurcation=bifurcation,
            raw_files=extracted_docs,
            auto_publish=auto_publish,
        )

        result_summary["files_processed"] = [d["filename"] for d in extracted_docs]
        return result_summary
