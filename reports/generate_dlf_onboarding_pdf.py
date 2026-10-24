"""Generate a complete, production-ready Real Estate Onboarding PDF for DLF Limited.

Creates a filled real-estate client document ready for immediate download,
client sharing, or uploading into the auto-bifurcation engine.
"""

from __future__ import annotations

import os
from pathlib import Path
import fitz  # PyMuPDF

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PDF = PROJECT_ROOT / "reports" / "DLF_Real_Estate_Client_Onboarding.pdf"
STATIC_PDF = PROJECT_ROOT / "backend" / "static" / "templates" / "onboarding" / "DLF_Real_Estate_Client_Onboarding.pdf"

# Ensure output directories exist
OUTPUT_PDF.parent.mkdir(parents=True, exist_ok=True)
STATIC_PDF.parent.mkdir(parents=True, exist_ok=True)


class DLFOnboardingPDFGenerator:
    def __init__(self, output_path: Path):
        self.output_path = output_path
        self.doc = fitz.open()
        self.page_w = 595.0
        self.page_h = 842.0
        self.margin = 38.0
        self.content_w = self.page_w - 2 * self.margin
        self.page_num = 0
        self.page = None
        self.y = self.margin
        self._new_page()

    def _new_page(self):
        if self.page:
            self._draw_footer()
        self.page_num += 1
        self.page = self.doc.new_page(width=self.page_w, height=self.page_h)
        self.y = self.margin
        self._draw_header()

    def _draw_header(self):
        self.page.insert_text(
            (self.margin, self.y + 10),
            "DLF LIMITED — REAL ESTATE CLIENT ONBOARDING & DATA SPECIFICATION",
            fontsize=8,
            fontname="hebo",
            color=(0.12, 0.22, 0.38),  # DLF Navy
        )
        self.page.draw_line(
            (self.margin, self.y + 15),
            (self.page_w - self.margin, self.y + 15),
            color=(0.82, 0.86, 0.9),
            width=0.75,
        )
        self.y += 25

    def _draw_footer(self):
        self.page.draw_line(
            (self.margin, self.page_h - 28),
            (self.page_w - self.margin, self.page_h - 28),
            color=(0.82, 0.86, 0.9),
            width=0.75,
        )
        self.page.insert_text(
            (self.margin, self.page_h - 16),
            "DLF India • WhatsApp Chatbot Onboarding Document • Auto-Bifurcation Ready",
            fontsize=7.2,
            fontname="helv",
            color=(0.45, 0.5, 0.55),
        )
        self.page.insert_text(
            (self.page_w - self.margin - 40, self.page_h - 16),
            f"Page {self.page_num}",
            fontsize=7.8,
            fontname="hebo",
            color=(0.12, 0.22, 0.38),
        )

    def _ensure_space(self, needed_h: float):
        if self.y + needed_h > self.page_h - 40:
            self._new_page()

    def draw_section_header(self, title: str, subtitle: str = ""):
        self._ensure_space(34 if subtitle else 26)
        # Navy section band
        rect = fitz.Rect(self.margin, self.y, self.page_w - self.margin, self.y + 18)
        self.page.draw_rect(rect, color=(0.12, 0.22, 0.38), fill=(0.12, 0.22, 0.38))
        self.page.insert_text(
            (self.margin + 8, self.y + 13),
            title,
            fontsize=9.2,
            fontname="hebo",
            color=(1.0, 1.0, 1.0),
        )
        self.y += 22
        if subtitle:
            self.page.insert_text(
                (self.margin, self.y + 7),
                subtitle,
                fontsize=7.5,
                fontname="helv",
                color=(0.4, 0.45, 0.5),
            )
            self.y += 12

    def draw_table(
        self,
        headers: list[str],
        rows: list[list[str]],
        col_widths: list[float],
        header_bg=(0.12, 0.22, 0.38),
        font_size=7.0,
    ):
        line_height = font_size * 1.34
        pad = 4.0

        # Header Row
        self._ensure_space(20)
        h_rect = fitz.Rect(self.margin, self.y, self.page_w - self.margin, self.y + 17)
        self.page.draw_rect(h_rect, color=header_bg, fill=header_bg)

        # Header grid vertical lines
        x_grid = self.margin
        for w in col_widths:
            self.page.draw_line((x_grid, self.y), (x_grid, self.y + 17), color=(0.7, 0.75, 0.8), width=0.5)
            x_grid += w
        self.page.draw_line((self.page_w - self.margin, self.y), (self.page_w - self.margin, self.y + 17), color=(0.7, 0.75, 0.8), width=0.5)

        x_curr = self.margin
        for idx, h_text in enumerate(headers):
            self.page.insert_text(
                (x_curr + pad, self.y + 11.5),
                h_text[:28],
                fontsize=font_size + 0.3,
                fontname="hebo",
                color=(1.0, 1.0, 1.0),
            )
            x_curr += col_widths[idx]
        self.y += 17

        # Rows
        for r_idx, row in enumerate(rows):
            max_lines = 1
            wrapped_cells = []
            for c_idx, cell_text in enumerate(row):
                w = col_widths[c_idx] - (2 * pad)
                chars_per_line = max(8, int(w / (font_size * 0.51)))
                words = str(cell_text).split()
                lines = []
                cur_line = ""
                for wd in words:
                    if len(cur_line) + len(wd) + 1 <= chars_per_line:
                        cur_line = f"{cur_line} {wd}".strip()
                    else:
                        if cur_line:
                            lines.append(cur_line)
                        cur_line = wd
                if cur_line:
                    lines.append(cur_line)
                lines = lines or [""]
                max_lines = max(max_lines, len(lines))
                wrapped_cells.append(lines)

            row_h = max_lines * line_height + (2 * pad)
            self._ensure_space(row_h)

            bg_color = (0.97, 0.98, 0.99) if r_idx % 2 == 0 else (1.0, 1.0, 1.0)
            row_rect = fitz.Rect(self.margin, self.y, self.page_w - self.margin, self.y + row_h)
            self.page.draw_rect(row_rect, color=(0.8, 0.83, 0.88), fill=bg_color, width=0.45)

            # Cell grid vertical lines
            x_grid = self.margin
            for w in col_widths:
                self.page.draw_line((x_grid, self.y), (x_grid, self.y + row_h), color=(0.8, 0.83, 0.88), width=0.45)
                x_grid += w
            self.page.draw_line((self.page_w - self.margin, self.y), (self.page_w - self.margin, self.y + row_h), color=(0.8, 0.83, 0.88), width=0.45)

            x_curr = self.margin
            for c_idx, lines in enumerate(wrapped_cells):
                for l_idx, line_str in enumerate(lines):
                    y_pos = self.y + pad + (l_idx + 1) * line_height - 2
                    is_bold = (c_idx == 0)
                    self.page.insert_text(
                        (x_curr + pad, y_pos),
                        line_str,
                        fontsize=font_size,
                        fontname="hebo" if is_bold else "helv",
                        color=(0.1, 0.14, 0.2),
                    )
                x_curr += col_widths[c_idx]
            self.y += row_h

        self.y += 8

    def generate(self):
        # Cover / Header Banner
        self._ensure_space(65)
        self.page.draw_rect(
            fitz.Rect(self.margin, self.y, self.page_w - self.margin, self.y + 44),
            color=(0.88, 0.92, 0.96),
            fill=(0.95, 0.97, 0.99),
            width=0.6,
        )
        self.page.insert_text(
            (self.margin + 12, self.y + 17),
            "DLF LUXURY REAL ESTATE — CLIENT ONBOARDING SPECIFICATION",
            fontsize=12,
            fontname="hebo",
            color=(0.12, 0.22, 0.38),
        )
        self.page.insert_text(
            (self.margin + 12, self.y + 32),
            "Vertical: Real Estate & Property Development (real_estate) • Official Tenant Profile & Knowledge Base",
            fontsize=8.2,
            fontname="helv",
            color=(0.3, 0.4, 0.5),
        )
        self.y += 54

        # ──────────────────────────────────────────────────────────────────────
        # SECTION 1: BRAND & PROFILE
        # ──────────────────────────────────────────────────────────────────────
        self.draw_section_header(
            "[SECTION: BRAND & PROFILE]",
            "Corporate identity, public display credentials and customer helpline parameters.",
        )
        brand_rows = [
            ["Company Legal Name", "Official registered corporate entity", "DLF Limited"],
            ["Brand / Display Name", "Public name presented on WhatsApp", "DLF India"],
            ["Tenant ID / Code", "Platform unique identifier", "dlf"],
            ["AI Bot Assistant Name", "Dedicated AI real estate concierge", "DLF Luxury Advisor"],
            ["Brand Tagline", "Core value proposition", "DLF - Where Luxury Meets Life"],
            ["Official Website URL", "Corporate & project portal", "https://www.dlf.in"],
            ["Customer Support Email", "Corporate buyer inquiries & care", "care@dlf.in"],
            ["Customer Support Phone", "All-India luxury helpline", "+91 8000305305"],
            ["WhatsApp Bot Number", "Dedicated WhatsApp Business Number", "+91 9810001234"],
            ["Business Working Hours", "Site office & concierge operation", "09:30 AM - 07:00 PM (Mon-Sat)"],
            ["Timezone & Currency", "Default operations timezone", "Asia/Kolkata / INR"],
        ]
        self.draw_table(
            headers=["Parameter", "Description & Scope", "DLF Specified Value"],
            rows=brand_rows,
            col_widths=[135.0, 180.0, 204.0],
            header_bg=(0.12, 0.22, 0.38),
            font_size=7.1,
        )

        # ──────────────────────────────────────────────────────────────────────
        # SECTION 2: WHATSAPP MENU
        # ──────────────────────────────────────────────────────────────────────
        self.draw_section_header(
            "[SECTION: WHATSAPP MENU]",
            "Interactive WhatsApp navigation buttons (strictly conforming to Meta API 24/72 char limits).",
        )
        menu_rows = [
            ["Explore Residences", "Browse 3, 4 & 5 BHK luxury apartments and penthouses", "🏢 Residences", "offerings"],
            ["Ongoing Projects", "View masterplans, prime locations & tower features", "🏢 Residences", "offering_details"],
            ["Commercial Offices", "Grade-A tech parks, bare-shell suites & cyber hubs", "💼 Commercial", "offerings"],
            ["Schedule Site Visit", "Book private chauffeur pickup & guided project tour", "📅 Site Tours", "book_callback"],
            ["Pricing & Plans", "Cost breakdown, CLP schedules & home loan schemes", "💳 Pricing", "quote"],
            ["RERA & Approvals", "Municipal sanctions, RERA certificates & bank tie-ups", "ℹ️ Legal Info", "faq"],
            ["Customer Care", "Existing unit owner support, queries & ticketing", "🆘 Support", "raise_ticket"],
        ]
        self.draw_table(
            headers=["Button Title (<=24ch)", "Description (<=72ch)", "Category Section", "Action Mapping"],
            rows=menu_rows,
            col_widths=[125.0, 210.0, 94.0, 90.0],
            header_bg=(0.12, 0.22, 0.38),
            font_size=6.9,
        )

        # ──────────────────────────────────────────────────────────────────────
        # SECTION 3: CATALOG & OFFERINGS
        # ──────────────────────────────────────────────────────────────────────
        self.draw_section_header(
            "[SECTION: CATALOG & OFFERINGS]",
            "Residential towers, luxury golf-course penthouses, and Grade-A commercial developments.",
        )
        catalog_headers = [
            "Property Name", "Type", "Configuration", "Carpet Area", "Price Range",
            "Location", "Key Amenities", "Possession", "RERA ID"
        ]
        catalog_rows = [
            [
                "The Camellias", "Super-Luxury Residence", "4 & 5 BHK Penthouses", "7,400 - 11,000 sqft",
                "INR 45 Cr - 95 Cr", "DLF Golf Links, Gurugram",
                "Private Golf Course, 7-Star Club, Olympic Pool, Concierge", "Ready to Move", "HRERA-480/2017"
            ],
            [
                "The Ultima", "Luxury High-Rise", "3 & 4 BHK Apartments", "2,100 - 2,872 sqft",
                "INR 3.5 Cr - 6.8 Cr", "Sector 81, Gurugram",
                "405 Hectares Reserved Greens, Clubhouse, Tennis & Spa", "Ready to Move", "HRERA-02/2018"
            ],
            [
                "DLF One Midtown", "Premium High-Rise", "2, 3 & 4 BHK Luxury", "1,750 - 3,030 sqft",
                "INR 3.2 Cr - 8.5 Cr", "Shivaji Marg, Moti Nagar, Delhi",
                "128 Acres Greenery, 45,000 sqft Club, Metro Connected", "Dec 2026", "DLRERA2021P0007"
            ],
            [
                "The Skycourt", "Air-Conditioned Luxury", "3 BHK High-Rise", "1,900 - 2,050 sqft",
                "INR 2.8 Cr - 4.2 Cr", "Sector 86, Gurugram",
                "Sky-Deck, Banquet Hall, 2 Covered Car Parks, Fitness Hub", "Ready to Move", "HRERA-10/2019"
            ],
            [
                "DLF Cybercity Tech Park", "Grade-A Commercial", "Bare Shell & Warm Shell", "5,000 - 100,000 sqft",
                "INR 125 / sq.ft. (Lease)", "Cybercity, Sector 24, Gurugram",
                "LEED Platinum Certified, 100% Redundant Power, Metro Stop", "Immediate", "HRERA-COM-01/2016"
            ],
            [
                "DLF Privana South", "Ultra-Luxury High-Rise", "4 BHK Luxury Residences", "3,577 sqft",
                "INR 7.5 Cr - 12.5 Cr", "Sector 76/77, Gurugram",
                "Aravalli Hills View, Grand Central Clubhouse, Forest Living", "2028", "HRERA-68/2023"
            ],
        ]
        col_w = self.content_w / len(catalog_headers)
        self.draw_table(
            headers=catalog_headers,
            rows=catalog_rows,
            col_widths=[col_w] * len(catalog_headers),
            header_bg=(0.08, 0.35, 0.32),  # Deep Emerald
            font_size=6.2,
        )

        # ──────────────────────────────────────────────────────────────────────
        # SECTION 4: FAQS & POLICIES
        # ──────────────────────────────────────────────────────────────────────
        self.draw_section_header(
            "[SECTION: FAQS & POLICIES]",
            "Official customer inquiry responses and legal investment guidelines for conversational RAG retrieval.",
        )
        faq_headers = ["Frequently Asked Customer Question", "Verified Official Answer", "Category"]
        faq_rows = [
            [
                "What is the procedure for Non-Resident Indians (NRIs) to invest in DLF properties?",
                "NRIs, PIOs, and OCIs can invest directly in DLF residential or commercial units using funds from NRE/NRO/FCNR accounts. We provide end-to-end assistance with FEMA compliance, Power of Attorney (PoA) registration, and legal verification.",
                "NRI Investments"
            ],
            [
                "Which banking partners offer approved home loans for DLF luxury projects?",
                "All DLF projects are pre-approved by leading financial institutions including SBI, HDFC Bank, ICICI Bank, Axis Bank, and Kotak Mahindra. Special low-rate financing up to 75-80% of property cost is available with fast-track processing.",
                "Home Loans"
            ],
            [
                "How do I schedule an in-person site visit or golf-cart tour of the developments?",
                "You can tap 'Schedule Site Visit' or request a callback. Our team arranges complimentary door-to-door luxury AC chauffeur pickup and a personalized tour of sample apartments, clubhouses, and amenities.",
                "Site Tours"
            ],
            [
                "What is the booking advance and typical payment schedule (CLP)?",
                "A formal booking advance of ₹10 Lakhs to ₹25 Lakhs (depending on typology) reserves the selected apartment. Payment schedules follow the Construction-Linked Plan (CLP) or Possession-Linked Plan (PLP) with transparent milestones.",
                "Payment Plans"
            ],
            [
                "Are all DLF projects RERA certified with clear land titles?",
                "Yes, 100% of DLF projects hold approved building sanctions from municipal development authorities, environmental clearances, and valid state RERA registration with verified unencumbered freehold land ownership.",
                "Legal & Approvals"
            ],
            [
                "What amenities are included within DLF clubhouses?",
                "DLF Clubhouses feature world-class facilities: all-weather heated swimming pools, Olympic-standard tennis & squash courts, private screening cinemas, spa & wellness salons, fine-dining restaurants, and banquet lawns.",
                "Amenities"
            ],
        ]
        self.draw_table(
            headers=faq_headers,
            rows=faq_rows,
            col_widths=[160.0, 275.0, 84.0],
            header_bg=(0.24, 0.2, 0.6),  # Royal Indigo
            font_size=6.7,
        )

        # ──────────────────────────────────────────────────────────────────────
        # SECTION 5: BOT PERSONA & GUARDRAILS
        # ──────────────────────────────────────────────────────────────────────
        self.draw_section_header(
            "[SECTION: BOT PERSONA & GUARDRAILS]",
            "Tone, conversational demeanor, strict guardrails and human agent escalation logic.",
        )
        guard_headers = ["Guardrail Parameter", "Bot Behavior / Value"]
        guard_rows = [
            ["Tone & Persona", "Consultative, polite, prestigious, knowledgeable, and brand-aligned"],
            ["Welcome Greeting", "Welcome to DLF India! I am your AI Luxury Property Concierge. How may I assist with your dream residence or commercial space today?"],
            ["Strict Guardrails (Never-Do List)", "1. Never negotiate unapproved prices or commit to extra discounts on WhatsApp.\n2. Never promise delivery or possession dates outside official RERA filings.\n3. Never solicit OTPs, banking credentials, or advance token money on chat."],
            ["Human Escalation Trigger", "Instantly route to human relationship manager when customer requests 'human', 'agent', 'sales manager', or asks for a customized multi-crore investment quote."],
        ]
        self.draw_table(
            headers=guard_headers,
            rows=guard_rows,
            col_widths=[140.0, 379.0],
            header_bg=(0.55, 0.12, 0.15),  # Crimson Red
            font_size=6.8,
        )

        self._draw_footer()
        self.doc.set_metadata({
            "title": "DLF Real Estate — Client Onboarding Specification",
            "subject": "Predefined AI WhatsApp Chatbot Onboarding Document",
            "author": "Antigravity Real Estate Engine",
        })

        # Save to both locations
        self.doc.save(str(self.output_path))
        self.doc.save(str(STATIC_PDF))
        self.doc.close()
        print(f"Generated DLF Onboarding PDF at: {self.output_path} ({os.path.getsize(self.output_path):,} bytes)")
        print(f"Also mirrored to static templates at: {STATIC_PDF}")
        return self.output_path


if __name__ == "__main__":
    gen = DLFOnboardingPDFGenerator(OUTPUT_PDF)
    gen.generate()
