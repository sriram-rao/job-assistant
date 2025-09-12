from pathlib import Path
from util import string


def replace(file: str, data: dict) -> str:
    with open(Path('resume') / file, encoding='utf-8') as f:
        content = f.read()
        for key, value in data.items():
            content = content.replace(string.pad(key), value)
        return content
