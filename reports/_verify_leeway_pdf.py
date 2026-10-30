import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]

from services.auto_bifurcator import AutoBifurcator

p = ROOT / "reports" / "leeway_softech_it_onboarding_kit.pdf"
print("size_bytes", p.stat().st_size)
doc = fitz.open(p)
print("pages", doc.page_count)
text = "\n".join(page.get_text() for page in doc)
for marker in (
    "[SECTION: BRAND",
    "[SECTION: WHATSAPP",
    "[SECTION: CATALOG",
    "[SECTION: FAQS",
    "[SECTION: INFO",
    "[SECTION: BOT",
):
    print(marker, "OK" if marker in text else "MISSING")
print("embedded_images", sum(len(page.get_images()) for page in doc))

tables = []
for page in doc:
    try:
        for t in page.find_tables().tables:
            tables.append([[(c or "") for c in row] for row in t.extract()])
    except Exception:
        pass

extracted = [{"text": text, "tables": tables, "filename": p.name, "ext": "pdf"}]
b = AutoBifurcator("leewaysoftech")
sections = b.partition_sections(extracted)
for key, val in sections.items():
    print(
        f"section {key}: text={len(val.get('text') or '')} tables={len(val.get('tables') or [])}"
    )

menu = b.extract_menu_section(sections["menu"], vertical="it_software")
print("menu_count", len(menu))
print("menu_titles", [m.get("title") for m in menu])
brand, _hours, vertical, _extras = b.extract_brand_section(
    sections["brand"], default_vertical="it_software"
)
print(
    "brand",
    brand.get("name"),
    vertical,
    brand.get("support_phone"),
    brand.get("website"),
)

# Catalog extraction method name varies
offerings = b.extract_catalog_section(sections["catalog"], vertical="it_software")
print("offerings_count", len(offerings))
ok_urls = 0
for o in offerings:
    url = o.get("media_url") or ""
    if "leewaysoftech.com" in url and url.endswith((".webp", ".png", ".jpg")):
        ok_urls += 1
    print("  -", o.get("name"), "|", o.get("price"), "|", url)
print("menu", len(menu), "offerings", len(offerings), "good_image_urls", ok_urls)
print("PASS" if len(menu) == 10 and len(offerings) >= 8 and ok_urls >= 6 and brand.get("name") else "FAIL")
