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
        "default_hours": "09:30 AM - 07:00 PM (Mon-Sat) · Support focus 24/7",
        "tagline": "Innovative Technology. Creative Work. Trusted Delivery. — AI, software & CPaaS since 2012",
        "support_email": "sales@leewaysoftech.com",
        "support_phone": "+91 8690783030",
        "website": "https://leewaysoftech.com",
        "menu_items": [
            ("Our Services", "AI, software, web, mobile & CPaaS", "💻 Services", "offerings"),
            ("Technologies", "React, Python, Flutter, cloud & AI", "💻 Services", "technologies"),
            ("Projects", "Clients, portfolio & industries served", "🏢 Company", "projects"),
            ("Get a Quote", "Share scope for a written estimate", "📋 Sales", "quote"),
            ("Careers", "Open roles & how to apply", "🏢 Company", "careers"),
            ("Benefits", "Why 1500+ clients choose Leeway", "🏢 Company", "benefits"),
        ],
        "catalog_columns": [
            "Service / Offering", "Category", "Starting Price / Model",
            "Tech Stack & Tools", "Typical Timeline", "Scope & Deliverables", "Image URL",
        ],
        "catalog_rows": [
            [
                "Generative AI Development", "Enterprise AI & GenAI", "₹1.5 Lakh - 8 Lakh / Project",
                "OpenAI, LangChain, RAG, Python", "4 - 10 Weeks",
                "LLM apps, agents, private RAG, evaluation & guardrails",
                f"{U}/photo-1677442136019-21780ecad995?auto=format&fit=crop&w=800&q=80",
                "leeway_chatbot.jpg",
            ],
            [
                "AI Chatbot Development", "Conversational AI", "₹75,000 - 3.5 Lakh",
                "WhatsApp/Web, NLP, RAG, FAISS", "3 - 8 Weeks",
                "Flows, FAQ/KB, handoff, analytics, multilingual options",
                f"{U}/photo-1531746790731-6c087fecd65a?auto=format&fit=crop&w=800&q=80",
                "leeway_chatbot.jpg",
            ],
            [
                "Machine Learning Solutions", "AI & ML", "₹2 Lakh - 10 Lakh",
                "PyTorch, TensorFlow, Hugging Face", "6 - 14 Weeks",
                "Predictive models, NLP, ranking, model ops handoff",
                f"{U}/photo-1555949963-aa79dcee981c?auto=format&fit=crop&w=800&q=80",
                "leeway_cloud.jpg",
            ],
            [
                "Computer Vision Solutions", "AI & Vision", "₹2 Lakh - 8 Lakh",
                "OpenCV, PyTorch, edge/cloud inference", "6 - 12 Weeks",
                "Detection, OCR, quality inspection, dashboards",
                f"{U}/photo-1485827404703-89b55fcc595e?auto=format&fit=crop&w=800&q=80",
                "leeway_cloud.jpg",
            ],
            [
                "AI Workflow Automation", "AI & Automation", "₹1 Lakh - 5 Lakh",
                "Python, RPA APIs, LLM tools", "4 - 10 Weeks",
                "Document processing, approvals, system integrations",
                f"{U}/photo-1518186285589-2f7649de83e0?auto=format&fit=crop&w=800&q=80",
                "leeway_web.jpg",
            ],
            [
                "Enterprise Software Development", "Software Engineering", "₹3 Lakh - 25 Lakh",
                "Node, Python, .NET, microservices", "8 - 24 Weeks",
                "Custom enterprise apps, workflows, SSO, audit trails",
                f"{U}/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=800&q=80",
                "leeway_web.jpg",
            ],
            [
                "SaaS Product Development", "Product Engineering", "₹4 Lakh - 30 Lakh",
                "Multi-tenant, billing, React/Next", "10 - 28 Weeks",
                "MVP to scale: tenancy, roles, subscriptions, analytics",
                f"{U}/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=800&q=80",
                "leeway_web.jpg",
            ],
            [
                "Web Application Development", "Web Engineering", "₹1 Lakh - 10 Lakh",
                "React, Next.js, Node, PostgreSQL", "6 - 16 Weeks",
                "Responsive portals, APIs, admin consoles, SEO basics",
                f"{U}/photo-1498050108023-c5249f4df085?auto=format&fit=crop&w=800&q=80",
                "leeway_web.jpg",
            ],
            [
                "Mobile App Development", "Mobile Solutions", "₹1.5 Lakh - 12 Lakh",
                "Flutter / React Native / Swift / Kotlin", "8 - 16 Weeks",
                "iOS & Android, push, offline, store publishing",
                f"{U}/photo-1512941937669-90a1b58e7e9c?auto=format&fit=crop&w=800&q=80",
                "leeway_mobile.jpg",
            ],
            [
                "UI/UX & Design Systems", "Creative & Design", "₹50,000 - 3 Lakh",
                "Figma, design tokens, accessibility", "2 - 8 Weeks",
                "Research, UI kits, prototypes, handoff to engineering",
                f"{U}/photo-1561070791-2526d30994b5?auto=format&fit=crop&w=800&q=80",
                "leeway_web.jpg",
            ],
            [
                "WhatsApp Business API Integration", "Communications", "₹25,000 - 1.5 Lakh",
                "Meta Cloud API, templates, webhooks", "2 - 6 Weeks",
                "Green-tick setup, bots, broadcasts, CRM sync",
                f"{U}/photo-1611746872915-64382b5c76da?auto=format&fit=crop&w=800&q=80",
                "leeway_chatbot.jpg",
            ],
            [
                "CPaaS / Omnichannel Messaging", "Communications", "Pay per use / Platform plan",
                "SMS, Email, WhatsApp, IVR, Push", "2 - 8 Weeks",
                "Unified messaging APIs, campaigns, delivery reports",
                f"{U}/photo-1557804506-669a67965ba0?auto=format&fit=crop&w=800&q=80",
                "leeway_cloud.jpg",
            ],
            [
                "Enterprise SMS Gateway & OTP", "Communications", "Pay per SMS / Plan",
                "SMSC, DLT, high-throughput APIs", "1 - 4 Weeks",
                "OTP, alerts, transactional SMS with compliance support",
                f"{U}/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=800&q=80",
                "leeway_cloud.jpg",
            ],
            [
                "Cloud Migration & DevOps", "Cloud & DevOps", "Starting ₹1.8 Lakh / Month squad",
                "AWS, Azure, GCP, Terraform, K8s", "Ongoing / SOW",
                "Migration, IaC, CI/CD, monitoring, cost control",
                f"{U}/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=800&q=80",
                "leeway_cloud.jpg",
            ],
            [
                "Data Engineering & BI", "Data & Analytics", "₹1.5 Lakh - 6 Lakh+",
                "Snowflake, BigQuery, dbt, dashboards", "6 - 14 Weeks",
                "Pipelines, warehouses, BI, predictive analytics",
                f"{U}/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=800&q=80",
                "leeway_cloud.jpg",
            ],
            [
                "E-Commerce / Headless Commerce", "Commerce", "₹2 Lakh - 15 Lakh",
                "Shopify, headless, payment gateways", "6 - 16 Weeks",
                "Storefronts, catalogs, payments, omnichannel retail",
                f"{U}/photo-1556742049-0cfed4f6a45d?auto=format&fit=crop&w=800&q=80",
                "leeway_web.jpg",
            ],
            [
                "CRM / ERP / CMS Platforms", "Enterprise Platforms", "License + implementation",
                "Custom CRM/ERP/CMS, APIs", "8 - 20 Weeks",
                "Sales, ops, content platforms tailored to process",
                f"{U}/photo-1454165804606-c3d57bc86b40?auto=format&fit=crop&w=800&q=80",
                "leeway_web.jpg",
            ],
            [
                "Dedicated Engineering Pod", "Teams / Retainer", "Starting ₹1.8 Lakh / Month",
                "Full-stack + QA + DevOps mix", "Monthly",
                "Embedded squad with sprint demos and shared backlog",
                f"{U}/photo-1522071820081-009f0129c71c?auto=format&fit=crop&w=800&q=80",
                "leeway_cloud.jpg",
            ],
        ],
        # Populates frontend sidebar: Technologies / Projects / Careers / Benefits
        # Tuple: (page_id, bot_answer, keywords_csv, examples_pipe)
        "info_pages": [
            (
                "technologies",
                "• *Leeway tech stack* (selected after requirement analysis):\n"
                "• *Frontend:* React.js, Next.js, Vue.js, Angular, TypeScript, Tailwind CSS\n"
                "• *Backend:* Node.js, Python (FastAPI / Django), Golang, Laravel, .NET Core\n"
                "• *AI & ML:* OpenAI (GPT APIs), LangChain, PyTorch, TensorFlow, Hugging Face, Vertex AI, Azure OpenAI\n"
                "• *Mobile:* iOS (Swift), Android (Kotlin), React Native, Flutter\n"
                "• *Data:* PostgreSQL, MySQL, MongoDB, DynamoDB, Firebase, Snowflake, BigQuery, Redis\n"
                "• *Cloud & DevOps:* AWS, Azure, GCP, Docker, Kubernetes, CI/CD\n"
                "• Ask which stack fits your product — tap *Get a Quote* or *Technologies* in the menu.",
                "technologies, technology, tech stack, stack, framework, tools, react, python, flutter, aws",
                "what technologies do you use|what is your tech stack|which tools do you work with",
            ),
            (
                "projects",
                "• *Portfolio & impact:*\n"
                "• 1500+ clients · 14 years · 120+ CPaaS projects · 60+ apps · 45+ AI solutions\n"
                "• *Trusted names:* Tata Tele, BHEL, Powergrid, Bandhan Bank, Club Mahindra, Airport Authority, Indian Railway, RITES, Jindal, Lodha, universities & education boards\n"
                "• *Industries:* Government & PSU, BFSI, Education, Hospitality, Enterprise, Politics, Retail & e-commerce\n"
                "• *Highlight:* MoU with Government of Gujarat for AI (pathway for 250+ jobs)\n"
                "• Detailed case studies shared on request with client permission — ask for a walkthrough.",
                "projects, project, portfolio, case study, case studies, clients, our work, experience",
                "show me your projects|who have you built for|any case studies",
            ),
            (
                "careers",
                "💼 *Careers at Leeway Softech*\n"
                "• We're hiring across sales, product, design, QA, support and operations.\n"
                "• *Sample openings:* Sales Executive (2–4 yrs, Mumbai/Bhavnagar), BDM (2–5 yrs, Mumbai), QA Tester (1–2 yrs, Bhavnagar), UI/UX Designer (1–2 yrs, Bhavnagar), L1/L2 Support (2–4 yrs, Delhi), Senior HR/Accountant/IT Manager as posted.\n"
                "• Apply: https://leewaysoftech.com/careers — PDF resume max 2 MB, or email HR with the role in the subject.\n"
                "• Culture: Life @ Leeway — festivals, anniversaries, trips and team events.",
                "career, careers, job, hiring, vacancy, internship, open role, join us",
                "are you hiring|job openings|careers at leeway|internship",
            ),
            (
                "benefits",
                "• *Why teams choose Leeway Softech:*\n"
                "• *Certified security & quality* — ISO 9001:2015, ISO/IEC 27001:2013, CMMI Level 3\n"
                "• *Proven at scale* — 1,500+ clients across India\n"
                "• *Government-grade trust* — MoU with Government of Gujarat for AI\n"
                "• *True end-to-end* — CPaaS, software, AI and cloud under one partner\n"
                "• Dedicated POC, transparent delivery, NDA/IP-friendly contracts, post-go-live support\n"
                "• Offices: Mumbai (corporate), Bhavnagar (registered), Delhi/NCR, Ahmedabad",
                "benefits, why choose you, why work with you, advantages, perks, differentiators",
                "why should we work with you|what are the benefits|why choose leeway",
            ),
        ],
        "faq_rows": [
            ("What services does Leeway Softech provide?", "AI development, custom/enterprise software, SaaS, data engineering & BI, CPaaS (SMS, Email, WhatsApp, IVR), web & mobile apps, UI/UX, cloud/DevOps, and digital transformation.", "Services"),
            ("Is Leeway an AI development company?", "Yes — Generative AI, AI chatbots, machine learning, computer vision, and AI automation for business processes.", "Artificial Intelligence"),
            ("Do you build WhatsApp Business API solutions?", "Yes. We integrate Meta WhatsApp Business API for support bots, notifications, and broadcasts, including CRM/website sync.", "WhatsApp Solutions"),
            ("What is CPaaS and do you offer it?", "Communications Platform as a Service — messaging/voice capabilities via APIs. We offer CPaaS, SMS gateway, SMSC, omnichannel, push, and bulk email.", "Platforms"),
            ("Which industries do you specialize in?", "Government & public sector, banking & financial services, education, hospitality, enterprise/corporate, politics, and retail/e-commerce.", "Industries"),
            ("Where is Leeway Softech based?", "Founded 2012. Corporate office Mumbai; registered office Bhavnagar; branches in Delhi/NCR (Noida) and Ahmedabad. Delivery also supports USA, UK, UAE, Canada, Australia.", "Company"),
            ("How do I contact sales or support?", "Sales: sales@leewaysoftech.com · Consultation +91 8690783030 · Support +91 8000305305. Typical reply under 2 hours for message inquiries.", "Contact"),
            ("How do you estimate project costs?", "We scope features, integrations, roles, non-functionals and timeline, then propose fixed-bid, T&M, or dedicated squad pricing with a written SOW.", "Pricing"),
            ("What engagement models do you offer?", "Fixed-price projects, time & materials, monthly dedicated teams/pods, and outcome-based retainers.", "Engagement"),
            ("Do you sign an NDA before discussions?", "Yes. Mutual NDAs before reviewing confidential architecture, code, or roadmaps.", "Security & IP"),
            ("Who owns the intellectual property (IP)?", "Clients own 100% of custom source code, designs, and project data after agreed milestone payments (open-source components keep their licenses).", "IP Ownership"),
            ("What post-launch maintenance do you provide?", "Typically 60 days warranty for defects we introduced, plus optional SLA retainers for monitoring, patches, and feature velocity.", "Support"),
            ("Which certifications does Leeway hold?", "ISO 9001:2015, ISO/IEC 27001:2013, and CMMI Level 3.", "Compliance"),
            ("Can you take over a legacy codebase?", "Yes — structured audit (tests, deps, infra, security) then stabilize vs rewrite recommendations.", "Legacy"),
            ("Do you deploy into our cloud accounts?", "Preferred model is deploy into the client AWS/GCP/Azure org with IaC and least-privilege access.", "Cloud"),
            ("What frontend and backend technologies do you use?", "Frontend: React, Next.js, Vue, Angular, TypeScript. Backend: Node.js, Python, Golang, Laravel, .NET Core — selected per requirement.", "Technology Stack"),
            ("Do you provide UI/UX design?", "Yes — research, interactive UI, mobile app design, and design systems, standalone or with engineering.", "Design"),
            ("How can I schedule a consultation?", "Message on WhatsApp, call +91 8690783030, or use Get a Quote / Book a Callback in the menu.", "Consultation & Quotes"),
            ("Are you hiring?", "Yes — see Careers for open roles (sales, QA, design, support, etc.). Apply on https://leewaysoftech.com/careers with a PDF resume.", "Careers"),
            ("What makes Leeway different?", "Certified security/quality, 1500+ clients, Gujarat Government AI MoU, and true end-to-end delivery from messaging platforms to full software builds.", "Why Us"),
        ],
        "kb_articles": [
            (
                "Company Overview & Trust Signals",
                "Company",
                "# Leeway Softech Private Limited\n\n"
                "Founded **2012**. Tagline: *Innovative Technology. Creative Work. Trusted Delivery.*\n\n"
                "**Contacts:** sales@leewaysoftech.com · +91 8690783030 (consultation) · +91 8000305305 (support)\n"
                "**Web:** https://leewaysoftech.com · CIN: U72900GJ2012PTC071245\n\n"
                "**Certifications:** ISO 9001:2015, ISO/IEC 27001:2013, CMMI Level 3.\n\n"
                "**Offices:** Mumbai corporate · Bhavnagar registered · Delhi/NCR · Ahmedabad.\n\n"
                "**Impact:** 1500+ clients, 14 years, 120+ CPaaS projects, 60+ apps, 45+ AI solutions.",
            ),
            (
                "Services Map — AI, Software, CPaaS & Cloud",
                "Services",
                "# Core Service Groups\n\n"
                "1. **Communication & CPaaS** — Bulk SMS, Email, WhatsApp API, IVR, SMS Gateway, omnichannel\n"
                "2. **AI & Emerging Technology** — GenAI, chatbots, ML, vision, automation\n"
                "3. **Custom Software & SaaS** — enterprise apps, APIs, product engineering\n"
                "4. **Web & Mobile** — React/Next, Flutter/RN, ASO, analytics\n"
                "5. **Data & Analytics** — engineering, BI, predictive\n"
                "6. **Cloud & DevOps** — AWS/Azure/GCP, CI/CD, Kubernetes\n"
                "7. **UI/UX** — research, design systems, mobile UI\n\n"
                "Ask for a scoped quote with your use case and timeline.",
            ),
            (
                "Engagement, NDA, IP & Support",
                "Delivery",
                "# How We Work\n\n"
                "Understand → Plan → Build → Integrate → Test & Deploy → Improve.\n\n"
                "Engagement models: fixed-price, T&M, dedicated pods. Mutual NDA before deep reviews. "
                "Client owns custom IP after milestone settlement. Warranty period plus optional SLA retainers "
                "for production support.",
            ),
            (
                "Offices, Hours & Escalation",
                "Contact",
                "# Reach Us\n\n"
                "Hours: 09:30–19:00 Mon–Sat (IST); platform monitoring emphasis 24/7.\n\n"
                "Mumbai · Bhavnagar · Noida · Ahmedabad — see Contact Us on the website for full addresses.\n\n"
                "For disputes or urgent account issues, ask for a human agent / raise a ticket — never share OTPs or passwords on chat.",
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

# INFO PAGES are Software & IT only (Technologies / Projects / Careers / Benefits).
# Non-IT verticals intentionally have no fallback — banking must not ship those pages.
DEFAULT_INFO_PAGES: Dict[str, List[Tuple[str, str]]] = {
    "it_software": [],  # filled from COMPANY_EXAMPLES["it_software"]["info_pages"]
}


def apply_company_examples(configs: Dict[str, Dict[str, Any]]) -> None:
    """Overlay real-company brand + catalog (with image URL + local filename)."""
    from complete_profile_overlays import apply_profile_overlays

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
        # Only IT kits include Technologies / Projects / Careers / Benefits.
        if key == "it_software":
            cfg["info_pages"] = list(ex.get("info_pages") or DEFAULT_INFO_PAGES.get(key) or [])
        else:
            cfg["info_pages"] = []
        # Prefer company-specific FAQs / KB (prepend), keep generic enrichments that aren't duplicates
        if ex.get("faq_rows"):
            existing = list(cfg.get("faq_rows") or [])
            seen_q = {str(q).strip().lower() for q, *_ in ex["faq_rows"]}
            merged = list(ex["faq_rows"])
            for row in existing:
                q = str(row[0]).strip().lower() if row else ""
                if q and q not in seen_q:
                    merged.append(row)
                    seen_q.add(q)
            cfg["faq_rows"] = merged
        if ex.get("kb_articles"):
            existing_kb = list(cfg.get("kb_articles") or [])
            seen_t = {str(t).strip().lower() for t, *_ in ex["kb_articles"]}
            merged_kb = list(ex["kb_articles"])
            for row in existing_kb:
                t = str(row[0]).strip().lower() if row else ""
                if t and t not in seen_t:
                    merged_kb.append(row)
                    seen_t.add(t)
            cfg["kb_articles"] = merged_kb
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

    # After company brand/catalog, fill every remaining universal + domain field.
    apply_profile_overlays(configs)
