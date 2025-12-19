from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Paths:
	root: Path

	@property
	def data(self) -> Path:
		return self.root / "data"

	@property
	def pdfs(self) -> Path:
		return self.data / "pdfs"

	@property
	def ocr_pdfs(self) -> Path:
		return self.data / "ocr_pdfs"

	@property
	def text(self) -> Path:
		return self.data / "text"

	@property
	def manifests(self) -> Path:
		return self.data / "manifests"

	@property
	def chroma(self) -> Path:
		return self.data / "chroma"

	def ensure_dirs(self) -> None:
		for d in [self.data, self.pdfs, self.ocr_pdfs, self.text, self.manifests, self.chroma]:
			d.mkdir(parents=True, exist_ok=True)

