from pathlib import Path


def replace(file: str, data: dict) -> str:
    with open(Path('resume') / file, encoding='utf-8') as f:
        return f.read().replace(**data)
