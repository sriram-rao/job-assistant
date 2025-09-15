from __future__ import annotations

from typing import Dict, List

from defaults import PERSON


def values_from_defaults(fields: List[Dict]) -> Dict[str, object]:
    values: Dict[str, object] = {}

    first = PERSON.get("first_name", "")
    last = PERSON.get("last_name", "")
    full = PERSON.get("full_name", f"{first} {last}" if first or last else "")
    contact = PERSON.get("contact", {}) if isinstance(PERSON.get("contact"), dict) else {}
    email = contact.get("email", "") if isinstance(contact, dict) else ""
    phone = contact.get("phone", "") if isinstance(contact, dict) else ""
    linkedin = contact.get("linkedin", "") if isinstance(contact, dict) else ""
    github = contact.get("github", "") if isinstance(contact, dict) else ""
    website = contact.get("website", "") if isinstance(contact, dict) else ""
    location = PERSON.get("location", "")

    def norm(s: str) -> str:
        return "".join(ch.lower() if ch.isalnum() else "" for ch in s or "")

    for f in fields:
        name = f.get("name") or ""
        if not name:
            continue
        n = norm(name)

        if ("firstname" in n) or ("givenname" in n):
            if first:
                values[name] = first
            continue
        if ("lastname" in n) or ("familyname" in n) or ("surname" in n):
            if last:
                values[name] = last
            continue
        if (n == "name") or ("fullname" in n) or ("yourname" in n):
            if full:
                values[name] = full
            continue
        if "email" in n:
            if email:
                values[name] = email
            continue
        if ("phone" in n) or ("tel" in n) or ("mobile" in n):
            if phone:
                values[name] = phone
            continue
        if "linkedin" in n:
            if linkedin:
                values[name] = f"https://www.linkedin.com/in/{linkedin}" if not linkedin.startswith("http") else linkedin
            continue
        if "github" in n:
            if github:
                values[name] = f"https://github.com/{github}" if not github.startswith("http") else github
            continue
        if ("website" in n) or (n.endswith("url")) or ("portfolio" in n):
            if website:
                values[name] = f"https://{website}" if website and not website.startswith("http") else website
            continue
        if ("location" in n) or ("city" in n and "state" not in n):
            if location:
                values[name] = location
            continue

    return values

