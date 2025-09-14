from __future__ import annotations

import json
import re
import ssl
import sys
import urllib.error
import urllib.request
from typing import Dict, List, Set


USER = "sriram-rao"
BASE = f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner&sort=updated"
HDRS = {
    "Accept": "application/vnd.github+json, application/vnd.github.mercy-preview+json",
    "User-Agent": "repo-skill-scan",
}
CTX = ssl.create_default_context()


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers=HDRS)
    with urllib.request.urlopen(req, context=CTX, timeout=30) as r:
        return r.read()


def main() -> int:
    repos = json.loads(get(BASE))
    areas: Set[str] = set()
    packages: Dict[str, Set[str]] = {
        "javascript": set(),
        "python": set(),
        "rust": set(),
        "go": set(),
        "ruby": set(),
    }
    manifests = [
        "package.json",
        "requirements.txt",
        "Pipfile",
        "Cargo.toml",
        "go.mod",
        "Gemfile",
    ]

    for repo in repos:
        name: str = repo.get("name") or ""
        for t in repo.get("topics") or []:
            if t:
                areas.add(t)
        lo = name.lower()
        if "svelte" in lo:
            areas.add("svelte/sveltekit")
        if "nvim" in lo or "neovim" in lo:
            areas.add("neovim")
        if "rust" in lo or lo.endswith("rs") or lo.startswith("rs-"):
            areas.add("rust")
        if "ios" in lo or "swift" in lo:
            areas.add("ios/swift")
        if "flask" in lo:
            areas.add("flask")
        if "spring" in lo:
            areas.add("spring")
        if any(x in lo for x in ("db", "sql", "postgres")):
            areas.add("databases/sql")

        owner = repo["owner"]["login"]
        branch = repo.get("default_branch") or "main"
        for path in manifests:
            raw_url = f"https://raw.githubusercontent.com/{owner}/{name}/{branch}/{path}"
            try:
                raw = get(raw_url).decode("utf-8", "ignore")
            except urllib.error.HTTPError:
                continue
            except Exception:
                continue
            p = path.lower()
            if p == "package.json":
                try:
                    data = json.loads(raw)
                    for sec in ("dependencies", "devDependencies", "peerDependencies"):
                        for k in (data.get(sec) or {}):
                            packages["javascript"].add(str(k))
                    areas.add("frontend")
                except Exception:
                    pass
            elif p in ("requirements.txt", "pipfile"):
                for line in raw.splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    pkg = re.split(r"[<>=!~\[; ]", line)[0]
                    if pkg:
                        packages["python"].add(pkg)
            elif p == "cargo.toml":
                indeps = False
                for line in raw.splitlines():
                    L = line.strip()
                    if L.startswith("["):
                        indeps = L.lower().startswith("[dependencies")
                        continue
                    if indeps and L and not L.startswith("#") and "=" in L:
                        dep = L.split("=", 1)[0].strip()
                        if dep:
                            packages["rust"].add(dep)
            elif p == "go.mod":
                for line in raw.splitlines():
                    ls = line.strip()
                    if ls.startswith("require "):
                        parts = ls.split()
                        if len(parts) >= 2:
                            packages["go"].add(parts[1])
            elif p == "gemfile":
                for m in re.finditer(r"gem\s+['\"]([\w\-:]+)['\"]", raw, re.I):
                    packages["ruby"].add(m.group(1))

    out = {
        "areas": sorted(a for a in areas if a),
        "packages": {k: sorted(v) for k, v in packages.items() if v},
    }
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

