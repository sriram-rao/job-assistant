import subprocess
from pathlib import Path

from util import date, strings


def compile_to_pdf(file: str, working_dir: Path, target_filename: str = "", target_dir: Path = Path("target")) -> Path:
    print(f"Compiling {file}...")
    subprocess.run(["xelatex", file], cwd=working_dir, timeout=60, capture_output=True, text=True)

    target_dir = target_dir / date.to_directory_suffix(date.TODAY)
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = strings.get_default_if_blank(target_filename) + f"_{date.get_file_suffix()}.pdf"
    file_path = (target_dir / filename).resolve()

    (working_dir / f"{file}.pdf").rename(file_path)
    print(f"Compiled {file} to {file_path}")
    return file_path
