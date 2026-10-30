"""Build a production-ready IT/software onboarding PDF for Leeway Softech.

Uses ReportLab tables (so AutoBifurcator find_tables / DOCX-style parse works)
and real brand assets from https://leewaysoftech.com/.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets" / "leeway-pdf"
PNG_DIR = ASSETS / "png"
OUT_DIR = ROOT / "backend" / "static" / "templates" / "onboarding"
EXAMPLES = ROOT / "onboarding_kit_examples"
OUT_PDF = OUT_DIR / "it_software_onboarding_kit.pdf"
EXAMPLE_PDF = EXAMPLES / "leeway_softech_it_onboarding_kit.pdf"
PRETTY = ROOT / "reports" / "leeway_softech_it_onboarding_kit.pdf"

NAVY = colors.Color(0.07, 0.14, 0.28)
TEAL = colors.Color(0.06, 0.46, 0.43)
LIGHT = colors.Color(0.96, 0.97, 0.98)
MUTED = colors.Color(0.40, 0.45, 0.52)

# Image URLs use short public paths so table cell wrap does not break the host.
IMG_AI = "https://leewaysoftech.com/assets/images/roboatImage.webp"
IMG_LOGO = "https://leewaysoftech.com/assets/images/leeway-logo.webp"
IMG_ISO = "https://leewaysoftech.com/assets/images/iso27001.webp"

OFFERINGS = [
    ["Service / Offering", "Category", "Starting Price / Model", "Tech Stack & Tools", "Typical Timeline", "Scope & Deliverables", "Image URL"],
    ["AI Chatbot Development", "Conversational AI", "INR 75,000 - 3.5 Lakh", "WhatsApp/Web, NLP, RAG", "3 - 8 Weeks", "Custom AI chatbots, FAQ/KB, human handoff, analytics", IMG_AI],
    ["Generative AI Development", "Enterprise AI & GenAI", "INR 1.5 Lakh - 8 Lakh", "OpenAI, LangChain, RAG, Python", "4 - 10 Weeks", "LLM apps, agents, private RAG, evaluation and guardrails", IMG_AI],
    ["WhatsApp Business API Integration", "Communications", "INR 25,000 - 1.5 Lakh", "Meta Cloud API, templates, webhooks", "2 - 6 Weeks", "Green-tick setup, bots, broadcasts, CRM sync", IMG_LOGO],
    ["CPaaS / Omnichannel Messaging", "Communications", "Pay per use / Platform plan", "SMS, Email, WhatsApp, IVR, Push", "2 - 8 Weeks", "Unified messaging APIs, campaigns, delivery reports (120+ projects)", IMG_LOGO],
    ["Enterprise Software Development", "Software Engineering", "INR 3 Lakh - 25 Lakh", "Node, Python, .NET, microservices", "8 - 24 Weeks", "Custom enterprise apps, workflows, SSO, audit trails", IMG_LOGO],
    ["Web & Mobile App Development", "Product Engineering", "INR 1 Lakh - 12 Lakh", "React, Next.js, Flutter, React Native", "6 - 16 Weeks", "Portals, iOS and Android apps, push, offline (60+ apps)", IMG_LOGO],
    ["Digital Growth & Marketing", "Growth", "Campaign / retainer", "SEO, content, analytics", "Ongoing", "Technical SEO, growth marketing, authority building (200+ campaigns)", IMG_LOGO],
    ["Enterprise Hosting & Security", "Cloud & Security", "From INR 50,000 / month", "Hosting, SSL, audits, monitoring", "Ongoing", "Pen-testing, encryption, 24/7 monitoring, compliance (0 breaches)", IMG_ISO],
]

MENU = [
    ["Button Title (<=24ch)", "Description (<=72ch)", "Section", "Action"],
    ["Our Services", "AI, software, web, mobile & CPaaS", "Services", "offerings"],
    ["Technologies", "React, Python, Flutter, cloud & AI", "Services", "technologies"],
    ["Projects", "Clients, portfolio & industries served", "Company", "projects"],
    ["Service Brochure", "Download our capability brochure", "Company", "brochure_request"],
    ["Careers", "Open roles & how to apply", "Company", "careers"],
    ["Benefits", "Why 1500+ clients choose Leeway", "Company", "benefits"],
    ["Get a Quote", "Share scope for a written estimate", "Talk To Us", "quote"],
    ["Book a Callback", "Have our team call you back", "Talk To Us", "book_callback"],
    ["Support", "Existing client support tickets", "Talk To Us", "raise_ticket"],
    ["Talk to Human", "Chat with a Leeway specialist", "Talk To Us", "book_callback"],
]

BRAND = [
    ["Parameter", "Description", "Value / Client Input"],
    ["Brand / Company Name", "Legal trading name", "Leeway Softech Private Limited"],
    ["Display Name", "Shown in admin and bot", "Leeway Softech"],
    ["Bot Name", "WhatsApp assistant name", "Leeway Tech Advisor"],
    ["Tagline", "Short brand line", "Innovative Technology. Creative Work. Trusted Delivery."],
    ["Website", "Public site", "https://leewaysoftech.com"],
    ["Support Email", "Sales / support inbox", "sales@leewaysoftech.com"],
    ["Support Phone", "E.164 with country code", "+91 8690783030"],
    ["Secondary Phone", "Support line", "+91 8000305305"],
    ["Vertical", "Must be it_software", "it_software"],
    ["Business Hours", "Local operating hours", "09:30 AM - 07:00 PM (Mon-Sat); Support focus 24/7"],
    ["Timezone", "IANA timezone", "Asia/Kolkata"],
    ["HQ Address", "Corporate office", "A 502, Rustomjee Central Park, Andheri (E), Mumbai 400059"],
    ["Registered Office", "Legal address", "306, Swara Parklane, Aatabhai Chowk, Bhavnagar 364002"],
    ["CIN", "Company identity", "U72900GJ2012PTC071245"],
    ["Certifications", "Trust signals", "ISO 9001:2015, ISO/IEC 27001:2013, CMMI Level 3"],
    ["Signature", "Message footer", "Leeway Softech — At your service."],
]

FAQS = [
    ["Customer Question", "Official Verified Answer", "Category"],
    ["What services does Leeway Softech provide?", "AI development, custom/enterprise software, SaaS, data engineering & BI, CPaaS (SMS, Email, WhatsApp, IVR), web & mobile apps, UI/UX, cloud/DevOps, and digital transformation.", "Services"],
    ["Is Leeway Softech an AI development company?", "Yes — Generative AI, AI chatbots, machine learning, computer vision, and AI automation for business processes.", "AI"],
    ["Do you build WhatsApp Business API solutions?", "Yes. We integrate Meta WhatsApp Business API for support bots, notifications, and broadcasts, including CRM/website sync.", "WhatsApp"],
    ["What is CPaaS and do you offer it?", "Communications Platform as a Service — messaging/voice via APIs. We offer CPaaS, SMS gateway, omnichannel, push, and bulk email.", "Platforms"],
    ["Which industries do you serve?", "Government & public sector, banking & financial services, education, hospitality, enterprise/corporate, politics, and retail/e-commerce.", "Industries"],
    ["Where is Leeway Softech based?", "Founded 2012. Corporate office Mumbai; registered office Bhavnagar; branches in Delhi/NCR (Noida) and Ahmedabad.", "Company"],
    ["How do I contact sales or support?", "Sales: sales@leewaysoftech.com · Consultation +91 8690783030 · Support +91 8000305305. Typical reply under 2 hours.", "Contact"],
    ["Which certifications does Leeway hold?", "ISO 9001:2015, ISO/IEC 27001:2013, and CMMI Level 3.", "Compliance"],
    ["Do you sign an NDA before discussions?", "Yes. Mutual NDAs before reviewing confidential architecture, code, or roadmaps.", "Security"],
    ["Who owns the intellectual property (IP)?", "Clients own 100% of custom source code, designs, and project data after agreed milestone payments (OSS keeps its licenses).", "IP"],
]

INFO = [
    ["Page / Intent ID", "Bot Answer (summary)", "Keywords"],
    ["technologies", "Frontend: React/Next/Vue/Angular. Backend: Node/Python/Golang/.NET. AI: OpenAI, LangChain, PyTorch. Mobile: Flutter/RN. Cloud: AWS/Azure/GCP.", "technologies, tech stack, react, python, flutter, aws"],
    ["projects", "1500+ clients · 14 years · Tata Tele, BHEL, Powergrid, Bandhan Bank, Club Mahindra, AAI, Railways, Lodha. MoU with Govt of Gujarat for AI.", "projects, portfolio, case study, clients, our work"],
    ["careers", "Hiring across sales, QA, design, support. Apply https://leewaysoftech.com/careers with PDF resume (max 2 MB).", "careers, job, hiring, vacancy, internship"],
    ["benefits", "ISO/CMMI certified, 1500+ clients, Gujarat AI MoU, end-to-end from CPaaS to full software builds, NDA/IP-friendly.", "benefits, why choose, advantages, differentiators"],
]

GUARD = [
    ["Guardrail", "Description", "Value"],
    ["Tone", "Professional, clear, confident — no hype", "professional"],
    ["Never invent pricing", "Only quote ranges from catalog or offer a callback", "true"],
    ["Never share OTPs / secrets", "Escalate security questions to human", "true"],
    ["Escalate keywords", "Words that force handoff", "fraud, lawsuit, data breach, urgent outage"],
    ["Forbidden terms", "Avoid cart/checkout language", "add to cart, buy now, checkout"],
    ["Escalation message", "Shown on handoff", "Connecting you to a Leeway specialist now."],
    ["Greeting hint", "First message style", "Welcome to Leeway Softech — how can we help today?"],
]

DOMAIN = [
    ["Domain Field", "Why we need it", "Your Answer"],
    ["Primary industries", "Sectors you serve", "Government, BFSI, Education, Hospitality, Enterprise"],
    ["Core capabilities", "Keywords for classifier", "AI, software, CPaaS, WhatsApp API, web, mobile, cloud"],
    ["Lead context", "What sales needs", "Use case, timeline, budget band, existing stack"],
    ["Delivery model", "How you engage", "Fixed-price, T&M, dedicated pods, retainers"],
]

KB = [
    ["Knowledge Article Title", "Category", "Article Content"],
    [
        "Company Overview & Trust Signals",
        "Company",
        "Leeway Softech Pvt Ltd founded 2012. Tagline: Innovative Technology. Creative Work. Trusted Delivery. "
        "Contacts: sales@leewaysoftech.com · +91 8690783030 · +91 8000305305. Web: https://leewaysoftech.com. "
        "CIN U72900GJ2012PTC071245. Certifications: ISO 9001:2015, ISO/IEC 27001:2013, CMMI Level 3. "
        "Offices: Mumbai, Bhavnagar, Delhi/NCR, Ahmedabad. Impact: 1500+ clients, 14 years, 120+ CPaaS, 60+ apps, 45+ AI.",
    ],
    [
        "Services Map — AI, Software, CPaaS & Cloud",
        "Services",
        "1) Communication & CPaaS 2) AI & Emerging Technology 3) Custom Software & SaaS 4) Web & Mobile "
        "5) Data & Analytics 6) Cloud & DevOps 7) UI/UX. Ask for a scoped quote with use case and timeline.",
    ],
    [
        "Engagement, NDA, IP & Support",
        "Delivery",
        "Understand → Plan → Build → Integrate → Test & Deploy → Improve. Models: fixed-price, T&M, dedicated pods. "
        "Mutual NDA before deep reviews. Client owns custom IP after milestone settlement. Warranty + optional SLA.",
    ],
    [
        "Offices, Hours & Escalation",
        "Contact",
        "Hours 09:30–19:00 Mon–Sat IST; monitoring emphasis 24/7. Mumbai · Bhavnagar · Noida · Ahmedabad. "
        "For urgent issues ask for a human agent — never share OTPs or passwords on chat.",
    ],
]


def ensure_pngs() -> dict[str, Path]:
    PNG_DIR.mkdir(parents=True, exist_ok=True)
    sources = {
        "logo.png": ("logo.webp", (360, 120)),
        "robot.png": ("roboatImage.webp", (320, 480)),
        "iso9001.png": ("iso9001.webp", (120, 120)),
        "iso27001.png": ("iso27001.webp", (120, 120)),
        "cmmi.png": ("cmmi.webp", (120, 120)),
        "client_tata.png": ("tatatele.webp", (140, 80)),
        "client_bhel.png": ("bhel.webp", (140, 80)),
        "client_bandhan.png": ("bandhanbank.webp", (140, 80)),
        "client_powergrid.png": ("powergrid.webp", (140, 80)),
        "client_mahindra.png": ("Club-Mahindra.webp", (140, 80)),
        "client_lodha.png": ("lodha.webp", (140, 80)),
        "client_aai.png": ("Airports_Authority.webp", (140, 80)),
    }
    out: dict[str, Path] = {}
    for dest_name, (src_name, size) in sources.items():
        src = ASSETS / src_name
        dest = PNG_DIR / dest_name
        if not src.exists():
            print(f"  [WARN] missing {src}")
            continue
        im = PILImage.open(src).convert("RGBA")
        bg = PILImage.new("RGBA", im.size, (255, 255, 255, 255))
        bg.alpha_composite(im)
        rgb = bg.convert("RGB")
        rgb.thumbnail(size, PILImage.Resampling.LANCZOS)
        rgb.save(dest, "PNG", optimize=True)
        out[dest_name] = dest
    return out


def styles():
    base = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle(
            "cover_title", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=26, textColor=colors.white, leading=32, alignment=TA_LEFT,
        ),
        "cover_sub": ParagraphStyle(
            "cover_sub", parent=base["Normal"], fontName="Helvetica",
            fontSize=11, textColor=colors.Color(0.75, 0.82, 0.9), leading=15,
        ),
        "h1": ParagraphStyle(
            "h1", parent=base["Heading1"], fontName="Helvetica-Bold",
            fontSize=13, textColor=NAVY, spaceBefore=8, spaceAfter=6,
        ),
        "h1_teal": ParagraphStyle(
            "h1_teal", parent=base["Heading1"], fontName="Helvetica-Bold",
            fontSize=13, textColor=TEAL, spaceBefore=8, spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"], fontName="Helvetica",
            fontSize=8.5, textColor=MUTED, leading=11, spaceAfter=6,
        ),
        "cell": ParagraphStyle(
            "cell", parent=base["Normal"], fontName="Helvetica",
            fontSize=6.5, textColor=colors.Color(0.12, 0.16, 0.23), leading=8,
        ),
        "cell_h": ParagraphStyle(
            "cell_h", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=6.5, textColor=colors.white, leading=8,
        ),
        "chip": ParagraphStyle(
            "chip", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=12, textColor=colors.white, alignment=TA_CENTER,
        ),
        "chip_l": ParagraphStyle(
            "chip_l", parent=base["Normal"], fontName="Helvetica",
            fontSize=7, textColor=colors.Color(0.75, 0.82, 0.9), alignment=TA_CENTER,
        ),
    }


def pcells(rows, style, header_style):
    out = []
    for i, row in enumerate(rows):
        st = header_style if i == 0 else style
        out.append([Paragraph(str(c).replace("\n", "<br/>"), st) for c in row])
    return out


def styled_table(rows, col_widths, header_color=NAVY):
    s = styles()
    data = pcells(rows, s["cell"], s["cell_h"])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), header_color),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.Color(0.80, 0.84, 0.88)),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return t


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(LIGHT)
    canvas.rect(0, 0, A4[0], 16 * mm, fill=1, stroke=0)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(
        18 * mm,
        7 * mm,
        "Leeway Softech Pvt Ltd  ·  CIN U72900GJ2012PTC071245  ·  https://leewaysoftech.com",
    )
    canvas.drawRightString(A4[0] - 18 * mm, 7 * mm, f"{doc.page}")
    canvas.restoreState()


def cover_page(imgs: dict[str, Path], story, s):
    logo = Image(str(imgs["logo.png"]), width=70 * mm, height=22 * mm) if "logo.png" in imgs else Spacer(1, 20)
    robot = Image(str(imgs["robot.png"]), width=55 * mm, height=85 * mm) if "robot.png" in imgs else Spacer(1, 20)

    left = [
        Paragraph("IT / SOFTWARE", ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=10, textColor=TEAL)),
        Spacer(1, 6),
        Paragraph("AI WhatsApp Chatbot<br/>Onboarding Kit", s["cover_title"]),
        Spacer(1, 8),
        Paragraph("Innovative Technology. Creative Work. Trusted Delivery.", s["cover_sub"]),
        Spacer(1, 6),
        Paragraph("Filled example for Leeway Softech · vertical: it_software", s["cover_sub"]),
        Spacer(1, 14),
        # Plain paragraphs (not a table) so find_tables never invents a "Clients" offering.
        Paragraph("<font color='white'><b>1500+</b> clients · <b>14</b> years · <b>45+</b> AI solutions · <b>60+</b> apps</font>", s["cover_sub"]),
    ]

    hero = Table([[left, robot]], colWidths=[105 * mm, 60 * mm])
    hero.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 24),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 24),
            ]
        )
    )
    story.append(logo)
    story.append(Spacer(1, 8))
    story.append(hero)
    story.append(PageBreak())


def build() -> Path:
    imgs = ensure_pngs()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    EXAMPLES.mkdir(parents=True, exist_ok=True)
    s = styles()

    doc = SimpleDocTemplate(
        str(OUT_PDF),
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=20 * mm,
        title="Leeway Softech — IT/Software WhatsApp Onboarding Kit",
        author="Leeway Softech",
    )
    story = []
    cover_page(imgs, story, s)

    # Brand
    story.append(Paragraph("[SECTION: BRAND & PROFILE]", s["h1"]))
    story.append(Paragraph("Company profile for Leeway Softech — sourced from https://leewaysoftech.com/", s["body"]))
    certs = []
    for key, w in (("logo.png", 45 * mm), ("iso9001.png", 18 * mm), ("iso27001.png", 18 * mm), ("cmmi.png", 18 * mm)):
        if key in imgs:
            certs.append(Image(str(imgs[key]), width=w, height=18 * mm if key != "logo.png" else 14 * mm))
    if certs:
        story.append(Table([certs], colWidths=[50 * mm, 22 * mm, 22 * mm, 22 * mm]))
        story.append(Spacer(1, 6))
    story.append(styled_table(BRAND, [38 * mm, 48 * mm, 92 * mm], NAVY))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Trusted by industry leaders", s["body"]))
    clients = []
    for key in (
        "client_tata.png",
        "client_bhel.png",
        "client_bandhan.png",
        "client_powergrid.png",
        "client_mahindra.png",
        "client_lodha.png",
        "client_aai.png",
    ):
        if key in imgs:
            clients.append(Image(str(imgs[key]), width=22 * mm, height=12 * mm))
    if clients:
        # Single row of images only — no text cells that confuse catalog extractors.
        logo_row = Table([clients], colWidths=[24 * mm] * len(clients))
        logo_row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        story.append(logo_row)
    story.append(PageBreak())

    # Menu + operations
    story.append(Paragraph("[SECTION: WHATSAPP MENU]", s["h1"]))
    story.append(Paragraph("WhatsApp interactive list — titles &lt;=24 chars, descriptions &lt;=72 chars.", s["body"]))
    story.append(styled_table(MENU, [40 * mm, 72 * mm, 32 * mm, 34 * mm], NAVY))
    story.append(Spacer(1, 10))
    story.append(Paragraph("[SECTION: OPERATIONS & DOMAIN]", s["h1_teal"]))
    story.append(styled_table(DOMAIN, [40 * mm, 50 * mm, 88 * mm], TEAL))
    story.append(PageBreak())

    # Catalog
    story.append(Paragraph("[SECTION: CATALOG & OFFERINGS]", s["h1_teal"]))
    story.append(Paragraph(
        "Service catalog with public Image URL values from leewaysoftech.com. "
        "Embedded previews follow so PDF image attach can map offerings.",
        s["body"],
    ))
    # Single parser table. Image URL cells are plain strings at 4pt so they
    # stay on one line — Paragraph wrap inserts newlines that break URLs.
    parse_header = ["Service / Offering", "Category", "Starting Price / Model", "Scope & Deliverables", "Image URL"]
    parse_data = [[Paragraph(h, s["cell_h"]) for h in parse_header]]
    for row in OFFERINGS[1:]:
        scope = f"{row[5]} | Stack: {row[3]} | Timeline: {row[4]}"
        parse_data.append(
            [
                Paragraph(row[0], s["cell"]),
                Paragraph(row[1], s["cell"]),
                Paragraph(row[2], s["cell"]),
                Paragraph(scope, s["cell"]),
                row[6],  # plain string — no mid-URL wrap
            ]
        )
    catalog = Table(parse_data, colWidths=[32 * mm, 24 * mm, 28 * mm, 36 * mm, 58 * mm], repeatRows=1)
    catalog.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), TEAL),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.Color(0.80, 0.84, 0.88)),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTNAME", (4, 1), (4, -1), "Helvetica"),
                ("FONTSIZE", (4, 1), (4, -1), 4.5),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(catalog)
    story.append(PageBreak())

    # Embedded previews WITHOUT nested tables (avoids false catalog rows for find_tables).
    story.append(Paragraph("Catalog images (embedded preview)", s["h1_teal"]))
    story.append(Paragraph(
        "Each offering name below is paired with a Leeway website image for PDF media attach.",
        s["body"],
    ))
    for row in OFFERINGS[1:]:
        name, category, price = row[0], row[1], row[2]
        img_path = imgs.get("robot.png") if "AI" in name or "Generative" in name else imgs.get("logo.png")
        if "Hosting" in name or "Security" in name:
            img_path = imgs.get("iso27001.png") or img_path
        story.append(Paragraph(f"<b>{name}</b> — {category} · {price}", s["cell"]))
        if img_path:
            story.append(Image(str(img_path), width=40 * mm, height=28 * mm))
        story.append(Spacer(1, 6))
    story.append(PageBreak())

    # FAQs
    story.append(Paragraph("[SECTION: FAQS & POLICIES]", s["h1"]))
    story.append(styled_table(FAQS, [48 * mm, 100 * mm, 30 * mm], colors.Color(0.26, 0.22, 0.79)))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Knowledge Base Articles (indexed for chatbot retrieval)", s["h1"]))
    story.append(styled_table(KB, [42 * mm, 24 * mm, 112 * mm], colors.Color(0.19, 0.18, 0.51)))
    story.append(PageBreak())

    # Info pages
    story.append(Paragraph("[SECTION: INFO PAGES & INTENTS]", s["h1"]))
    story.append(Paragraph("IT-only pages: Technologies / Projects / Careers / Benefits.", s["body"]))
    story.append(styled_table(INFO, [30 * mm, 110 * mm, 38 * mm], colors.Color(0.15, 0.55, 0.72)))
    story.append(PageBreak())

    # Guardrails
    story.append(Paragraph("[SECTION: BOT PERSONA & GUARDRAILS]", s["h1"]))
    story.append(styled_table(GUARD, [40 * mm, 80 * mm, 58 * mm], colors.Color(0.45, 0.18, 0.22)))

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    shutil.copy2(OUT_PDF, EXAMPLE_PDF)
    shutil.copy2(OUT_PDF, PRETTY)
    print(f"Wrote {OUT_PDF} ({OUT_PDF.stat().st_size:,} bytes)")
    print(f"Copied {EXAMPLE_PDF}")
    print(f"Copied {PRETTY}")
    return OUT_PDF


if __name__ == "__main__":
    build()
    print("Verify with: python reports/_verify_leeway_pdf.py")
