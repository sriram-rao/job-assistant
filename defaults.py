from __future__ import annotations

from typing import Dict, Mapping, Optional, Iterable


# Common defaults used by both letters and resume templates
Common: Dict[str, str] = {
    # Personal info
    "myfirstname": "Sriram",
    "mylastname": "Rao",
    "myname": "Sriram Rao",
    "mywebsite": "sriramrao.com",
    "myemail": "reach@sriramrao.com",
    "mylinkedin": "sriram-rao",
    "myphone": "+1 (949) 560-3250",
    "mylocation": "San Jose, CA",
}

# Defaults specific to cover letters
Letter: Dict[str, str] = {
    # Letter basics
    "greeting": "Hello",
    "recipientfirstname": "Hiring Manager",
    "recipientlastname": "",
    "company": "Microsoft AI",
    "fullcompany": "Microsoft AI",
    "city": "Mountain View, ",
    "state": "CA",
    "country": "",
    # Roles and titles
    "mytitle": "Software Engineer",
    "jobtitle": "",
    "myindustryname": "large-scale systems",
    "product": "",
    # Closers
    "closer": "Yours truly",
    # Contact specific to letter template
    "phone": "+1 949 (560) 3250",
}

# Defaults specific to resume
Resume: Dict[str, str] = {
    "mytagline": r"""\hyphenchar\font=-1
Software engineer with industry and research experience in distributed data systems.
Proven track record
in developing efficient, resilient solutions
and collaborating across teams to drive software innovation.""",
}


def with_overrides(
    overrides: Optional[Mapping[str, str]] = None,
    include: Iterable[str] = ("common", "letter", "resume"),
) -> Dict[str, str]:
    """
    Merge defaults from the selected sets and overlay user-provided overrides.

    include accepts any of: "common", "letter", "resume" (case-insensitive),
    or "Common", "Letter", "Resume". Order matters for resolving collisions;
    later sets in the sequence override earlier ones.

    This function does not mutate the module-level constants; it always returns
    a new dictionary.
    """
    pool: Dict[str, Dict[str, str]] = {
        "common": Common,
        "letter": Letter,
        "resume": Resume,
    }
    merged: Dict[str, str] = {}
    for name in include:
        key = str(name).lower()
        mapping = pool.get(key)
        if mapping is None:
            print(
                f"Unknown defaults set: {name!r}. Use one of ('common', 'letter', 'resume')."
            )
            continue
        # Merge into a new dict to avoid mutating any source dicts
        merged = {**merged, **mapping}
    if overrides:
        merged = {**merged, **dict(overrides)}
    return merged
