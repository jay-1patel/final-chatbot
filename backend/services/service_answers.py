"""Deterministic, tenant-scoped replies for service enquiries."""

from __future__ import annotations

import logging
import re

logger = logging.getLogger("services.service_answers")

SERVICE_QUERY_PHRASES = (
    "service", "services", "serevice", "serevices", "servise", "servises", "servie", "servies",
    "offering", "offerings", "what do you do",
    "what do you offer", "what services", "service brochure", "brochure of services",
    "package", "packages", "tour package", "tour packages", "tours", "destinations",
    "product", "products", "banking products", "what products", "list products",
    "project", "projects", "ongoing project", "ongoing projects", "explore properties", "property", "properties",
    "ongoing", "developments",
)
BROAD_SERVICE_PHRASES = (
    "our services", "your services", "what services", "list services",
    "our serevices", "your serevices", "our servises", "your servises",
    "services do you offer", "what do you offer", "tell me about your services",
    "what service do you", "service do you provide", "services do you provide",
    "service brochure", "brochure of services",
    "our packages", "your packages", "what packages", "list packages",
    "tour packages", "packages do you offer", "tell me about your packages",
    "our products", "your products", "what products", "list products",
    "products do you offer", "banking products",
    "ongoing projects", "ongoing project", "our projects", "your projects", "what projects", "list projects",
    "explore properties", "our properties", "your properties", "list properties", "what properties",
)


def is_service_query(text: str) -> bool:
    query = (text or "").strip().lower()
    return any(phrase in query for phrase in SERVICE_QUERY_PHRASES)


def _fit_description(text: str, limit: int = 1200) -> str:
    """Trim a description without slicing a word or sentence in half.

    A plain ``text[:limit]`` cuts mid-word, so trim at
    the end of a sentence when possible, then at the last whole word.
    """
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    window = text[:limit]
    sentence_end = max(window.rfind("."), window.rfind("!"), window.rfind("?"))
    if sentence_end >= limit // 2:
        return window[: sentence_end + 1].rstrip()
    space = window.rfind(" ")
    if space >= limit // 2:
        window = window[:space]
    return window.rstrip()


def answer_for_text(wa_id: str, text: str, tenant_id: str | None = None) -> str | None:
    """Return only configured service records for a recognized service query."""
    query = (text or "").strip()
    if not query:
        return None

    try:
        from shared.tenancy.loader import get_tenant_profile
        from shared.tenancy.resolver import resolve_tenant_for_user
        from shared.tenancy.intent_match import match_by_rules
        try:
            from backend.database import list_products
        except ImportError:
            from database import list_products

        tid = tenant_id or resolve_tenant_for_user(wa_id or "")
        profile = get_tenant_profile(tid)
        vocab = getattr(profile, "vocabulary", None)
        vertical = getattr(profile, "vertical", "generic") or "generic"
        if vertical in ("real_estate", "construction"):
            item_noun = "projects"
        elif vertical in ("tours_travel", "tourism"):
            item_noun = "packages"
        elif vertical in ("banking", "retail", "ecommerce"):
            item_noun = "products"
        else:
            item_noun = (getattr(vocab, "item_noun", "services") if vocab else "services") or "services"
        intent = (
            profile.intent("service_enquiry")
            or profile.intent("property_listings")
            or profile.intent("project_details")
            or profile.intent("product_details")
            or profile.intent("package_details")
        )

        # 1. Authoritative profile intent answer: If tenant configured an explicit answer, use it!
        intent_ans = (getattr(intent, "answer", None) or "").strip() if (intent and intent.enabled) else ""
        broad = (
            any(phrase in query.lower() for phrase in BROAD_SERVICE_PHRASES)
            or query.lower() in {
                "service", "services", "offerings", "package", "packages", "products", "product",
                "ongoing projects", "ongoing project", "explore properties", "projects", "properties",
            }
        )
        matched = match_by_rules(query, [intent]) if intent and intent.enabled else None

        if intent_ans and (broad or matched):
            return intent_ans

        # 2. Offerings lookup, strictly filtered by tenant vertical relevance
        offerings = list_products(active_only=True, limit=100, tenant_id=tid)
        try:
            from backend.services.auto_bifurcator import _is_offering_relevant_to_vertical
        except Exception:
            _is_offering_relevant_to_vertical = None

        if _is_offering_relevant_to_vertical:
            offerings = [
                o for o in offerings
                if _is_offering_relevant_to_vertical(o.get("name") or "", o.get("category") or "", vertical)
            ]

        selected = _matching_offerings(query, offerings)
        if not matched and not selected and not broad:
            return None
        if not profile.feature_on("offerings") or (intent is not None and not intent.enabled):
            return f"{item_noun.capitalize()} information isn't available right now. Please contact our team for help."
        if not selected and (matched or broad):
            selected = offerings

        # 3. Fallback to intent answer if no matching vertical offerings exist
        if not selected and intent_ans:
            return intent_ans
    except Exception as exc:
        logger.warning("Could not resolve tenant services for %s: %s", wa_id, exc)
        return None

    if not selected:
        return f"We don't have any {item_noun} listed right now. Please contact our team for details."

    lines = [f"Here are the {item_noun} we offer:"]
    for item in selected[:10]:
        name = (item.get("name") or "").strip()
        if not name:
            continue
        category = (item.get("category") or "").strip()
        price = (item.get("price") or "").strip()
        details = []
        if category:
            details.append(category)
        if price:
            details.append(price if price.startswith("₹") else f"₹{price}")
        if details:
            lines.append(f"• *{name}* ({' | '.join(details)})")
        else:
            lines.append(f"• *{name}*")
        description = (item.get("short_description") or item.get("description") or "").strip()
        if description:
            lines.append(f"  {_fit_description(description)}")
    return "\n".join(lines) if len(lines) > 1 else f"We don't have any {item_noun} listed right now. Please contact our team for details."


def _matching_offerings(query: str, offerings: list[dict]) -> list[dict]:
    normalized = re.sub(r"[^a-z0-9]+", " ", query.lower()).strip()
    matches = []
    for item in offerings:
        name = re.sub(r"[^a-z0-9]+", " ", str(item.get("name") or "").lower()).strip()
        if name and re.search(rf"(?<!\w){re.escape(name)}(?!\w)", normalized):
            matches.append(item)
    return matches
