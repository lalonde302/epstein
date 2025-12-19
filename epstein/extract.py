from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

import fitz  # pymupdf


@dataclass(frozen=True)
class ExtractResult:
	pdf_path: Path
	text_path: Path
	char_count: int
	used_ocr: bool


def _extract_text_pymupdf(pdf_path: Path) -> str:
	doc = fitz.open(pdf_path)
	try:
		parts: list[str] = []
		for page in doc:
			txt = page.get_text("text") or ""
			parts.append(txt)
		return "\n".join(parts)
	finally:
		doc.close()


def _has_ocrmypdf() -> bool:
	try:
		r = subprocess.run(["ocrmypdf", "--version"], check=False, capture_output=True, text=True)
		return r.returncode == 0
	except Exception:
		return False


def ocr_to_searchable_pdf(pdf_in: Path, pdf_out: Path) -> bool:
	"""
	Run `ocrmypdf` if available. Returns True if OCR ran successfully.
	"""
	if not _has_ocrmypdf():
		return False

	pdf_out.parent.mkdir(parents=True, exist_ok=True)

	r = subprocess.run(
		[
			"ocrmypdf",
			"--skip-text",
			"--rotate-pages",
			"--deskew",
			"--clean",
			str(pdf_in),
			str(pdf_out),
		],
		check=False,
		capture_output=True,
		text=True,
	)
	return r.returncode == 0 and pdf_out.exists()


def extract_text_to_file(
	pdf_path: Path,
	out_text_path: Path,
	ocr_pdf_out_path: Path | None = None,
	ocr: bool = False,
	min_chars_before_ocr: int = 200,
) -> ExtractResult:
	"""
	Extract text from a PDF. If `ocr` is True and extracted text is short, attempt OCR (ocrmypdf).
	"""
	out_text_path.parent.mkdir(parents=True, exist_ok=True)

	text = _extract_text_pymupdf(pdf_path)
	used_ocr = False

	if ocr and len(text.strip()) < min_chars_before_ocr and ocr_pdf_out_path is not None:
		if ocr_to_searchable_pdf(pdf_path, ocr_pdf_out_path):
			used_ocr = True
			text = _extract_text_pymupdf(ocr_pdf_out_path)

	with open(out_text_path, "w", encoding="utf-8") as f:
		f.write(text)

	return ExtractResult(
		pdf_path=pdf_path,
		text_path=out_text_path,
		char_count=len(text),
		used_ocr=used_ocr,
	)

