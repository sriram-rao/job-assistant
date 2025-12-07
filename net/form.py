from __future__ import annotations
from typing import cast

from defaults import PERSON


contact = cast(dict[str, str], PERSON.get("contact", {}))

def get_contact_attribute(site: str, value: str) -> str:
    return f"https://www.{site}/{value}" if not value.startswith("http") else value

EASY_FILLS: list[tuple[list[str], str | dict[str, str]]] = [
    (["firstname", "givenname"], PERSON["first_name"]),
    (["lastname", "familyname", "surname"], PERSON["last_name"]),
    (["name", "fullname", "yourname"], f"{PERSON['first_name']} {PERSON['last_name']}"),
    (["email"], contact["email"]),
    (["phone", "tel", "mobile"], contact["phone"]),
    (["location",  "city"], PERSON["location"]),
    (["linkedin"], get_contact_attribute("linkedin.com/in", contact["linkedin"])),
    (["github"], get_contact_attribute("github.com", contact["github"])),
    (["website", "portfolio", "url"], get_contact_attribute(contact["website"], "")),
]

easy_fills_unrolled = [(field, value) for fields, value in EASY_FILLS for field in fields]

def values_from_defaults(all_fields: list[dict[str, object]]) -> dict[str, object]:
    # Normalize incoming fields (list of dicts) to string values
    fields = [{k: str(v) for k, v in f.items()} for f in all_fields]
    values: dict[str, object] = {}

    def norm(s: str) -> str:
        return "".join(ch.lower() if ch.isalnum() else "" for ch in s or "")

    for f in fields:
        field_name = f.get("name")
        if not field_name:
            continue
        normalised_field = norm(field_name)
        for field, value in easy_fills_unrolled:
            if field in normalised_field:
                values[field_name] = value
                break

    return values
