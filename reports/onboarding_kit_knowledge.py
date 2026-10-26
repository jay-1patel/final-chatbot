"""Expanded FAQ + Knowledge Base content for onboarding kits.

Used by generate_onboarding_kits.py so every vertical ships with enough
chatbot-ready Q&A and longer policy / how-to articles for FAQ + KB indexing.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

FaqRow = Tuple[str, str, str]  # question, answer, category
KbArticle = Tuple[str, str, str]  # title, category, markdown/body


FAQ_BY_VERTICAL: Dict[str, List[FaqRow]] = {
    "real_estate": [
        ("What banks have approved home loans for these projects?", "Approved by SBI, HDFC, ICICI, Axis, and Kotak with pre-approved sanction letters and financing up to 80–90% of the agreement value.", "Home Loans"),
        ("Is the site visit pickup complimentary?", "Yes. We arrange a dedicated AC cab pickup and drop from your residence or office at no charge, typically within the same city limits.", "Site Visits"),
        ("What is the booking advance amount?", "A booking advance of ₹2,00,000 secures your selected unit. The balance follows the construction-linked payment plan in the cost sheet.", "Booking & Payments"),
        ("Are all projects RERA certified?", "Yes. Every live inventory project holds valid RERA registration and municipal sanctions. RERA IDs are listed against each property in the catalog.", "Legal & Approvals"),
        ("Can Non-Resident Indians (NRIs) purchase units?", "Yes. NRIs can buy residential or commercial units via NRE/NRO channels with full RBI compliance. Our NRI desk assists with power of attorney and remittance paperwork.", "NRI Purchase"),
        ("What is included in the possession handover kit?", "Handover includes keys, occupancy certificate copy, society bye-laws summary, snag checklist sign-off, and introduction to facility management.", "Possession"),
        ("Do you offer construction-linked payment plans?", "Yes. Milestone plans are published in the official cost sheet (booking, foundation, slab stages, finishing, possession). Custom plans need sales-head approval.", "Booking & Payments"),
        ("Can I upgrade my unit configuration later?", "Unit upgrades depend on available inventory and stage of construction. Differential pricing and a fresh agreement addendum apply.", "Inventory"),
        ("What amenities are common across residential projects?", "Typical amenities include clubhouse, swimming pool, gym, landscaped gardens, 24x7 security, power backup, and visitor parking. Exact lists vary by project.", "Amenities"),
        ("How are stamp duty and registration handled?", "Stamp duty and registration are paid by the buyer as per state rates. Our documentation team coordinates the appointment and checklist.", "Legal & Approvals"),
        ("What is your resale / transfer policy before possession?", "Pre-possession transfers require builder NOC, transfer fee as per agreement, and updated KYC of the incoming buyer.", "Transfers"),
        ("How do I raise a post-sales complaint?", "Message your booking ID with the issue, or use Customer Support in the menu. Tickets are acknowledged within 1 business day.", "Support"),
        ("Are floor plans and carpet areas approximate?", "Marketing floor plans are indicative. Carpet area and final layout follow the RERA-approved drawings attached to your agreement.", "Floor Plans"),
        ("Do commercial leases include CAM charges?", "Lease quotes typically exclude CAM, property tax, and parking unless stated. Ask for the commercial term sheet for full break-up.", "Commercial"),
    ],
    "ecommerce": [
        ("What is your standard delivery timeline?", "Metro cities: 2–3 business days. Tier-2/3 cities: 4–6 business days. Remote pin codes may take up to 8 days. Live courier tracking is shared on dispatch.", "Shipping"),
        ("How do I return a product?", "Initiate return within 7 days of delivery via Returns & Refunds or by sharing your Order ID. We arrange free pickup within 48 hours for eligible SKUs.", "Returns"),
        ("What payment methods do you accept?", "UPI (GPay, PhonePe, Paytm), credit/debit cards, net banking, wallets, and Cash on Delivery on eligible pin codes (COD fee may apply).", "Payments"),
        ("How do I track my active order?", "Type Track Order with your 6-digit Order ID or registered mobile number. You will receive the courier AWB link and status.", "Tracking"),
        ("When will I receive my refund?", "Refunds are processed within 5–7 business days after the returned item passes QC. UPI/card refunds go to the original payment method; COD refunds use UPI/bank transfer.", "Refunds"),
        ("Do you ship internationally?", "Currently we ship within India only. International expansion is planned; join the waitlist via Customer Support.", "Shipping"),
        ("What is your exchange policy?", "Size/color exchanges are allowed once within 7 days if the item is unused with tags. Stock availability determines exchange vs store credit.", "Exchanges"),
        ("Are products covered under warranty?", "Warranty terms are listed per SKU (typically 1–2 years for electronics/accessories). Warranty covers manufacturing defects, not misuse or water damage unless stated.", "Warranty"),
        ("How do coupon codes work?", "Enter the code at checkout. Coupons cannot usually stack with other promos unless marked Stackable. One coupon per order.", "Offers"),
        ("What if my package arrives damaged?", "Refuse delivery if visibly damaged, or share unboxing photos within 24 hours. We arrange free replacement or full refund.", "Damages"),
        ("Can I cancel an order after placing it?", "Orders can be cancelled free of charge until packed. After dispatch, convert to return after delivery.", "Cancellations"),
        ("Do you offer gift wrapping?", "Gift wrap is available on select SKUs for a small fee. Add Gift Wrap in order notes or ask Support before dispatch.", "Gifting"),
        ("How is GST shown on invoices?", "All prices are inclusive of GST unless marked otherwise. Tax invoices are emailed and available under Track Order.", "Invoices"),
        ("What pin codes support Cash on Delivery?", "COD is enabled for most serviceable pin codes. Checkout will show COD availability; prepaid may be required for high-value or remote orders.", "Payments"),
    ],
    "it_software": [
        ("How do you estimate project costs?", "We scope features, integrations, user roles, non-functionals, and timeline, then propose fixed-bid, T&M, or dedicated squad pricing with a written SOW.", "Pricing"),
        ("Do you sign an NDA before discussions?", "Yes. Mutual NDAs are executed before reviewing architecture diagrams, codebases, or confidential product roadmaps.", "Security & IP"),
        ("Who owns the intellectual property (IP)?", "Clients own 100% of custom source code, designs, and project data upon settlement of agreed milestones, unless open-source components apply under their licenses.", "IP Ownership"),
        ("What post-launch maintenance do you provide?", "Every build includes 60 days complimentary warranty for defects introduced by us. Optional SLA retainers cover monitoring, patches, and feature velocity.", "Support"),
        ("Which engagement models do you offer?", "Fixed-price projects, time & materials, monthly dedicated teams, and outcome-based retainers for product pods.", "Engagement"),
        ("Do you work with existing internal teams?", "Yes. We embed with client engineering via shared repos, CI, and standups, or run as a parallel delivery stream with clear interface contracts.", "Delivery"),
        ("What is your typical discovery timeline?", "Paid discovery usually runs 1–2 weeks and produces UX flows, architecture options, backlog, and a budget-confidence estimate.", "Discovery"),
        ("Can you take over a legacy codebase?", "Yes. We run a structured audit (tests, deps, infra, security), then propose stabilization vs rewrite recommendations.", "Legacy"),
        ("How do you handle security and compliance?", "Secure SDLC practices, dependency scanning, secrets management, and optional SOC2/ISO-aligned controls depending on the engagement.", "Security & IP"),
        ("Do you deploy to our cloud accounts?", "Preferred model is deploy into the client’s AWS/GCP/Azure org with IaC (Terraform) and least-privilege access.", "Cloud"),
        ("What communication cadence should we expect?", "Weekly demos, shared Slack/Teams channel, written status notes, and a single accountable delivery lead.", "Delivery"),
        ("Do you provide UI/UX design?", "Yes — product design is available as a standalone track or bundled with engineering (wireframes, design system, handoff).", "Design"),
        ("How are change requests priced?", "Out-of-scope items are estimated in writing and approved before work starts; velocity trackers keep the backlog transparent.", "Pricing"),
        ("Can you help hire or train our team?", "We offer enablement workshops, pairing, and hiring scorecards as an optional professional-services add-on.", "Enablement"),
    ],
    "tours_travel": [
        ("Are flights included in the package cost?", "Packages are offered with or without flights. Flight-inclusive quotes depend on departure city, dates, and airline class.", "Flights"),
        ("What is your cancellation and refund policy?", "Cancel 21+ days before departure: typically 90% refund of land package. 7–20 days: partial refund per supplier rules. Inside 7 days: largely non-refundable unless travel insurance covers it.", "Refunds"),
        ("Do you assist with tourist visas?", "Yes. Our visa desk reviews documents, books appointments where needed, and tracks application status. Visa approval is always at the consulate’s discretion.", "Visa"),
        ("Can packages be customized for families?", "Yes — rooming, kid meals, accessibility needs, extra nights, and activity swaps can be tailored before booking confirmation.", "Customization"),
        ("What documents do travellers need?", "Valid passport (6+ months validity for international), tickets, hotel vouchers, travel insurance, and destination-specific forms. Domestic trips need government photo ID.", "Documents"),
        ("Is travel insurance mandatory?", "Strongly recommended for international trips; some packages bundle basic cover. Medical evacuation and trip cancellation add-ons are available.", "Insurance"),
        ("How do I pay for a booking?", "Booking amount secures seats; balance is due as per invoice schedule. We accept UPI, cards, net banking, and bank transfer. EMI options on select cards.", "Payments"),
        ("What if a flight is delayed or cancelled?", "We coordinate rebooking with airlines/hotels. Compensation follows airline policy; land arrangements are adjusted where possible.", "Disruptions"),
        ("Do prices include tourist taxes and resort fees?", "Inclusions are listed per package. City taxes, resort fees, and personal expenses are usually extra unless marked inclusive.", "Pricing"),
        ("Can you arrange honeymoon or group departures?", "Yes — honeymoon upgrades, private transfers, and group blocks with tour managers are available on request.", "Customization"),
        ("How early should I book peak-season travel?", "For Dec–Jan and school holidays, book 6–10 weeks ahead for better airfares and hotel inventory.", "Planning"),
        ("Are meals included every day?", "Meal plans vary (BB, MAP, AP). Daily inclusions are listed in the itinerary; special diets should be declared at booking.", "Meals"),
        ("Do you provide 24x7 emergency support on trip?", "Yes. Guests receive a destination duty phone for medical, lost passport, or logistics emergencies.", "Support"),
        ("What is the child / infant policy?", "Child rates depend on age and bed sharing. Infants usually travel free on land packages excluding flights and entrance fees.", "Family"),
    ],
    "healthcare": [
        ("How do I book an appointment with a doctor?", "Use Book Appointment or message the doctor/department name. You will get available slots; confirmation SMS/WhatsApp follows.", "Appointments"),
        ("How do I receive my diagnostic lab test reports?", "Reports are shared as PDF on WhatsApp/email typically within 12 hours for routine tests; specialized panels may take 24–48 hours.", "Lab Reports"),
        ("Do you accept insurance and cashless claims?", "Yes for listed TPAs and corporate tie-ups. Carry your e-card and photo ID. Planned procedures need pre-authorization.", "Insurance"),
        ("What should I do in case of a medical emergency?", "Call our 24/7 emergency hotline immediately for triage and ambulance dispatch. Share location and patient condition clearly.", "Emergency"),
        ("How early should I arrive for a consultation?", "Arrive 15 minutes early for registration and vitals. First-time patients should carry prior reports and medication list.", "Appointments"),
        ("Can I get a video consultation?", "Video consults are available for eligible specialties. Prescriptions are shared digitally; some cases still need in-person exam.", "Telehealth"),
        ("What payment modes are accepted at the clinic?", "UPI, cards, net banking, and cash. Insurance co-pay is collected as applicable.", "Payments"),
        ("How do I reschedule or cancel an appointment?", "Message at least 2 hours before the slot. Repeated no-shows may require advance payment for future bookings.", "Appointments"),
        ("Are health checkup packages customizable?", "Yes — packages can add/remove tests with price adjustment. Fasting instructions are sent with the booking confirmation.", "Packages"),
        ("Do you provide home sample collection?", "Home collection is available in selected pin codes for routine blood tests. Book via Lab Tests & Reports.", "Lab Reports"),
        ("Is parking available at the clinic?", "On-site visitor parking is available; wheelchair access is provided at the main entrance and lifts.", "Facilities"),
        ("How is patient data kept private?", "Records are access-controlled and shared only with treating clinicians or as authorized by the patient/guardian.", "Privacy"),
        ("Can I request a particular language-speaking doctor?", "We try to match language preference (English, Hindi, and regional languages) subject to doctor availability.", "Appointments"),
        ("What is the pharmacy / medicine policy?", "In-house pharmacy stocks commonly prescribed medicines. Bring outside prescriptions only if your clinician advises continuity.", "Pharmacy"),
    ],
    "banking": [
        ("How do I immediately block a lost or stolen card?", "Type Block Card or tap Block Lost Card and confirm the last 4 digits. Blocking is acknowledged by SMS usually within seconds.", "Card Security"),
        ("Can financial transactions be made through WhatsApp?", "No. This assistant helps with information, eligibility, and service requests only. Never share OTPs, PINs, or passwords here.", "Security Guardrail"),
        ("What documents are required to open a savings account?", "Aadhaar, PAN, and a photograph. Video KYC can often be completed online in minutes for eligible customers.", "Account Opening"),
        ("How do I submit an insurance claim?", "Use Insurance & Claims for the checklist, TPA contacts, and document upload guidance. Keep policy number and hospital bills ready.", "Claims"),
        ("How can I find my IFSC and branch details?", "Ask for your city or PIN, or use Locate Branch & ATM. IFSC is also printed on cheque books and account statements.", "Branch Info"),
        ("What is the minimum balance for Elite Savings?", "Average Monthly Balance of ₹10,000. Non-maintenance charges apply as per the schedule of charges.", "Accounts"),
        ("How do I activate net banking or mobile banking?", "Use the official bank app or net-banking portal after debit-card based activation. The chatbot will never ask for your password.", "Digital Banking"),
        ("What should I do if I see an unauthorized transaction?", "Block the card immediately, then raise a dispute ticket with date, amount, and merchant. Keep SMS alerts as evidence.", "Fraud"),
        ("Are senior citizens eligible for higher FD rates?", "Yes — senior citizen rates are published on the Smart Fixed Deposit scheme and may be ~0.50% higher.", "Deposits"),
        ("How long does home loan sanction take?", "Express Home Loan targets sanction in about 48 hours after complete documents and satisfactory verification.", "Loans"),
        ("Can I update my registered mobile number?", "Visit a branch with KYC or use authenticated channels in the official app. WhatsApp cannot change registered numbers alone.", "Profile"),
        ("What are branch working hours?", "Typically 09:30 AM – 05:00 PM on weekdays and 1st/3rd/5th Saturdays. Confirm for your branch as timings can vary.", "Branch Info"),
        ("Do you offer nomination facilities?", "Yes. Nomination can be registered for savings, deposits, and lockers as per bank policy.", "Accounts"),
        ("How do I download account statements?", "Use official net banking/app for PDF statements. The assistant can explain steps but cannot email statements without authenticated channels.", "Statements"),
    ],
    "finance": [
        ("How do I apply for a two-wheeler loan?", "Apply at a partner dealership or via the PLANET app/website. Instant in-principle approval is available on eligible profiles.", "Two-Wheeler"),
        ("What is the personal loan amount range?", "Typically ₹50,000 to ₹15 Lakhs (higher pre-approved offers may show in-app). Tenure usually 12–60 months.", "Personal Loan"),
        ("Do you finance electric two-wheelers?", "Yes — EV scooters and bikes are covered under two-wheeler finance on select models and partner dealers.", "Two-Wheeler"),
        ("What documents are needed for a personal loan?", "KYC (Aadhaar/PAN), income proofs (salary slips/ITR), and bank statements. Exact list depends on profile.", "Documents"),
        ("How fast is disbursal after approval?", "Personal loans are often credited within about 24 hours after digital verification. Dealer loans follow dealership timelines.", "Disbursal"),
        ("What gold purity is accepted for gold loans?", "Typically 18–22 karat household jewellery within RBI LTV norms. Valuation is done at the branch/partner location.", "Gold Loan"),
        ("Can I get a loan against property (LAP)?", "Yes — LAP is available on eligible residential/commercial property for business or liquidity needs, subject to underwriting.", "LAP"),
        ("Are interest rates guaranteed in chat?", "No. Published rates are indicative. Final rate depends on credit assessment and product scheme at sanction.", "Rates"),
        ("How do I raise a grievance?", "Use Raise Complaint in the menu or call customer care. Escalations follow the published grievance redressal process.", "Support"),
        ("Will the bot ever ask for OTP or MPIN?", "Never. Do not share OTP, MPIN, CVV, or passwords on chat. Report anyone asking for them immediately.", "Security"),
        ("Is balance transfer available on home loans?", "Yes — housing finance supports balance transfer with optional top-up subject to eligibility.", "Home Loan"),
        ("What is the tenure for two-wheeler loans?", "Usually 12–48 months; premium bikes may go up to 60 months depending on scheme.", "Two-Wheeler"),
        ("Can women borrowers get special concessions?", "Select two-wheeler schemes offer concessions for female co-borrowers — ask for the current scheme sheet.", "Offers"),
        ("How do I check loan eligibility?", "Use Check Eligibility / Apply Now and share basic income and city details. Final sanction is always after underwriting.", "Eligibility"),
    ],
    "generic": [
        ("What are your business operating hours?", "The digital assistant is available 24/7. Human support operates Monday–Friday, 9:00 AM–6:00 PM local time unless a holiday calendar says otherwise.", "Hours"),
        ("How can I request a customized quotation?", "Use Pricing & Quote or describe your requirements in chat. A specialist follows up with a written estimate.", "Quotes"),
        ("What is your refund or cancellation policy?", "New subscriptions may cancel within 14 days for a full refund if onboarding deliverables are unused. After that, billing follows the contract notice period.", "Refunds"),
        ("How do I contact a senior representative?", "Use Schedule a Callback and pick a slot, or ask for a human agent — we escalate with your ticket summary.", "Contact"),
        ("Where can I see product feature comparisons?", "Ask for a comparison of Standard vs Professional tiers, or open Our Offerings for the catalog summary.", "Products"),
        ("Do you offer onboarding and training?", "Yes. Custom Consultation & Setup includes configuration and a team training session; extra workshops can be quoted.", "Onboarding"),
        ("How is customer data protected?", "We apply role-based access, encryption in transit, and tenant isolation. Detailed security summaries are available on request.", "Security"),
        ("Can I integrate with my existing tools?", "Professional tier includes standard integrations; custom APIs are scoped as professional services.", "Integrations"),
        ("What SLAs do you provide?", "Professional plans include priority support SLAs (response targets in the order form). Standard plans use business-hours email/chat support.", "Support"),
        ("How do license seats work?", "Standard includes up to 5 seats; Professional is unlimited seats under fair-use. Extra admin seats can be added on Standard.", "Licensing"),
        ("Do you support multi-location businesses?", "Yes — multi-branch profiles and localized menus can be configured during onboarding.", "Setup"),
        ("How do I report a bug or outage?", "Raise a ticket via Customer Support with screenshots and time of issue. Critical outages are escalated immediately.", "Support"),
        ("Is there a long-term contract requirement?", "Month-to-month and annual plans are both available; annual plans usually include a discount.", "Pricing"),
        ("Can I white-label the experience?", "White-label options are available on enterprise agreements — ask Sales for branding guidelines and feasibility.", "Branding"),
    ],
}


KB_BY_VERTICAL: Dict[str, List[KbArticle]] = {
    "real_estate": [
        (
            "Home Buying Journey & Booking Process",
            "Policies",
            "# Home Buying Journey\n\n"
            "1. **Discover** — Browse catalog properties and shortlist by location, configuration, and budget.\n"
            "2. **Site visit** — Schedule a complimentary cab visit; collect cost sheet and brochure.\n"
            "3. **Booking** — Pay booking advance, complete KYC, and lock the unit.\n"
            "4. **Agreement** — Sign builder-buyer agreement; registration as per state rules.\n"
            "5. **Milestones** — Follow construction-linked payments; keep receipts.\n"
            "6. **Possession** — Snagging, OC verification, handover kit, and society onboarding.\n\n"
            "Always rely on RERA IDs and sanctioned plans over marketing creatives.",
        ),
        (
            "Home Loan & NRI Purchase Guide",
            "Home Loans",
            "# Home Loans & NRI Buying\n\n"
            "Partner banks typically finance 80–90% of agreement value subject to eligibility.\n"
            "Salaried buyers should keep salary slips, Form 16, and bank statements ready.\n"
            "Self-employed buyers need ITR, business proofs, and financials.\n\n"
            "NRIs can remit via NRE/NRO accounts. Power of attorney may be used for registration "
            "with our documentation desk guidance. Tax implications vary — consult your CA for TDS on property.",
        ),
        (
            "RERA, Legal Checks & Customer Support",
            "Legal",
            "# Legal & Support\n\n"
            "Every listed project carries a RERA ID in the catalog. Buyers should verify registration "
            "on the state RERA portal and review sanctioned layout plans.\n\n"
            "Post-sales support handles payment receipts, demand letters, and possession coordination. "
            "Share your booking ID when raising tickets for faster resolution.",
        ),
    ],
    "ecommerce": [
        (
            "Shipping, Delivery & Order Tracking Policy",
            "Shipping",
            "# Shipping & Tracking\n\n"
            "Orders are processed within 24 hours on business days. Metro deliveries average 2–3 days; "
            "other regions 4–6 days. An AWB tracking link is sent on dispatch.\n\n"
            "If a package shows Delivered but is missing, contact Support within 48 hours with photos "
            "of the delivery location. We coordinate with the courier for traces and resolution.",
        ),
        (
            "Returns, Exchanges, Refunds & Warranty",
            "Returns",
            "# Returns & Warranty\n\n"
            "Most SKUs allow returns within 7 days if unused with original tags and packaging. "
            "Personal-care items may be non-returnable for hygiene once unsealed — check the product page.\n\n"
            "Refunds complete in 5–7 business days after QC. Warranty covers manufacturing defects only; "
            "keep the invoice and serial number for claims.",
        ),
        (
            "Payments, COD, Coupons & Invoicing",
            "Payments",
            "# Payments & Offers\n\n"
            "Accepted modes: UPI, cards, net banking, wallets, and COD where enabled. "
            "Coupon codes apply at checkout and usually do not stack.\n\n"
            "GST-inclusive invoices are emailed automatically. For GSTIN business invoices, "
            "share your GST details in order notes before dispatch.",
        ),
    ],
    "it_software": [
        (
            "Engagement Models, SOW & Change Control",
            "Delivery",
            "# How We Engage\n\n"
            "We deliver via fixed-price, time & materials, or dedicated squads. Every engagement starts "
            "with a written SOW covering scope, milestones, acceptance criteria, and commercial terms.\n\n"
            "Change requests are estimated and approved in writing before implementation so budgets stay predictable.",
        ),
        (
            "Security, NDA & Intellectual Property",
            "Security & IP",
            "# Security & IP\n\n"
            "Mutual NDAs precede deep technical discussions. Custom code and designs transfer to the client "
            "after milestone payments, excluding third-party/open-source components which keep their licenses.\n\n"
            "Access is least-privilege; secrets stay in vaults; production access is logged.",
        ),
        (
            "Support Warranty & SLA Retainers",
            "Support",
            "# After Go-Live\n\n"
            "Projects include 60 days warranty for defects attributable to our delivery. "
            "Ongoing SLAs can cover uptime monitoring, dependency patches, and a monthly feature capacity.\n\n"
            "Severity-1 production incidents get priority response under active retainer terms.",
        ),
    ],
    "tours_travel": [
        (
            "Booking, Payments & Travel Documents Checklist",
            "Planning",
            "# Booking Checklist\n\n"
            "Confirm destination dates, traveler names as per passport, rooming, and meal plan. "
            "Pay the booking amount to hold space; clear the balance per invoice timeline.\n\n"
            "Carry passport (6+ months validity for international), tickets, vouchers, insurance, "
            "and any destination forms. Domestic travelers need government photo ID.",
        ),
        (
            "Cancellation, Reschedule & Travel Insurance",
            "Refunds",
            "# Cancellations & Insurance\n\n"
            "Land-package refunds generally: 90% if cancelled 21+ days prior; reduced thereafter; "
            "limited inside 7 days. Airline tickets follow airline fare rules.\n\n"
            "Travel insurance is strongly recommended for medical emergencies, baggage loss, and trip interruption.",
        ),
        (
            "Visa Assistance & On-Trip Emergency Support",
            "Visa",
            "# Visas & Support\n\n"
            "Our visa desk helps with document checklists and appointments. Final approval is always "
            "the consulate’s decision — never guarantee outcomes.\n\n"
            "On trip, guests receive a 24x7 duty number for hotel, medical, or document emergencies.",
        ),
    ],
    "healthcare": [
        (
            "Appointments, Telehealth & Clinic Visit Guide",
            "Appointments",
            "# Visiting CareWell\n\n"
            "Book via WhatsApp menu or by naming the specialty. Arrive 15 minutes early with prior reports "
            "and a medication list. First-time patients complete a short registration form.\n\n"
            "Video consultations are available for eligible cases; some conditions still require physical examination.",
        ),
        (
            "Lab Tests, Reports & Health Packages",
            "Diagnostics",
            "# Labs & Packages\n\n"
            "Routine reports are typically shared within 12 hours as PDF. Specialized tests may take longer. "
            "Home sample collection is available in selected pin codes.\n\n"
            "Health packages can be customized; fasting instructions are sent with confirmation messages.",
        ),
        (
            "Insurance Cashless, Emergency & Privacy",
            "Insurance",
            "# Insurance & Emergency\n\n"
            "Cashless care is available with listed TPAs — carry e-card and ID; planned procedures need pre-auth.\n\n"
            "For emergencies dial the 24/7 hotline for triage and ambulance. Patient records are confidential "
            "and shared only with care teams or authorized persons.",
        ),
    ],
    "banking": [
        (
            "Card Safety, Fraud Response & Digital Banking Guardrails",
            "Security",
            "# Stay Safe\n\n"
            "Block lost cards immediately via the menu. Never share OTP, PIN, CVV, or passwords in chat.\n\n"
            "This WhatsApp assistant does not move money. Use official apps/net banking for payments. "
            "Report unauthorized transactions at once with amount, time, and merchant details.",
        ),
        (
            "Accounts, Deposits, Cards & Loans Overview",
            "Products",
            "# Product Guide\n\n"
            "Elite Savings offers higher interest with AMB requirements and lifestyle benefits. "
            "Fixed deposits support flexible tenures and senior-citizen rate upsides.\n\n"
            "CashBack cards and Express Home Loans have published eligibility — ask for the latest rate sheet "
            "and document checklist before applying.",
        ),
        (
            "Claims, Branch Locator & Service Requests",
            "Service",
            "# Everyday Banking Help\n\n"
            "Insurance claims follow the checklist under Insurance & Claims. Branch/ATM locator helps with "
            "IFSC and timings (typically weekdays + alternate Saturdays).\n\n"
            "Service requests (statements, nomination, mobile update) may require authenticated banking channels "
            "or a branch visit for regulatory compliance.",
        ),
    ],
    "finance": [
        (
            "ITR Filing Document Checklist & Timeline",
            "ITR",
            "# ITR Prep\n\n"
            "Share Form 16, 26AS, AIS/TIS, interest certificates, capital-gains reports, and Chapter VI-A proofs. "
            "Salaried returns usually complete in 2–4 business days after docs are complete.\n\n"
            "NRI and capital-gains heavy returns need extra schedules — flag them early in the engagement.",
        ),
        (
            "GST Compliance, Notices & Multi-State Ops",
            "GST",
            "# GST Operations\n\n"
            "Monthly retainers cover GSTR-1/3B, ITC reconciliation, and notice responses. "
            "Multi-state registrations and filings are supported for pan-India businesses.\n\n"
            "Clients must share purchase/sales data on the agreed cutoff to avoid late fees.",
        ),
        (
            "Virtual CFO, Audit & Data Security Practices",
            "Advisory",
            "# Advisory & Security\n\n"
            "Virtual CFO retainers include MIS, cash-flow visibility, and board summaries as scoped. "
            "Statutory/internal audits are scheduled with clear PBC lists.\n\n"
            "Documents should be uploaded via secure links only. All engagements are under NDA with encrypted storage.",
        ),
    ],
    "generic": [
        (
            "Getting Started, Plans & Onboarding",
            "Onboarding",
            "# Getting Started\n\n"
            "Choose Standard or Professional based on seats and support needs. Onboarding includes "
            "configuration help; Custom Consultation adds training and architecture review.\n\n"
            "Share your success metrics early so we tailor menus, FAQs, and automations to your workflows.",
        ),
        (
            "Support SLAs, Escalations & Refund Policy",
            "Support",
            "# Support & Refunds\n\n"
            "Human support runs business hours; the bot is 24/7. Ask for a human agent anytime for grievances.\n\n"
            "New subscriptions may cancel within 14 days for a full refund if deliverables are unused. "
            "Afterwards, cancellations follow the contractual notice period.",
        ),
        (
            "Security, Integrations & Data Isolation",
            "Security",
            "# Platform Trust\n\n"
            "Tenant data is isolated with role-based access and encryption in transit. "
            "Professional plans unlock standard integrations; custom APIs are quoted separately.\n\n"
            "Request our security summary for enterprise questionnaires and DPIA support.",
        ),
    ],
}


def _slug_seed(text: str) -> str:
    keep = "".join(ch.lower() if ch.isalnum() else "-" for ch in (text or "item"))
    while "--" in keep:
        keep = keep.replace("--", "-")
    return keep.strip("-")[:48] or "item"


def ensure_catalog_image_column(configs: Dict[str, Dict[str, Any]]) -> None:
    """Add Image URL column + sample public image links on every catalog row."""
    for key, cfg in configs.items():
        cols: List[str] = list(cfg.get("catalog_columns") or [])
        if not any("image" in c.lower() or "media" in c.lower() for c in cols):
            cols.append("Image URL")
        cfg["catalog_columns"] = cols
        image_idx = next(
            i for i, c in enumerate(cols) if "image" in c.lower() or "media" in c.lower()
        )
        tenant = cfg.get("default_tenant") or key
        rows = []
        for row in cfg.get("catalog_rows") or []:
            cells = list(row)
            while len(cells) < image_idx:
                cells.append("")
            name = str(cells[0]) if cells else "item"
            sample = f"https://picsum.photos/seed/{tenant}-{_slug_seed(name)}/800/600"
            if len(cells) == image_idx:
                cells.append(sample)
            elif not str(cells[image_idx]).strip():
                cells[image_idx] = sample
            # Keep existing real https URLs (company examples) as-is
            rows.append(cells)
        cfg["catalog_rows"] = rows


def enrich_vertical_configs(configs: Dict[str, Dict[str, Any]]) -> None:
    """Attach expanded FAQs + KB articles. Image column filled after company overlay."""
    for key, cfg in configs.items():
        if key in FAQ_BY_VERTICAL:
            cfg["faq_rows"] = FAQ_BY_VERTICAL[key]
        if key in KB_BY_VERTICAL:
            cfg["kb_articles"] = KB_BY_VERTICAL[key]
