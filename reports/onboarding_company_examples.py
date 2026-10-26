"""Real-company example overlays for onboarding kits (one per vertical/tenant).

Each vertical maps to a live client folder under /clients. Catalog rows include
Image URL (public https) plus a local media filename downloaded into
backend/static/templates/onboarding/media/{tenant}/ for embedding in DOCX/PDF.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

# Unsplash source URLs (stable enough for kit demos + WhatsApp media_url samples)
U = "https://images.unsplash.com"

COMPANY_EXAMPLES: Dict[str, Dict[str, Any]] = {
    "real_estate": {
        "default_company": "Skyline Realty & Developers",
        "default_tenant": "skylinerealty",
        "default_bot": "Skyline Property Advisor",
        "default_hours": "09:30 AM - 07:00 PM (Mon-Sat)",
        "tagline": "Premium residential residences, luxury villas & commercial spaces",
        "support_email": "sales@skylinerealty.com",
        "support_phone": "+91 98765 43210",
        "website": "https://www.skylinerealty.com",
        "catalog_columns": [
            "Property Name", "Type", "Configuration", "Carpet Area (sqft)",
            "Price Range", "Location", "Key Amenities", "Possession", "RERA ID", "Image URL",
        ],
        "catalog_rows": [
            [
                "Skyline Elegance", "Apartment", "2 & 3 BHK", "820 - 1,150",
                "₹68 Lakhs - ₹96 Lakhs", "S.G. Highway, Ahmedabad",
                "Clubhouse, Pool, Gym, Landscaped Gardens", "Ready / Dec 2026",
                "PR/GJ/AHMEDABAD/RAA09876/2024",
                f"{U}/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=800&q=80",
                "skyline_elegance.jpg",
            ],
            [
                "Skyline Grandeur", "Luxury Penthouse", "4 BHK Duplex", "2,150 - 3,200",
                "₹1.75 Cr - ₹2.85 Cr", "Sindhu Bhavan Extension",
                "Private Jacuzzi, Terrace Garden, Concierge", "Mar 2027",
                "PR/GJ/AHMEDABAD/RAA11245/2024",
                f"{U}/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=800&q=80",
                "skyline_grandeur.jpg",
            ],
            [
                "Skyline Horizon Tech Park", "Commercial Office", "Grade-A Bare Shell", "2,500 - 25,000",
                "₹95 / sq.ft. (Lease)", "S.G. Highway ORR",
                "100% Power Backup, High-Speed Lifts", "Immediate",
                "PR/GJ/AHMEDABAD/COM/2022",
                f"{U}/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=800&q=80",
                "skyline_horizon.jpg",
            ],
            [
                "Skyline Orchard Green", "Gated Villa", "4 BHK Luxury Villa", "2,850",
                "₹1.95 Cr", "Near Science City",
                "Private Garden, Solar, Clubhouse", "June 2027",
                "PR/GJ/AHMEDABAD/RAA1251/2025",
                f"{U}/photo-1613490493576-7fde63acd811?auto=format&fit=crop&w=800&q=80",
                "skyline_orchard.jpg",
            ],
        ],
    },
    "ecommerce": {
        "default_company": "TrooGood",
        "default_tenant": "troogood",
        "default_bot": "TrooGood",
        "default_hours": "24/7 Automated Support",
        "tagline": "Premium homemade-style chikki — jaggery, peanuts, sesame & dry fruits",
        "support_email": "support@troogood.com",
        "support_phone": "+91 1234567891",
        "website": "https://www.troogood.com",
        "catalog_columns": [
            "Product Name", "SKU", "Category", "Price (₹)", "Discount Price",
            "Key Specifications / Size", "Stock Status", "Warranty / Returns", "Image URL",
        ],
        "catalog_rows": [
            [
                "Classic Peanut Chikki", "TG-CHK-001", "Chikki", "₹149", "₹129",
                "Jaggery + roasted peanuts, 200g pack", "In Stock", "7-Day Easy Return",
                f"{U}/photo-1599599810769-bcde5a160d32?auto=format&fit=crop&w=800&q=80",
                "troogood_peanut.jpg",
            ],
            [
                "Sesame Jaggery Chikki", "TG-CHK-014", "Chikki", "₹159", "₹139",
                "Til + jaggery bars, 200g pack", "In Stock", "7-Day Easy Return",
                f"{U}/photo-1606313564200-e75d5e30476c?auto=format&fit=crop&w=800&q=80",
                "troogood_sesame.jpg",
            ],
            [
                "Dry Fruit Energy Chikki", "TG-CHK-022", "Chikki", "₹249", "₹219",
                "Almonds, cashew, dates & jaggery, 180g", "In Stock", "7-Day Easy Return",
                f"{U}/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=800&q=80",
                "troogood_dryfruit.jpg",
            ],
            [
                "Millet Multigrain Chikki", "TG-CHK-031", "Healthy Snacks", "₹199", "₹179",
                "Ragi + jowar + jaggery, 200g", "In Stock", "7-Day Easy Return",
                f"{U}/photo-1498837167922-ddd27525d352?auto=format&fit=crop&w=800&q=80",
                "troogood_millet.jpg",
            ],
        ],
    },
    "it_software": {
        "default_company": "Leeway Softech Private Limited",
        "default_tenant": "leewaysoftech",
        "default_bot": "Leeway Tech Advisor",
        "default_hours": "09:30 AM - 07:00 PM (Mon-Sat)",
        "tagline": "Software Development & AI Solutions — Engineering Future-Ready Digital Products",
        "support_email": "sales@leewaysoftech.com",
        "support_phone": "+91 8690783030",
        "website": "https://leewaysoftech.com",
        "menu_items": [
            ("Our Services", "Web, mobile, AI & enterprise engineering", "💻 Services", "offerings"),
            ("Technologies", "React, Python, Flutter, AWS & AI stack", "💻 Services", "technologies"),
            ("Projects", "Portfolio, case studies & industries", "🏢 Company", "projects"),
            ("Get a Quote", "Share requirements for a written estimate", "📋 Sales", "quote"),
            ("Careers", "Open roles, internships & how to apply", "🏢 Company", "careers"),
            ("Benefits", "Why teams choose Leeway Softech", "🏢 Company", "benefits"),
        ],
        "catalog_columns": [
            "Service / Offering", "Category", "Starting Price / Model",
            "Tech Stack & Tools", "Typical Timeline", "Scope & Deliverables", "Image URL",
        ],
        "catalog_rows": [
            [
                "Full-Stack Web App Development", "Custom Software", "Starting ₹4,00,000 / Fixed or T&M",
                "Next.js, FastAPI, PostgreSQL, AWS, Docker", "6 - 12 Weeks",
                "Architecture, responsive UI, APIs, CI/CD",
                f"{U}/photo-1498050108023-c5249f4df085?auto=format&fit=crop&w=800&q=80",
                "leeway_web.jpg",
            ],
            [
                "Cross-Platform Mobile App", "Mobile Engineering", "Starting ₹5,50,000 / Project",
                "Flutter / React Native, Firebase", "8 - 14 Weeks",
                "iOS & Android, push, offline, store publishing",
                f"{U}/photo-1512941937669-90a1b58e7e9c?auto=format&fit=crop&w=800&q=80",
                "leeway_mobile.jpg",
            ],
            [
                "WhatsApp Business API + AI Chatbot", "AI Engineering", "Starting ₹2,50,000 / Project",
                "Meta Cloud API, RAG, FAISS, Ollama/OpenAI", "4 - 8 Weeks",
                "Bot flows, catalog, FAQ/KB, human handoff",
                f"{U}/photo-1677442136019-21780ecad995?auto=format&fit=crop&w=800&q=80",
                "leeway_chatbot.jpg",
            ],
            [
                "Cloud & Dedicated Engineering Pods", "Cloud / Teams", "Starting ₹1,80,000 / Month",
                "AWS, GCP, Terraform, Kubernetes", "Ongoing retainer",
                "IaC, deployments, dedicated squad",
                f"{U}/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=800&q=80",
                "leeway_cloud.jpg",
            ],
        ],
        "info_pages": [
            (
                "technologies",
                "• Here's the stack we build with:\n"
                "• *Frontend:* React.js, Next.js, Vue.js, Angular, TypeScript, Tailwind CSS\n"
                "• *Backend:* Node.js, Python (FastAPI/Django), Golang, Laravel, .NET Core\n"
                "• *AI & ML:* OpenAI, LangChain, PyTorch, TensorFlow, Hugging Face, Vertex AI, Azure OpenAI\n"
                "• *Mobile:* iOS (Swift), Android (Kotlin), React Native, Flutter\n"
                "• *Data & Cloud:* PostgreSQL, MySQL, MongoDB, Redis, AWS, Azure, GCP, Docker, CI/CD\n"
                "• Tell us what you're building and we'll match the right stack.",
            ),
            (
                "projects",
                "• A snapshot of the work we deliver:\n"
                "• *Web platforms:* e-commerce stores, customer portals and internal systems\n"
                "• *Mobile apps:* customer and field-force apps for iOS and Android\n"
                "• *Enterprise:* CRM/ERP integrations, workflow automation and analytics dashboards\n"
                "• *Industries:* retail, healthcare, finance, logistics and education\n"
                "• Client names and detailed case studies are shared only with written permission — ask for a walkthrough on a call.",
            ),
            (
                "careers",
                "💼 *Open roles at Leeway Softech:*\n\n"
                "*Development*\n• Python Developer — 1–3 yrs · Ahmedabad\n• UI/UX Developer — 0–1 yrs\n\n"
                "*Sales*\n• Sales Executive — 2–4 yrs\n\n"
                "Forward your CV to hr@leewaysoftech.com with the role in the subject. Shortlisted candidates hear from us shortly.",
            ),
            (
                "benefits",
                "• Why teams choose Leeway Softech:\n"
                "• *Dedicated point of contact* for every engagement\n"
                "• *Agile delivery* with transparent sprints and demos\n"
                "• *Learning culture* — mentorship and exposure across web, mobile, AI and cloud\n"
                "• *Your IP stays yours* — code and assets handed over\n"
                "• Post-launch support / AMC options and clear contracts + NDA on request",
            ),
        ],
    },
    "tours_travel": {
        "default_company": "99 Destinations Holidays Pvt. Ltd.",
        "default_tenant": "99destinations",
        "default_bot": "99 Destinations Assistant",
        "default_hours": "10:30 AM - 07:30 PM (Mon-Sat)",
        "tagline": "Recognized by Gujarat Tourism (TCGL) | Customized Domestic & International Holidays",
        "support_email": "info@99destinations.in",
        "support_phone": "+91 7874833999",
        "website": "https://www.99destinations.in",
        "catalog_columns": [
            "Package Name", "Destination", "Duration", "Price per Person",
            "Key Inclusions", "Highlights", "Best Travel Months", "Image URL",
        ],
        "catalog_rows": [
            [
                "Best of Gujarat", "Gujarat Circuit", "8N / 7D", "On request",
                "Hotels, transfers, sightseeing, breakfast",
                "Dwarka, Somnath, Gir, Diu", "Oct - Mar",
                f"{U}/photo-1524492412937-b28074a5d7da?auto=format&fit=crop&w=800&q=80",
                "99_best_gujarat.jpg",
            ],
            [
                "Rann Utsav Special", "Kutch / Dhordo", "3N / 2D", "On request",
                "Tent city, transfers, cultural evening",
                "White Rann sunset, camel safari", "Nov - Feb",
                f"{U}/photo-1477587458883-47145ed94245?auto=format&fit=crop&w=800&q=80",
                "99_rann.jpg",
            ],
            [
                "Lions Calling — Gir Safari", "Sasan Gir", "3N / 2D", "On request",
                "Resort, safari permit assist, meals",
                "Asiatic lion jungle safari", "Dec - May",
                f"{U}/photo-1546182990-dffeafbe841d?auto=format&fit=crop&w=800&q=80",
                "99_gir.jpg",
            ],
            [
                "Statue of Unity Escape", "Kevadia", "3N / 2D", "On request",
                "Hotel, viewing gallery assist, transfers",
                "182m statue, Valley of Flowers, dam", "All year",
                f"{U}/photo-1524492412937-b28074a5d7da?auto=format&fit=crop&w=800&q=80",
                "99_sou.jpg",
            ],
        ],
    },
    "healthcare": {
        "default_company": "CareWell Multi-Specialty Clinic",
        "default_tenant": "carewellclinic",
        "default_bot": "CareWell Care Assistant",
        "default_hours": "08:00 AM - 08:30 PM (Mon-Sat), Emergency 24/7",
        "tagline": "Specialties, doctor consultation timings, health packages & appointments",
        "support_email": "care@carewellclinic.example",
        "support_phone": "+91 9988776655",
        "website": "https://www.carewellclinic.example",
        "catalog_columns": [
            "Specialty / Department", "Senior Specialist Doctor", "Consultation Fee",
            "Available Timings", "Services & Treatments", "Room / Clinic wing", "Image URL",
        ],
        "catalog_rows": [
            [
                "Cardiology & Heart Care", "Dr. Rajesh Sharma, MD, DM", "₹900",
                "Mon, Wed, Fri 10:00-14:00", "ECG, 2D Echo, TMT, Hypertension", "Wing A, Room 104",
                f"{U}/photo-1576091160399-112ba8d25d1d?auto=format&fit=crop&w=800&q=80",
                "care_cardio.jpg",
            ],
            [
                "Orthopedics & Joint Surgery", "Dr. Sunita Rao, MS (Ortho)", "₹800",
                "Tue, Thu, Sat 14:00-18:00", "Arthritis, fracture care, sports rehab", "Wing B, Room 201",
                f"{U}/photo-1559757175-0eb30cd8c063?auto=format&fit=crop&w=800&q=80",
                "care_ortho.jpg",
            ],
            [
                "Pediatrics & Child Health", "Dr. Amit Verma, DCH, DNB", "₹700",
                "Mon-Sat 09:00-13:00", "Vaccination, growth, allergy care", "Wing A, Room 108",
                f"{U}/photo-1631217868264-e5b90bb7e133?auto=format&fit=crop&w=800&q=80",
                "care_pedia.jpg",
            ],
            [
                "Dermatology & Cosmetology", "Dr. Neha Kulkarni, MD", "₹850",
                "Mon, Wed, Sat 16:00-20:00", "Acne, laser, PRP, skin allergy", "Wing C, Room 302",
                f"{U}/photo-1515377905703-c4788e51af15?auto=format&fit=crop&w=800&q=80",
                "care_derma.jpg",
            ],
        ],
    },
    "banking": {
        "default_company": "Meridian Bank",
        "default_tenant": "meridianbank",
        "default_bot": "Meridian Assistant",
        "default_hours": "09:00 AM - 06:00 PM (Mon-Fri) | Phone banking 24x7",
        "tagline": "Meridian Bank — Bank of All Banks",
        "support_email": "care@meridianbank.com",
        "support_phone": "+91 7418527567",
        "website": "https://www.meridianbanker.com/",
        "catalog_columns": [
            "Product / Scheme", "Category", "Interest Rate / Annual Fee",
            "Key Features & Benefits", "Eligibility Criteria", "Minimum Balance", "Image URL",
        ],
        "catalog_rows": [
            [
                "Meridian Savings Account", "Savings", "As published (quarterly credit)",
                "Digital KYC, debit card, net/mobile banking", "Resident Indian, 18+", "₹5,000 AMB / zero-balance salary",
                f"{U}/photo-1554224155-6726b3ff858f?auto=format&fit=crop&w=800&q=80",
                "meridian_savings.jpg",
            ],
            [
                "Meridian Fixed Deposit", "Deposits", "Competitive FD rates + senior upside",
                "Flexible tenure, loan against FD", "Individual / Joint", "Min ₹5,000",
                f"{U}/photo-1579621970563-ebec7560ff3e?auto=format&fit=crop&w=800&q=80",
                "meridian_fd.jpg",
            ],
            [
                "CashBack / Travel Credit Card", "Credit Card", "Annual fee as per variant",
                "Contactless, rewards, secured-against-FD option", "Income ₹20,000+/mo or FD secure", "N/A",
                f"{U}/photo-1556742049-0cfed4f6a45d?auto=format&fit=crop&w=800&q=80",
                "meridian_card.jpg",
            ],
            [
                "Home Loan", "Loans", "From 8.50% p.a.*",
                "Up to 80% LTV, tenure up to 30 years", "Age 21–65, income norms apply", "N/A",
                f"{U}/photo-1560518883-ce09059eeffa?auto=format&fit=crop&w=800&q=80",
                "meridian_homeloan.jpg",
            ],
        ],
    },
    "finance": {
        "default_company": "L&T Finance Limited",
        "default_tenant": "ltfinance",
        "default_bot": "LTF Virtual Assistant",
        "default_hours": "09:00 AM - 06:00 PM (Mon-Sat)",
        "tagline": "Leading NBFC | Two-Wheeler, Personal, Home, Gold, Farm & SME Loans",
        "support_email": "customercare@ltfs.com",
        "support_phone": "+91 7378333451",
        "website": "https://www.ltfs.com",
        "catalog_columns": [
            "Service Name", "Category", "Fee Structure / Pricing",
            "Deliverables & Scope", "Turnaround Time", "Target Client", "Image URL",
        ],
        "catalog_rows": [
            [
                "Two-Wheeler Loan", "Retail Lending", "Up to 100% on-road on select models",
                "Bike/scooter/EV finance, tenure 12–48 months", "Instant in-principle at dealership", "Salaried / Self-employed",
                f"{U}/photo-1558981806-ec527fa84c39?auto=format&fit=crop&w=800&q=80",
                "ltf_twowheeler.jpg",
            ],
            [
                "Personal Loan", "Consumer Finance", "₹50,000 – ₹15 Lakhs",
                "100% digital via PLANET app, 12–60 months", "Disbursal ~24 hrs after verification", "Salaried / Self-employed",
                f"{U}/photo-1450101499163-c8848c66ca85?auto=format&fit=crop&w=800&q=80",
                "ltf_personal.jpg",
            ],
            [
                "Gold Loan", "Secured Lending", "Rates from ~11.75%* p.a.",
                "18–22K jewellery, flexible repayment schemes", "Same-day after valuation", "Individuals",
                f"{U}/photo-1610375461246-83df859d849d?auto=format&fit=crop&w=800&q=80",
                "ltf_gold.jpg",
            ],
            [
                "Home Loan / LAP", "Housing Finance", "Long tenure up to 30 years",
                "Home purchase, BT + top-up, LAP up to ₹5 Cr", "As per underwriting", "Salaried / Self-employed / Business",
                f"{U}/photo-1560518883-ce09059eeffa?auto=format&fit=crop&w=800&q=80",
                "ltf_home.jpg",
            ],
        ],
    },
    "generic": {
        "default_company": "Apex Global Logistics & Freight Services",
        "default_tenant": "apexlogistics",
        "default_bot": "Apex Assistant",
        "default_hours": "09:00 AM - 06:00 PM (Mon-Fri)",
        "tagline": "Your trusted partner for seamless global logistics",
        "support_email": "care@apexlogistics.com",
        "support_phone": "+91 98765 43210",
        "website": "https://www.apexlogistics.com",
        "catalog_columns": [
            "Item / Service Name", "Category", "Price / Rate", "Unit",
            "Key Features & Inclusions", "Detailed Description", "Image URL",
        ],
        "catalog_rows": [
            [
                "Domestic Express Freight", "Freight", "On request", "per shipment",
                "Door-to-door, tracking, insurance assist", "Pan-India surface & air express",
                f"{U}/photo-1586528116311-ad8dd3c8310d?auto=format&fit=crop&w=800&q=80",
                "apex_domestic.jpg",
            ],
            [
                "International Air Cargo", "Freight", "On request", "per kg",
                "Airport-to-airport / DDU options", "Export documentation support",
                f"{U}/photo-1436491865332-7a61a109cc05?auto=format&fit=crop&w=800&q=80",
                "apex_air.jpg",
            ],
            [
                "Ocean FCL / LCL", "Ocean", "On request", "per container / CBM",
                "Port handling, customs coordination", "Scheduled sailings major lanes",
                f"{U}/photo-1494412574643-ff11b0a5c1c3?auto=format&fit=crop&w=800&q=80",
                "apex_ocean.jpg",
            ],
            [
                "Warehousing & Fulfilment", "3PL", "Starting retainer", "per month",
                "Storage, pick-pack, last-mile handoff", "SKU inventory visibility",
                f"{U}/photo-1553413077-190dd305871c?auto=format&fit=crop&w=800&q=80",
                "apex_warehouse.jpg",
            ],
        ],
    },
}

# Fallback INFO PAGES for every vertical (used when company block has no info_pages yet).
DEFAULT_INFO_PAGES: Dict[str, List[Tuple[str, str]]] = {
    "real_estate": [
        ("technologies", "• Construction & living tech we highlight:\n• Smart-home ready wiring, biometric locks, solar options\n• Digital site-visit booking and e-brochures\n• RERA-verified project data shared in chat\n• Ask for the tech sheet of any tower or villa."),
        ("projects", "• Featured developments:\n• Skyline Elegance — 2 & 3 BHK residences\n• Skyline Grandeur — 4 BHK sky residences & penthouses\n• Skyline Horizon — Grade-A commercial\n• Skyline Orchard Green — gated villas\n• Schedule a site visit for a guided walkthrough."),
        ("careers", "• Hiring across sales, CRM, site ops and documentation.\n• Share your CV with HR via support email.\n• Mention the role in the subject line."),
        ("benefits", "• Why buyers choose us:\n• RERA-registered inventory and clear cost sheets\n• Complimentary site-visit cab in city limits\n• Bank tie-ups for home loans\n• Dedicated post-sales desk through possession."),
    ],
    "ecommerce": [
        ("technologies", "• How we make & ship TrooGood:\n• Homemade-style recipes with jaggery and natural ingredients\n• Hygienic production and sealed packaging\n• Online ordering with live courier tracking\n• Ask about ingredients or shelf life for any SKU."),
        ("projects", "• Product highlights:\n• Classic Peanut, Sesame, Dry Fruit and Millet chikkis\n• Seasonal limited packs and gift hampers\n• Distributor / bulk programs for retailers\n• Browse the catalog for live prices and pack sizes."),
        ("careers", "• Openings in production, packing, sales and support.\n• Send your CV to support@troogood.com with the role in the subject."),
        ("benefits", "• Why customers choose TrooGood:\n• Clean, homemade-style recipes\n• Transparent ingredients and pack sizes\n• Easy returns on eligible SKUs\n• Fast dispatch across India."),
    ],
    "tours_travel": [
        ("technologies", "• How we plan your trip:\n• Curated itineraries with live hotel/flight inventory partners\n• Visa document checklists and appointment guidance\n• 24x7 duty phone while you travel\n• Ask for the tech/tools behind a specific package."),
        ("projects", "• Signature experiences:\n• Best of Gujarat, Rann Utsav, Gir safari, Statue of Unity\n• Custom honeymoon, family and group itineraries\n• Domestic and international circuits on request\n• Ask for a sample day-wise plan."),
        ("careers", "• We hire destination experts, operations and sales consultants.\n• Share your CV with info@99destinations.in."),
        ("benefits", "• Why travellers choose us:\n• Gujarat Tourism–recognized operator\n• Customizable packages and visa assistance\n• Transparent inclusions and on-trip support\n• 20,000+ happy guests."),
    ],
    "healthcare": [
        ("technologies", "• Clinical & digital tools:\n• Diagnostics (ECG, Echo, lab panels) with WhatsApp report delivery\n• Video consults for eligible specialties\n• Appointment scheduling in chat\n• Ask which wing or equipment supports your treatment."),
        ("projects", "• Care programs we run:\n• Cardiology, Orthopedics, Pediatrics, Dermatology OPD\n• Executive and senior health checkup packages\n• Emergency triage with 24x7 hotline\n• Book a slot under the specialty you need."),
        ("careers", "• Hiring doctors, nurses, lab techs and front-desk staff.\n• Share your CV with the careers / support desk."),
        ("benefits", "• Why patients choose CareWell:\n• Multi-specialty cover under one roof\n• Insurance / TPA cashless where listed\n• Digital reports and easy reschedule\n• Emergency response when it matters."),
    ],
    "banking": [
        ("technologies", "• Digital banking channels:\n• Mobile app & net banking (never share OTP/PIN in chat)\n• Instant card block and service requests\n• Secure KYC / video-KYC journeys\n• Ask how to activate a product — we guide steps, not passwords."),
        ("projects", "• Flagship products:\n• Savings & FD schemes\n• Cashback / travel cards\n• Home, personal and vehicle loans\n• Browse offerings or ask eligibility questions."),
        ("careers", "• Careers across branches, credit and digital teams.\n• Apply via the official careers channel or support email."),
        ("benefits", "• Why customers bank with Meridian:\n• Clear product guides without phishing asks\n• Fast card-block and fraud escalation\n• Branch/ATM locator help\n• Published grievance timelines."),
    ],
    "finance": [
        ("technologies", "• How we process loans digitally:\n• PLANET app / web journeys with e-KYC\n• Dealer-point two-wheeler financing\n• Secure document vaulting for gold loans\n• We never ask for OTP or MPIN on WhatsApp."),
        ("projects", "• Lending programs:\n• Two-wheeler, personal, gold, home/LAP and SME finance\n• Balance transfer and top-up options where eligible\n• Ask which product fits your need."),
        ("careers", "• Hiring credit, sales and customer-care roles.\n• Share your CV via customercare@ltfs.com with the role named."),
        ("benefits", "• Why borrowers choose L&T Finance:\n• Wide product suite and partner network\n• Fast in-principle decisions on eligible profiles\n• Transparent grievance redressal\n• Chat for guidance — never for passwords."),
    ],
    "generic": [
        ("technologies", "• Platforms & tools we operate with:\n• Tracking systems, EDI/API partner links, warehouse WMS\n• Ask which stack supports your lane or fulfilment need."),
        ("projects", "• Delivery programs:\n• Domestic express, air cargo, ocean FCL/LCL, 3PL warehousing\n• Ask for a lane quote or SLA summary."),
        ("careers", "• Hiring ops, warehouse and sales talent.\n• Send your CV to care@apexlogistics.com."),
        ("benefits", "• Why shippers choose Apex:\n• End-to-end visibility\n• Customs and documentation support\n• Flexible domestic and international lanes\n• Dedicated account coordination."),
    ],
}


def apply_company_examples(configs: Dict[str, Dict[str, Any]]) -> None:
    """Overlay real-company brand + catalog (with image URL + local filename)."""
    for key, cfg in configs.items():
        ex = COMPANY_EXAMPLES.get(key)
        if not ex:
            continue
        for field in (
            "default_company", "default_tenant", "default_bot", "default_hours", "tagline",
        ):
            if field in ex:
                cfg[field] = ex[field]
        cfg["support_email"] = ex.get("support_email")
        cfg["support_phone"] = ex.get("support_phone")
        cfg["website"] = ex.get("website")
        if ex.get("menu_items"):
            cfg["menu_items"] = list(ex["menu_items"])
        cfg["info_pages"] = list(ex.get("info_pages") or DEFAULT_INFO_PAGES.get(key) or [])
        cfg["catalog_columns"] = list(ex["catalog_columns"])
        # Store rows with trailing local filename stripped from table cells
        table_rows: List[List[str]] = []
        media_files: List[Tuple[str, str]] = []  # (url, local_name)
        for row in ex["catalog_rows"]:
            *cells, local_name = row
            url = cells[-1] if cells else ""
            table_rows.append([str(c) for c in cells])
            if local_name and url:
                media_files.append((str(url), str(local_name)))
        cfg["catalog_rows"] = table_rows
        cfg["catalog_media"] = media_files  # used by generator to download/embed
