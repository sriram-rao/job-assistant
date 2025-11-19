from __future__ import annotations

import logging
import subprocess
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import override

from .handler import Handler


def thread_logger() -> logging.Logger:
    name: str = f"{__name__}.{threading.current_thread().name}"
    return logging.getLogger(name)


class PDFGenerator(Handler[Path, Path], ABC):
    """Base class for generating PDFs from documents."""

    @property
    @override
    def log(self) -> logging.Logger:
        return thread_logger()

    @abstractmethod
    @override
    def process(self, input_path: Path) -> Path:
        """Generate PDF from input file."""
        ...


class LatexPDFGenerator(PDFGenerator):
    """Generates PDF from LaTeX files."""

    @override
    def process(self, tex_file: Path) -> Path:
        """Compile LaTeX file to PDF."""
        output_dir = tex_file.parent

        self.log.info(f"Compiling {tex_file} to PDF")
        _ = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-output-directory", str(output_dir.absolute()), tex_file.name],
            cwd=tex_file.parent,
            check=False,
            capture_output=True
        )

        pdf_path = tex_file.with_suffix(".pdf")
        return pdf_path


class DocxPDFGenerator(PDFGenerator):
    """Generates PDF from .docx files."""

    @override
    def process(self, docx_path: Path) -> Path:
        """Convert .docx file to PDF using LibreOffice."""
        output_dir = docx_path.parent

        self.log.info(f"Converting {docx_path} to PDF")
        _ = subprocess.run(
            ["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(output_dir), str(docx_path)],
            check=False,
            capture_output=True
        )

        pdf_path = output_dir / docx_path.with_suffix(".pdf").name
        return pdf_path
