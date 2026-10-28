"""Complete universal + vertical domain fields for every onboarding kit.

Merged on top of COMPANY_EXAMPLES so generated DOCX/PDF kits leave nothing out:
brand, WhatsApp, hours, notifications, vocabulary, features, domain answers,
guardrails. Catalog / menu / FAQ / info_pages still come from company examples.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

# domain_answers: list of (label, description, filled_example)
DomainRow = Tuple[str, str, str]


def _voc(
    item: str,
    singular: str,
    browse: str,
    brochure: str,
    lead: str,
    enquire: str,
    support: str = "Support",
) -> Dict[str, str]:
    return {
        "item_noun": item,
        "item_noun_singular": singular,
        "browse_label": browse,
        "brochure_label": brochure,
        "lead_noun": lead,
        "enquiry_label": enquire,
        "support_label": support,
    }


PROFILE_OVERLAYS: Dict[str, Dict[str, Any]] = {
    # ── Software & IT (Leeway Softech) ─────────────────────────────────────
    "it_software": {
        "legal_name": "Leeway Softech Private Limited",
        "display_name": "Leeway Softech",
        "logo_url": "https://leewaysoftech.com/assets/logo.png",
        "signature": "Leeway Softech — Building software that moves business forward.",
        "greeting": "Welcome to Leeway Softech! Ask about services, tech stack, projects, careers — or request a quote / callback.",
        "sales_email": "sales@leewaysoftech.com",
        "notifications_support_email": "support@leewaysoftech.com",
        "brochure_url": "https://leewaysoftech.com/company-profile.pdf",
        "brochure_label": "Company Profile",
        "waba_phone": "+91 8690783030",
        "timezone": "Asia/Kolkata",
        "always_open": False,
        "open_time": "09:30",
        "close_time": "19:00",
        "open_days": "Mon–Sat (closed Sunday)",
        "out_of_hours_message": (
            "We are outside working hours (Mon–Sat 09:30–19:00 IST). "
            "Leave your name, phone and project summary — sales will call you next working day."
        ),
        "tone": "professional and confident",
        "vocabulary": _voc(
            "services", "service", "Our Services", "Service Brochure", "enquiry", "Enquire", "Raise Ticket"
        ),
        "features_enabled": [
            "offerings", "offering_details", "services", "brochure_pdf",
            "lead_capture", "quote", "callback", "book_appointment",
            "faq", "kb", "complaints", "handoff", "human_handover",
        ],
        "features_disabled": [
            "cart", "buy_now", "orders", "payments", "track_order", "returns",
            "distributors", "products", "products_schemes", "campaigns",
        ],
        "domain_answers": [
            ("Technologies / tech stack", "Chips the bot understands", "React, Next.js, Node.js, Python, Flutter, AWS, Azure, GCP, AI/ML, DevOps"),
            ("Engagement models", "How you contract", "Mixed — Fixed-price, Time & materials, Dedicated pods / retainers"),
            ("Typical engagement size", "Budget framing for quotes", "Projects from ₹75,000 · dedicated pods from ₹1.8 Lakh/month"),
            ("After-sales / AMC / SLA", "Post go-live support", "60-day defect warranty; optional SLA retainers for monitoring, patches & feature velocity"),
            ("Certifications", "Trust signals", "ISO 9001:2015, ISO/IEC 27001:2013, CMMI Level 3"),
            ("Offices", "Locations shown on Benefits", "Mumbai (corporate), Bhavnagar (registered), Delhi/NCR, Ahmedabad"),
            ("Founded / scale", "Credibility stats", "Founded 2012 · 1500+ clients · AI MoU with Government of Gujarat"),
        ],
        "never_state": [
            "unconfirmed project prices", "guaranteed delivery dates without SOW",
            "client names without permission", "discounts not approved by sales",
            "security certifications you do not hold",
        ],
        "forbidden_terms": ["OTP", "password", "share card details", "wire transfer to personal account"],
        "escalate_keywords": ["fraud", "legal", "lawsuit", "urgent", "complaint", "breach", "data leak"],
        "handoff_keywords": ["human", "agent", "person", "manager", "call me", "speak to someone"],
        "escalation_message": "This needs a human — connecting you with our team now. A specialist will follow up shortly.",
    },
    # ── E-commerce (TrooGood) ──────────────────────────────────────────────
    "ecommerce": {
        "legal_name": "TrooGood Foods Private Limited",
        "display_name": "TrooGood",
        "logo_url": "https://www.troogood.com/logo.png",
        "signature": "TrooGood — Homemade-style chikki, delivered fresh.",
        "greeting": "Hi! Browse TrooGood chikki & snacks, track an order, or ask about delivery & returns.",
        "sales_email": "orders@troogood.com",
        "notifications_support_email": "support@troogood.com",
        "brochure_url": "https://www.troogood.com/catalogue.pdf",
        "brochure_label": "Product Catalogue",
        "waba_phone": "+91 1234567891",
        "timezone": "Asia/Kolkata",
        "always_open": True,
        "open_time": "09:00",
        "close_time": "21:00",
        "open_days": "All days (bot 24/7; warehouse Mon–Sat)",
        "out_of_hours_message": "Our warehouse team is offline. Leave Order ID + issue — we reply next working morning.",
        "tone": "friendly and helpful",
        "vocabulary": _voc(
            "products", "product", "Browse Products", "View Brochure", "enquiry", "Enquire", "Support"
        ),
        "features_enabled": [
            "cart", "buy_now", "orders", "track_order", "returns", "payments",
            "offerings", "offering_details", "products", "brochure_pdf",
            "faq", "kb", "complaints", "handoff", "human_handover",
        ],
        "features_disabled": [
            "distributors", "services", "products_schemes", "lead_capture",
            "quote", "callback", "book_appointment", "campaigns",
        ],
        "domain_answers": [
            ("Product categories", "Menu sections / classifier", "Chikki, Healthy Snacks, Dry Fruit Bars, Gift Packs, Grocery"),
            ("Payment methods", "Checkout options", "UPI, Card, Net banking, Cash on delivery (eligible PIN codes)"),
            ("Delivery & returns (one line)", "Policy summary", "Metro 2–3 days · Free delivery above ₹499 · 7-day easy returns"),
            ("Order reference prefix", "Order IDs look like", "TG"),
            ("Courier partners", "Tracking partners", "BlueDart, Xpressbees, Delhivery"),
            ("Refund timeline", "After QC", "5–7 business days to original payment method (COD → UPI/bank)"),
            ("Warranty / quality", "Per SKU defaults", "Manufacturing defects covered; sealed food items non-returnable once opened"),
        ],
        "never_state": [
            "out-of-stock items as available", "delivery dates for remote PIN without check",
            "unauthorized discount codes", "COD on restricted high-value SKUs",
        ],
        "forbidden_terms": ["OTP", "CVV", "full card number", "UPI PIN"],
        "escalate_keywords": ["fraud", "chargeback", "legal", "food poisoning", "allergen", "urgent"],
        "handoff_keywords": ["human", "agent", "person", "manager", "complaint"],
        "escalation_message": "Connecting you with TrooGood support. Keep your Order ID ready.",
    },
    # ── Real estate (Skyline) ──────────────────────────────────────────────
    "real_estate": {
        "legal_name": "Skyline Realty & Developers Private Limited",
        "display_name": "Skyline Realty & Developers",
        "logo_url": "https://www.skylinerealty.com/logo.png",
        "signature": "Skyline Realty — Homes & workspaces with lasting value.",
        "greeting": "Welcome to Skyline Realty! Explore residences, villas & commercial spaces, or book a site visit.",
        "sales_email": "sales@skylinerealty.com",
        "notifications_support_email": "care@skylinerealty.com",
        "brochure_url": "https://www.skylinerealty.com/brochures/master.pdf",
        "brochure_label": "Project Brochure",
        "waba_phone": "+91 98765 43210",
        "timezone": "Asia/Kolkata",
        "always_open": False,
        "open_time": "09:30",
        "close_time": "19:00",
        "open_days": "Mon–Sat",
        "out_of_hours_message": "Sales lounge is closed. Share name, phone, preferred project & city — we schedule a call or site visit next working day.",
        "tone": "reassuring, consultative, and knowledgeable",
        "vocabulary": _voc(
            "properties", "property", "Featured Properties", "Project Brochure",
            "site visit request", "Schedule Site Visit", "Customer Support",
        ),
        "features_enabled": [
            "offerings", "offering_details", "brochure_pdf",
            "lead_capture", "quote", "callback", "book_appointment",
            "faq", "kb", "complaints", "handoff", "human_handover",
        ],
        "features_disabled": [
            "cart", "buy_now", "orders", "payments", "track_order", "returns",
            "distributors", "services", "products", "products_schemes", "campaigns",
        ],
        "domain_answers": [
            ("Property types", "Inventory focus", "2/3 BHK Apartments, Luxury Penthouses, Villas, Commercial Offices, Plots"),
            ("RERA registration", "Compliance IDs", "Per-project RERA IDs listed in catalog (e.g. PR/GJ/AHMEDABAD/RAA09876/2024)"),
            ("Site visit rules", "Booking logistics", "Complimentary AC cab within city · Tue–Sun slots · sales executive assigned on confirmation"),
            ("Booking advance", "Token to lock unit", "₹2,00,000 typical (project-specific; confirm on cost sheet)"),
            ("Home loan partners", "Banks", "SBI, HDFC, ICICI, Axis, Kotak — up to 80–90% of agreement value"),
            ("NRI purchase", "Policy", "Yes via NRE/NRO with documentation desk support"),
            ("Possession / OC", "Handover", "Ready / under-construction dates in catalog; OC & snag checklist at possession"),
        ],
        "never_state": [
            "guaranteed appreciation / returns", "inventory locked without booking",
            "RERA numbers not on the official list", "final carpet area different from RERA drawings",
            "loan sanction without bank underwriting",
        ],
        "forbidden_terms": ["OTP", "password", "pay to personal UPI", "black money"],
        "escalate_keywords": ["fraud", "legal", "RERA complaint", "dispute", "urgent", "police"],
        "handoff_keywords": ["human", "agent", "sales manager", "site visit now"],
        "escalation_message": "Connecting you with a Skyline sales advisor for personalised guidance.",
    },
    # ── Tours & travel (99 Destinations) ───────────────────────────────────
    "tours_travel": {
        "legal_name": "99 Destinations Holidays Private Limited",
        "display_name": "99 Destinations",
        "logo_url": "https://www.99destinations.in/logo.png",
        "signature": "99 Destinations — Recognised by Gujarat Tourism (TCGL).",
        "greeting": "Namaste! Explore holiday packages, visas & custom itineraries — or speak to a travel expert.",
        "sales_email": "bookings@99destinations.in",
        "notifications_support_email": "info@99destinations.in",
        "brochure_url": "https://www.99destinations.in/packages.pdf",
        "brochure_label": "Trip Brochure",
        "waba_phone": "+91 7874833999",
        "timezone": "Asia/Kolkata",
        "always_open": False,
        "open_time": "10:30",
        "close_time": "19:30",
        "open_days": "Mon–Sat",
        "out_of_hours_message": "Travel desk is closed. Share destination, dates, travellers & budget — we reply next working day with options.",
        "tone": "warm and helpful",
        "vocabulary": _voc(
            "packages", "package", "Explore Packages", "Trip Brochure",
            "booking enquiry", "Enquire", "Travel Support",
        ),
        "features_enabled": [
            "offerings", "offering_details", "brochure_pdf",
            "lead_capture", "book_appointment", "callback", "quote",
            "faq", "kb", "complaints", "handoff", "human_handover",
        ],
        "features_disabled": [
            "cart", "buy_now", "orders", "payments", "track_order", "returns",
            "distributors", "services", "products", "products_schemes", "campaigns",
        ],
        "domain_answers": [
            ("Destinations", "Where you sell", "Gujarat, Kutch, Gir, Statue of Unity, Kashmir, Goa, Rajasthan, Dubai, Bali, Europe"),
            ("Trip types", "Audience", "Honeymoon, Family, Group, Adventure, Corporate, Pilgrimage, Solo"),
            ("Booking & cancellation", "Policy summary", "Token to confirm · 21+ days ~90% refund on land package · inside 7 days largely non-refundable (supplier rules)"),
            ("Seasonality", "Peak windows", "Oct–Mar peak for Gujarat / Rann; international varies by destination"),
            ("Flights in package?", "Default", "Land-only or with flights — choose at quote time"),
            ("Visa assistance", "Service", "Document vetting, appointments, tracking — approval is consulate discretion"),
            ("Emergency on trip", "Support", "Destination duty phone shared on voucher"),
        ],
        "never_state": [
            "visa approval guarantees", "airline schedule locks without PNR",
            "prices excluding mandatory taxes when quoted all-in",
            "weather guarantees",
        ],
        "forbidden_terms": ["OTP", "passport password", "pay to personal account"],
        "escalate_keywords": ["stranded", "medical emergency", "lost passport", "fraud", "legal", "urgent"],
        "handoff_keywords": ["human", "agent", "travel expert", "manager"],
        "escalation_message": "Connecting you with a 99 Destinations travel expert now.",
    },
    # ── Healthcare (CareWell) ──────────────────────────────────────────────
    "healthcare": {
        "legal_name": "CareWell Multi-Specialty Clinic Private Limited",
        "display_name": "CareWell Multi-Specialty Clinic",
        "logo_url": "https://www.carewellclinic.example/logo.png",
        "signature": "CareWell — Compassionate care, clear guidance.",
        "greeting": "Welcome to CareWell. Book appointments, check departments & timings — for emergencies call our 24×7 helpline.",
        "sales_email": "appointments@carewellclinic.example",
        "notifications_support_email": "care@carewellclinic.example",
        "brochure_url": "https://www.carewellclinic.example/services.pdf",
        "brochure_label": "Services List",
        "waba_phone": "+91 9988776655",
        "timezone": "Asia/Kolkata",
        "always_open": False,
        "open_time": "08:00",
        "close_time": "20:30",
        "open_days": "Mon–Sat · Emergency desk 24/7",
        "out_of_hours_message": "OPD is closed. For emergencies call +91 9988776655. For appointments, leave name, phone, department — reception books next day.",
        "tone": "calm and empathetic",
        "vocabulary": _voc(
            "departments", "department", "Our Departments", "Services List",
            "appointment request", "Book Appointment", "Patient Support",
        ),
        "features_enabled": [
            "offerings", "offering_details", "brochure_pdf",
            "lead_capture", "book_appointment", "callback",
            "faq", "kb", "complaints", "handoff", "human_handover",
        ],
        "features_disabled": [
            "cart", "buy_now", "orders", "payments", "track_order", "returns",
            "distributors", "services", "products", "products_schemes", "campaigns", "quote",
        ],
        "domain_answers": [
            ("Departments", "OPD list", "Cardiology, Orthopaedics, Paediatrics, Dermatology, General Medicine, Diagnostics, Dental"),
            ("Triage / escalation rule (REQUIRED)", "Bot must never diagnose", "Never diagnose or prescribe. Emergencies → show helpline +91 9988776655 and escalate to reception immediately."),
            ("Emergency / ambulance", "24×7", "+91 9988776655 — share location & patient condition"),
            ("Insurance / cashless", "TPA", "Listed TPAs & corporates; planned procedures need pre-auth"),
            ("Lab reports", "Delivery", "Routine PDF on WhatsApp/email within ~12 hours; specialised 24–48 hours"),
            ("Languages", "Preference matching", "English, Hindi, Gujarati — subject to doctor availability"),
        ],
        "never_state": [
            "diagnosis", "prescription / medicine dosage", "guaranteed cure",
            "lab interpretation as clinical advice", "surgery recommendation without clinician",
        ],
        "forbidden_terms": ["self-medicate", "ignore chest pain", "stop your medicines"],
        "escalate_keywords": ["chest pain", "breathing", "unconscious", "bleeding", "suicide", "emergency", "ambulance"],
        "handoff_keywords": ["human", "doctor", "nurse", "reception", "agent"],
        "escalation_message": "For clinical matters I must connect you with our care team. If this is an emergency, call +91 9988776655 now.",
    },
    # ── Banking (Meridian) ─────────────────────────────────────────────────
    "banking": {
        "legal_name": "Meridian Premier Bank Limited",
        "display_name": "Meridian Bank",
        "logo_url": "https://www.meridianbanker.com/logo.png",
        "signature": "Meridian Bank — Bank of All Banks. (Information only — never share OTP/PIN.)",
        "greeting": "Welcome to Meridian Bank. Ask about accounts, cards, deposits & claims. We never ask for OTP, PIN or passwords here.",
        "sales_email": "sales@meridianbank.com",
        "notifications_support_email": "care@meridianbank.com",
        "brochure_url": "https://www.meridianbanker.com/product-guide.pdf",
        "brochure_label": "Product Brochure",
        "waba_phone": "+91 7418527567",
        "timezone": "Asia/Kolkata",
        "always_open": False,
        "open_time": "09:30",
        "close_time": "17:00",
        "open_days": "Mon–Fri + 1st/3rd/5th Sat · Phone banking 24×7",
        "out_of_hours_message": "Branch hours ended. For card block / fraud use Block Lost Card anytime. Other queries: leave details for next working day.",
        "tone": "formal and compliant",
        "vocabulary": _voc(
            "schemes", "scheme", "Our Products", "Product Brochure", "enquiry", "Enquire", "Customer Care"
        ),
        "features_enabled": [
            "offerings", "offering_details", "products_schemes", "brochure_pdf",
            "lead_capture", "callback", "faq", "kb", "complaints", "handoff", "human_handover",
        ],
        "features_disabled": [
            "cart", "buy_now", "orders", "payments", "track_order", "returns",
            "distributors", "services", "products", "quote", "book_appointment", "campaigns",
        ],
        "domain_answers": [
            ("Products on offer", "Catalogue focus", "Savings, Current, Fixed Deposit, Credit Cards, Home Loans, Personal Loans, Insurance"),
            ("Regulatory note", "How bot must speak", "Information & service requests only. Never execute transfers. Never request OTP/PIN/password. Rates indicative until sanction."),
            ("KYC for savings", "Docs", "Aadhaar, PAN, photograph — Video KYC where eligible"),
            ("Lost card", "Action", "Block via menu/chat with last 4 digits — SMS ack in seconds"),
            ("Branch / IFSC", "Locator", "Ask city or PIN; IFSC also on cheque book / statements"),
            ("Claims", "Insurance path", "Policy number + hospital bills; TPA checklist via Insurance & Claims"),
        ],
        "never_state": [
            "loan approval / sanction", "guaranteed investment returns",
            "account balance without authenticated channel", "ability to transfer money on WhatsApp",
            "interest rates as final without underwriting",
        ],
        "forbidden_terms": ["OTP", "PIN", "MPIN", "CVV", "password", "net banking password"],
        "escalate_keywords": ["fraud", "unauthorized transaction", "legal", "ombudsman", "RBI", "urgent", "phishing"],
        "handoff_keywords": ["human", "agent", "branch manager", "relationship manager"],
        "escalation_message": "For your safety I'm connecting you with Meridian customer care. Never share OTP or PIN on chat.",
    },
    # ── Finance (L&T Finance — loans / advisory products) ──────────────────
    "finance": {
        "legal_name": "L&T Finance Limited",
        "display_name": "L&T Finance",
        "logo_url": "https://www.ltfs.com/logo.png",
        "signature": "L&T Finance — Responsible lending. Clear eligibility guidance.",
        "greeting": "Welcome to L&T Finance. Ask about two-wheeler, personal, gold or home loans — or check eligibility. We never ask for OTP/MPIN here.",
        "sales_email": "care@ltfs.com",
        "notifications_support_email": "grievance@ltfs.com",
        "brochure_url": "https://www.ltfs.com/products.pdf",
        "brochure_label": "Product Guide",
        "waba_phone": "+91 1800 209 0404",
        "timezone": "Asia/Kolkata",
        "always_open": False,
        "open_time": "09:30",
        "close_time": "18:30",
        "open_days": "Mon–Sat",
        "out_of_hours_message": "Advisors are offline. Share product interest, city & contact — we schedule a callback next working day.",
        "tone": "precise and professional",
        "vocabulary": _voc(
            "services", "service", "Our Services", "Product Guide",
            "consultation", "Request a Callback", "Customer Care",
        ),
        "features_enabled": [
            "offerings", "offering_details", "services", "brochure_pdf",
            "lead_capture", "callback", "book_appointment",
            "faq", "kb", "handoff", "human_handover", "complaints",
        ],
        "features_disabled": [
            "cart", "buy_now", "orders", "payments", "track_order", "returns",
            "distributors", "products", "products_schemes", "campaigns", "quote",
        ],
        "domain_answers": [
            ("Services / products offered", "Catalogue focus", "Two-wheeler loans, Personal loans, Gold loans, Home loans / LAP, EV finance"),
            ("Key deadlines / SLAs bot should mention", "Ops cues", "In-principle eligibility in minutes · Personal loan disbursal often ~24h after verification"),
            ("Documents checklist", "KYC / income", "Aadhaar/PAN, salary slips or ITR, bank statements — product-specific list on request"),
            ("Rate guidance rule", "Compliance", "Published rates are indicative only; final rate after credit assessment"),
            ("Grievance path", "Escalation", "Raise Complaint in menu or customer care — follows published grievance redressal"),
            ("Security rule", "Never ask", "Never share OTP, MPIN, CVV or passwords on chat"),
        ],
        "never_state": [
            "guaranteed loan approval", "final interest rate without underwriting",
            "investment returns", "ability to disburse money inside WhatsApp chat",
        ],
        "forbidden_terms": ["OTP", "MPIN", "CVV", "password", "net banking password"],
        "escalate_keywords": ["fraud", "legal", "ombudsman", "RBI", "urgent", "harassment", "grievance"],
        "handoff_keywords": ["human", "agent", "manager", "relationship manager"],
        "escalation_message": "Connecting you with L&T Finance care. Never share OTP or MPIN on chat.",
    },
    # ── Generic / logistics (Apex) ─────────────────────────────────────────
    "generic": {
        "legal_name": "Apex Global Logistics & Freight Services Private Limited",
        "display_name": "Apex Global Logistics & Freight Services",
        "logo_url": "https://www.apexlogistics.com/logo.png",
        "signature": "Apex Logistics — Seamless freight, clear milestones.",
        "greeting": "Welcome to Apex Logistics. Explore freight services, request a quote, or ask how to share an AWB for status guidance.",
        "sales_email": "sales@apexlogistics.com",
        "notifications_support_email": "care@apexlogistics.com",
        "brochure_url": "https://www.apexlogistics.com/services.pdf",
        "brochure_label": "Service Brochure",
        "waba_phone": "+91 98765 43210",
        "timezone": "Asia/Kolkata",
        "always_open": False,
        "open_time": "09:00",
        "close_time": "18:00",
        "open_days": "Mon–Fri (ops desk extended for active shipments)",
        "out_of_hours_message": "Sales desk is closed. For active shipments share AWB + issue. New quotes: leave origin, destination, weight — we reply next working day.",
        "tone": "helpful",
        "vocabulary": _voc(
            "services", "service", "Explore Services", "Brochure", "enquiry", "Enquire", "Support"
        ),
        "features_enabled": [
            "offerings", "offering_details", "lead_capture", "quote", "callback",
            "faq", "kb", "handoff", "human_handover", "brochure_pdf",
        ],
        "features_disabled": [
            "cart", "buy_now", "orders", "payments", "track_order", "returns",
            "distributors", "services", "products", "products_schemes",
            "book_appointment", "complaints", "campaigns",
        ],
        "domain_answers": [
            ("What you offer", "Catalogue types", "Domestic Express, Air Freight, Ocean FCL/LCL, Warehousing & Fulfilment, Customs coordination"),
            ("Availability", "Coverage", "Pan-India + major international lanes (port-to-port / door-to-door on request)"),
            ("Lead time", "Typical turnaround", "Domestic express 24–48h · Air 2–5 days · Ocean lane-dependent"),
            ("Consignment / AWB format", "Lookup hint", "AWB / consignment ID as issued on booking confirmation (share full ID in chat)"),
            ("Quote inputs needed", "Lead capture", "Origin, destination, weight/CBM, Incoterms, ready date, commodity type"),
            ("Customs", "Scope", "Coordination available; duties/taxes billed as actuals unless DDP quoted"),
        ],
        "never_state": [
            "guaranteed customs clearance times", "fixed ocean rates without validity window",
            "delivery without address verification", "hazardous goods acceptance without DG check",
        ],
        "forbidden_terms": ["OTP", "pay to personal UPI", "undeclared cargo"],
        "escalate_keywords": ["lost shipment", "damage", "fraud", "legal", "urgent", "customs hold"],
        "handoff_keywords": ["human", "agent", "ops manager", "person"],
        "escalation_message": "Connecting you with Apex operations. Keep your AWB ready.",
    },
}


def apply_profile_overlays(configs: Dict[str, Dict[str, Any]]) -> None:
    """Merge complete universal/domain fields into each vertical config."""
    for key, cfg in configs.items():
        overlay = PROFILE_OVERLAYS.get(key) or {}
        for field, value in overlay.items():
            cfg[field] = value
        # Convenience aliases used by older generator code
        if overlay.get("display_name"):
            cfg.setdefault("default_company", overlay["display_name"])
        if overlay.get("legal_name"):
            cfg["legal_name"] = overlay["legal_name"]


def brand_field_rows(config: Dict[str, Any]) -> List[Tuple[str, str, str]]:
    """Every brand / hours / notification field the client must supply."""
    tenant = config.get("default_tenant") or "tenant"
    voc = config.get("vocabulary") or {}
    features_on = ", ".join(config.get("features_enabled") or []) or "(see console)"
    features_off = ", ".join(config.get("features_disabled") or []) or "—"
    return [
        ("Company Legal Name", "Registered entity name", str(config.get("legal_name") or config.get("default_company") or "")),
        ("Brand / Display Name", "Public WhatsApp-facing name", str(config.get("display_name") or config.get("default_company") or "")),
        ("Tenant ID / Code", "Lowercase slug (unique)", str(tenant)),
        ("Industry Vertical", "Must match kit vertical", str(config.get("slug") or "")),
        ("AI Bot Name", "Assistant persona name", str(config.get("default_bot") or "")),
        ("Brand Tagline", "1–2 sentence positioning", str(config.get("tagline") or "")),
        ("Official Website URL", "https homepage", str(config.get("website") or f"https://www.{tenant}.com")),
        ("Logo URL", "Public PNG/JPG (min ~512px)", str(config.get("logo_url") or "")),
        ("Closing Signature", "Sign-off on bot messages", str(config.get("signature") or "")),
        ("Welcome / Greeting Message", "First reply after Hi", str(config.get("greeting") or "")),
        ("Support Email", "Customer care inbox", str(config.get("support_email") or f"support@{tenant}.com")),
        ("Support Phone", "Helpline with country code (+91…)", str(config.get("support_phone") or "")),
        ("Sales / Enquiries Email", "Lead & quote destination", str(config.get("sales_email") or config.get("support_email") or "")),
        ("Notifications Support Email", "Optional second inbox", str(config.get("notifications_support_email") or "")),
        ("Brochure URL", "Downloadable PDF link", str(config.get("brochure_url") or "")),
        ("Brochure Label", "Button / menu wording", str(config.get("brochure_label") or voc.get("brochure_label") or "Brochure")),
        ("WhatsApp Bot Number", "Send2Digital / WABA MSISDN", str(config.get("waba_phone") or "+91 XXXXXXXXXX")),
        ("Timezone", "IANA timezone", str(config.get("timezone") or "Asia/Kolkata")),
        ("Always Open?", "true = ignore open/close window", "Yes" if config.get("always_open") else "No"),
        ("Opens", "HH:MM 24h", str(config.get("open_time") or "09:00")),
        ("Closes", "HH:MM 24h", str(config.get("close_time") or "18:00")),
        ("Open Days", "Weekday pattern", str(config.get("open_days") or config.get("default_hours") or "")),
        ("Business Hours (display)", "Human-readable schedule", str(config.get("default_hours") or "")),
        ("Out-of-hours Message", "Fallback when closed", str(config.get("out_of_hours_message") or "")),
        ("Tone / Persona", "Bot voice", str(config.get("tone") or "helpful")),
        ("Vocabulary — plural item", "e.g. products / services / packages", str(voc.get("item_noun") or "")),
        ("Vocabulary — singular item", "e.g. product / service", str(voc.get("item_noun_singular") or "")),
        ("Vocabulary — browse label", "Menu browse title", str(voc.get("browse_label") or "")),
        ("Vocabulary — brochure label", "Brochure CTA", str(voc.get("brochure_label") or "")),
        ("Vocabulary — lead noun", "enquiry / booking / consultation", str(voc.get("lead_noun") or "")),
        ("Vocabulary — enquire button", "Lead CTA label", str(voc.get("enquiry_label") or "")),
        ("Vocabulary — support label", "Support CTA", str(voc.get("support_label") or "Support")),
        ("Features ENABLED", "Capabilities turned on", features_on),
        ("Features DISABLED", "Must stay off for this vertical", features_off),
    ]


def domain_field_rows(config: Dict[str, Any]) -> List[Tuple[str, str, str]]:
    rows = list(config.get("domain_answers") or [])
    return [(str(a), str(b), str(c)) for a, b, c in rows]


def guardrail_field_rows(config: Dict[str, Any]) -> List[Tuple[str, str]]:
    never = config.get("never_state") or []
    forbidden = config.get("forbidden_terms") or []
    escalate = config.get("escalate_keywords") or []
    handoff = config.get("handoff_keywords") or []
    return [
        ("Tone & Persona", str(config.get("tone") or "helpful")),
        ("Welcome Message", str(config.get("greeting") or f"Welcome to {config.get('default_company', 'us')}!")),
        ("Never State (one per line)", "\n".join(f"- {x}" for x in never) or "- (add claims the bot must never invent)"),
        ("Forbidden Terms", ", ".join(forbidden) or "OTP, password, PIN"),
        ("Escalate Keywords", ", ".join(escalate) or "fraud, legal, urgent, complaint"),
        ("Handoff Keywords", ", ".join(handoff) or "human, agent, person, manager"),
        ("Escalation Message", str(config.get("escalation_message") or "Connecting you with our team now.")),
        (
            "Human Escalation Rule",
            "Pause bot and alert humans when handoff/escalate keywords appear or confidence is low.",
        ),
    ]
