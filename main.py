from pathlib import Path

from tex import compile_to_pdf

compile_to_pdf("main", Path("resume"), "resume")
compile_to_pdf("simplecover", Path("letter"), "letter")
