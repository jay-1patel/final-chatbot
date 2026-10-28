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
