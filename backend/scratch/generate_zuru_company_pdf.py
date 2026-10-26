"""Properly formatted ZURU Toys / Zuru Tech company PDF for upload testing."""

from pathlib import Path

import fitz

OUT = Path(__file__).resolve().parents[2] / "ZURU_Toys_Company_Pack.pdf"
DESKTOP = Path.home() / "Desktop" / "ZURU_Toys_Company_Pack.pdf"

# Colors
RED = (0.545, 0, 0)  # ZURU-ish dark red
GOLD = (0.85, 0.65, 0.05)
DARK = (0.12, 0.12, 0.14)
GRAY = (0.35, 0.35, 0.38)
LIGHT = (0.96, 0.95, 0.94)
WHITE = (1, 1, 1)


def new_page(doc):
    return doc.new_page(width=595, height=842)


def draw_header(page, title, subtitle=None):
    page.draw_rect(fitz.Rect(0, 0, 595, 72), color=RED, fill=RED)
    page.insert_text((36, 32), "ZURU TOYS", fontsize=11, fontname="helv", color=GOLD)
    page.insert_text((36, 52), title, fontsize=16, fontname="helv", color=WHITE)
    if subtitle:
        page.insert_text((36, 68), subtitle, fontsize=8, fontname="helv", color=WHITE)
    page.draw_rect(fitz.Rect(0, 72, 595, 76), color=GOLD, fill=GOLD)


def draw_footer(page, n, total):
    page.insert_text(
        (36, 820),
        f"ZURU Toys Company Pack  |  Confidential chatbot knowledge  |  Page {n}/{total}",
        fontsize=8,
        fontname="helv",
        color=GRAY,
    )


def body_text(page, text, y, fontsize=10, color=DARK, max_width=523):
    """Write wrapped text starting at y; return next y."""
    rect = fitz.Rect(36, y, 36 + max_width, 800)
    overflow = page.insert_textbox(rect, text, fontsize=fontsize, fontname="helv", color=color, align=0)
    # insert_textbox returns unused height leftover (negative if overflow)
    # Estimate used height from lines
    lines = max(1, text.count("\n") + 1)
    used = lines * (fontsize + 3)
    return y + used + 6


def section_title(page, text, y):
    page.draw_rect(fitz.Rect(36, y, 559, y + 22), color=LIGHT, fill=LIGHT)
    page.insert_text((44, y + 15), text, fontsize=11, fontname="helv", color=RED)
    return y + 30


def kv_block(page, rows, y):
    for label, value in rows:
        page.insert_text((44, y), f"{label}:", fontsize=9, fontname="helv", color=GRAY)
        page.insert_text((160, y), value, fontsize=9, fontname="helv", color=DARK)
        y += 14
    return y + 6


def product_card(page, y, idx, name, brand, category, price, short, desc):
    box_h = 78
    if y + box_h > 790:
        return None  # signal need new page
    page.draw_rect(fitz.Rect(36, y, 559, y + box_h), color=(0.88, 0.88, 0.9), fill=WHITE)
    page.draw_rect(fitz.Rect(36, y, 40, y + box_h), color=RED, fill=RED)
    page.insert_text((50, y + 14), f"{idx}. {name}", fontsize=10, fontname="helv", color=DARK)
    page.insert_text(
        (50, y + 28),
        f"Brand: {brand}  |  Category: {category}  |  Price: {price}",
        fontsize=8,
        fontname="helv",
        color=RED,
    )
    page.insert_text((50, y + 42), f"Short: {short}", fontsize=8, fontname="helv", color=GRAY)
    # wrap description
    page.insert_textbox(
        fitz.Rect(50, y + 48, 545, y + box_h - 4),
        f"Description: {desc}",
        fontsize=8,
        fontname="helv",
        color=DARK,
    )
    return y + box_h + 8


def faq_pair(page, y, q, a):
    need = 36 + (len(a) // 90) * 11
    if y + need > 790:
        return None
    page.insert_text((44, y), f"Q: {q}", fontsize=9, fontname="helv", color=RED)
    y += 12
    used = page.insert_textbox(
        fitz.Rect(44, y, 555, y + 60),
        f"A: {a}",
        fontsize=9,
        fontname="helv",
        color=DARK,
    )
    # approximate advance
    lines = max(1, (len(a) // 95) + 1)
    return y + lines * 11 + 10


def build():
    doc = fitz.open()
    pages_meta = []

    # ── Page 1: Brand / Company ─────────────────────────────────────────
    page = new_page(doc)
    draw_header(page, "Company Profile & Brand", "For chatbot auto-bifurcation upload")
    y = 92
    y = section_title(page, "1. Brand & Profile (extract into tenant Profile)", y)
    y = kv_block(
        page,
        [
            ("Company Name", "ZURU Toys"),
            ("Parent Organization", "ZURU Group"),
            ("Bot Name", "ZURU Helper"),
            ("Brand Tagline", "Play Reimagined."),
            ("Website", "https://zurutoys.com/"),
            ("Support Email", "india@zuru.com"),
            ("Support Phone", "+91 81288 64506"),
            ("Signature", "ZURU Toys — Play Reimagined."),
            ("Industry / Vertical", "ecommerce"),
            ("Timezone", "Asia/Kolkata"),
            ("Business Hours", "09:00 – 21:00, Monday–Saturday"),
        ],
        y,
    )
    y = section_title(page, "2. Company Overview (Knowledge Base)", y)
    overview = (
        "ZURU Toys is a global toy company focused on creativity, innovation, imaginative play, "
        "and accessible products for children and families. The company uses automation, "
        "manufacturing capabilities, and product innovation to develop toys for international markets. "
        "ZURU distributes its products through major retailers in more than 120 countries.\n\n"
        "Mission and values: encourage imagination and creative play; develop engaging and innovative "
        "toys; improve product quality and affordability; use automation and manufacturing innovation; "
        "support responsible business practices and sustainability.\n\n"
        "Official links: Website https://zurutoys.com/ | Contact https://zurutoys.com/contact/ | "
        "About https://zurutoys.com/about/ | ZURU Tech www.zuru.tech"
    )
    page.insert_textbox(fitz.Rect(44, y, 555, 780), overview, fontsize=9, fontname="helv", color=DARK)
    draw_footer(page, 1, 6)
    pages_meta.append(page)

    # ── Page 2: Brands KB ───────────────────────────────────────────────
    page = new_page(doc)
    draw_header(page, "Brand Portfolio", "Knowledge base — main toy brands")
    y = 92
    y = section_title(page, "3. Main Toy Brands (Knowledge Base article)", y)
    brands = [
        ("XSHOT", "Toy blasters for active play. Features, ages, accessories vary by model."),
        ("Mini Brands", "Miniature collectibles inspired by consumer goods and licensed brands."),
        ("Rainbocorns", "Colorful surprise toys and plush characters with reveal-based play."),
        ("Pets Alive", "Interactive animal-inspired toys; features depend on the product."),
        ("Robo Alive", "Robotic / lifelike animal toys with movement and sound features."),
        ("Bunch O Balloons", "Outdoor water toys that simplify filling water balloons."),
        ("Fuggler", "Collectible plush with unusual character designs."),
        ("Smashers", "Surprise discovery toys with themed unboxing play."),
        ("5 Surprise", "Mystery collectible capsules with varying series contents."),
        ("Snackles", "Soft food-inspired plush characters."),
    ]
    for name, desc in brands:
        page.insert_text((44, y), name, fontsize=9, fontname="helv", color=RED)
        page.insert_textbox(fitz.Rect(140, y - 8, 555, y + 24), desc, fontsize=8, fontname="helv", color=DARK)
        y += 28
    y += 4
    y = section_title(page, "4. Policies (Knowledge Base)", y)
    policies = (
        "Product availability, prices, packaging, colors, accessories, and features may vary by region "
        "and retailer. Customers should check local retailers for current prices, stock, shipping, "
        "payment methods, and returns.\n\n"
        "Safety: follow age recommendations and warnings on packaging. Keep small parts away from "
        "young children. Do not use damaged toys. Water toys need supervision. The chatbot must not "
        "invent age ratings, warranties, refunds, or spare-part guarantees.\n\n"
        "Support data to collect: product name and brand, item/model number, date and place of purchase, "
        "issue description, photos, proof of purchase."
    )
    page.insert_textbox(fitz.Rect(44, y, 555, 800), policies, fontsize=9, fontname="helv", color=DARK)
    draw_footer(page, 2, 6)
    pages_meta.append(page)

    # ── Pages 3–4: Products ─────────────────────────────────────────────
    products = [
        ("XSHOT Excel Crusher Blaster", "XSHOT", "Action toy", "Rs. 7,700",
         "Dart blaster with large capacity.",
         "Dart blaster with a 48-dart capacity designed for active outdoor play."),
        ("XSHOT Skins Pro Series Sinister", "XSHOT", "Action toy", "Rs. 5,400",
         "Skins-range toy blaster.",
         "Toy blaster from the XSHOT Skins Pro Series Sinister range."),
        ("XSHOT Fast-Fill Water Blaster, 2-pack", "XSHOT", "Outdoor toy", "Rs. 1,545",
         "Two outdoor water blasters.",
         "Two water blasters designed for outdoor water play with fast-fill design."),
        ("Rainbocorns Pupycorn Surprise", "Rainbocorns", "Surprise / plush toy", "Rs. 1,999",
         "Puppy-inspired surprise toy.",
         "Surprise toy featuring a puppy-inspired character with reveal play."),
        ("Rainbocorns Eggzania Mini Mania", "Rainbocorns", "Surprise / collectible toy", "Rs. 5,000",
         "Multi-reveal surprise collection.",
         "Surprise collection with multiple reveal items in the Eggzania Mini Mania line."),
        ("Robo Alive Deep Sea Monster Surprise", "Robo Alive", "Interactive toy", "Rs. 4,499",
         "Octopus-themed surprise toy.",
         "Octopus-themed surprise toy from the Robo Alive Deep Sea Monster range."),
        ("Robo Alive Water-Activated Swimming Shark", "Robo Alive", "Interactive / water toy", "Rs. 1,999",
         "Water-activated robotic shark.",
         "Water-activated robotic swimming shark for supervised water play."),
        ("Pets Alive Fifi the Flossing Sloth", "Pets Alive", "Interactive plush toy", "Rs. 5,999",
         "Dancing interactive sloth.",
         "Interactive sloth toy featuring dance movements and music."),
        ("5 Surprise My Mini Baby, Series 1", "5 Surprise", "Collectible toy", "Rs. 1,599",
         "Mystery baby-themed capsule.",
         "Mystery capsule featuring miniature baby-themed collectibles, Series 1."),
        ("Fuggler Old Fogies, 22 cm", "Fuggler", "Plush collectible", "Rs. 2,735",
         "Monster-style plush character.",
         "Unusual monster-style plush character, approximately 22 cm."),
        ("Smashers Dino vs Aliens", "Smashers", "Surprise / dinosaur toy", "Rs. 5,995",
         "Dinosaur surprise discovery toy.",
         "Dinosaur-themed surprise toy for discovery-based smash-and-reveal play."),
        ("5 Surprise Dino Strike Mystery Ball", "5 Surprise", "Dinosaur collectible", "Rs. 2,189",
         "Dinosaur mystery capsule.",
         "Dinosaur-themed mystery capsule from the Dino Strike series."),
    ]

    page = new_page(doc)
    draw_header(page, "Product Catalog", "Extract each item into Offerings / Products")
    y = 92
    y = section_title(page, "5. Products & Offerings (live catalog)", y)
    page_num = 3
    idx = 1
    for p in products:
        nxt = product_card(page, y, idx, *p)
        if nxt is None:
            draw_footer(page, page_num, 6)
            pages_meta.append(page)
            page = new_page(doc)
            page_num += 1
            draw_header(page, "Product Catalog (continued)", "Offerings")
            y = 92
            nxt = product_card(page, y, idx, *p)
        y = nxt
        idx += 1
    draw_footer(page, page_num, 6)
    pages_meta.append(page)

    # ── FAQs ────────────────────────────────────────────────────────────
    faqs = [
        ("What is ZURU Toys?",
         "ZURU Toys is a global toy company that develops and distributes toys and play products."),
        ("What are ZURU's popular toy brands?",
         "XSHOT, Mini Brands, Rainbocorns, Pets Alive, Robo Alive, Bunch O Balloons, Fuggler, Smashers, 5 Surprise, and Snackles."),
        ("Where can I buy ZURU toys?",
         "Through major retailers and channels listed on https://zurutoys.com/. Availability varies by country."),
        ("How can I find a toy's price?",
         "Check the retailer listing for the exact product and country. Prices vary by region and store."),
        ("How do I report a damaged toy?",
         "Keep proof of purchase, photograph the damage, and contact the retailer or official support."),
        ("How do I find the correct age recommendation?",
         "Check the packaging and instructions for that specific product. Do not invent age ratings."),
        ("Are all ZURU toys available in every country?",
         "No. Availability depends on country, retailer, distribution, and stock."),
        ("What should I do if a toy is missing a piece?",
         "Contact support with product name, item number, purchase details, and missing part description."),
        ("Can I use rechargeable batteries?",
         "Only when the product instructions allow it. Match the required battery type and voltage."),
        ("Does ZURU provide a warranty?",
         "Warranty depends on product, country, and terms. Check documentation or contact support."),
        ("How can I contact ZURU in India?",
         "Ahmedabad: +91 81288 64506, india@zuru.com. Kolkata: +91 90383 84033."),
        ("What is ZURU Tech?",
         "ZURU Tech is the technology arm of ZURU. Website: www.zuru.tech. Careers: careers.tech@zuru.com."),
        ("Can retailers inquire about selling ZURU products?",
         "Yes. Contact ZURU through the official website for distribution and commercial enquiries."),
        ("What information should I give customer support?",
         "Product name and brand, item/model number, purchase date/place, issue description, photos, and proof of purchase."),
    ]

    page = new_page(doc)
    draw_header(page, "Frequently Asked Questions", "Extract each Q/A into FAQ index")
    y = 92
    y = section_title(page, "6. FAQs", y)
    faq_page = page_num + 1
    for q, a in faqs:
        nxt = faq_pair(page, y, q, a)
        if nxt is None:
            draw_footer(page, faq_page, 6)
            pages_meta.append(page)
            page = new_page(doc)
            faq_page += 1
            draw_header(page, "FAQs (continued)", "FAQ index")
            y = 92
            nxt = faq_pair(page, y, q, a)
        y = nxt
    draw_footer(page, faq_page, 6)
    pages_meta.append(page)

    # ── Menu & chatbot config ───────────────────────────────────────────
    page = new_page(doc)
    draw_header(page, "WhatsApp Menu & Chatbot Rules", "Menu buttons + guardrails")
    y = 92
    y = section_title(page, "7. Suggested WhatsApp Menu (titles <= 24 chars)", y)
    menus = [
        ("Browse Toys", "Explore catalog and bestsellers", "Explore"),
        ("Our Brands", "XSHOT, Rainbocorns, and more", "Explore"),
        ("Where to Buy", "Retailers and purchase options", "Explore"),
        ("Product Safety", "Age guidance and safe play tips", "Help"),
        ("Returns Help", "Damaged, missing parts, warranty", "Help"),
        ("Talk to Support", "Contact ZURU customer care", "Support"),
    ]
    for title, desc, sec in menus:
        page.insert_text((44, y), f"• {title}", fontsize=9, fontname="helv", color=RED)
        page.insert_text((160, y), f"{desc}  [{sec}]", fontsize=8, fontname="helv", color=DARK)
        y += 16
    y += 8
    y = section_title(page, "8. Chatbot Configuration", y)
    y = kv_block(
        page,
        [
            ("Chatbot Name", "ZURU Helper"),
            ("Welcome Message", "Hello! Welcome to ZURU Toys. How can I help you today?"),
            ("Fallback", "I don't have that information. Let me connect you to support."),
            ("Primary Color", "#8B0000"),
            ("Secondary Color", "#FFD700"),
        ],
        y,
    )
    y = section_title(page, "9. Guardrails", y)
    rules = (
        "• Answer only from this knowledge pack and live catalog.\n"
        "• Never invent prices, stock, warranties, age ratings, or refunds.\n"
        "• Never invent job openings or partnership terms.\n"
        "• Ask for product name/model when unclear.\n"
        "• Prefer https://zurutoys.com/ for current company information.\n"
        "• Escalate unresolved safety or warranty questions to support."
    )
    page.insert_textbox(fitz.Rect(44, y, 555, 780), rules, fontsize=9, fontname="helv", color=DARK)
    draw_footer(page, faq_page + 1, 6)
    pages_meta.append(page)

    # Fix footers with real total
    total = len(doc)
    for i, pg in enumerate(doc, 1):
        # wipe old footer area lightly
        pg.draw_rect(fitz.Rect(30, 808, 565, 830), color=WHITE, fill=WHITE)
        draw_footer(pg, i, total)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUT)
    doc.close()

    import shutil
    shutil.copy2(OUT, DESKTOP)
    print(f"Wrote {OUT}")
    print(f"Copied {DESKTOP}")
    print(f"pages={total} size={OUT.stat().st_size}")


if __name__ == "__main__":
    build()
