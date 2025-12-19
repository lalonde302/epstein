from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm


_DEFAULT_UA = "Mozilla/5.0 (compatible; epstein-pdf-downloader/1.0)"


def _safe_filename(name: str) -> str:
	name = name.strip()
	name = re.sub(r"[\s]+", " ", name)
	name = re.sub(r"[^a-zA-Z0-9\.\-\_\(\) ]+", "_", name)
	name = name.replace(" ", "_")
	return name[:180] if len(name) > 180 else name


def _url_sha256(url: str) -> str:
	return hashlib.sha256(url.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PdfLink:
	source_page_url: str
	pdf_url: str
	link_text: str

	@property
	def url_hash(self) -> str:
		return _url_sha256(self.pdf_url)[:16]


def find_pdf_links(page_url: str, timeout_s: int = 30) -> list[PdfLink]:
	r = requests.get(
		page_url,
		headers={"User-Agent": _DEFAULT_UA},
		timeout=timeout_s,
	)
	r.raise_for_status()

	soup = BeautifulSoup(r.text, "html.parser")
	links: list[PdfLink] = []

	for a in soup.select("a[href]"):
		href = a.get("href") or ""
		abs_url = urljoin(page_url, href)
		if not abs_url.lower().endswith(".pdf"):
			continue
		links.append(
			PdfLink(
				source_page_url=page_url,
				pdf_url=abs_url,
				link_text=(a.get_text() or "").strip(),
			)
		)

	seen: set[str] = set()
	uniq: list[PdfLink] = []
	for l in links:
		if l.pdf_url in seen:
			continue
		seen.add(l.pdf_url)
		uniq.append(l)
	return uniq


def find_pdf_links_many(page_urls: Iterable[str], timeout_s: int = 30) -> list[PdfLink]:
	all_links: list[PdfLink] = []
	for u in page_urls:
		all_links.extend(find_pdf_links(u, timeout_s=timeout_s))

	seen: set[str] = set()
	uniq: list[PdfLink] = []
	for l in all_links:
		if l.pdf_url in seen:
			continue
		seen.add(l.pdf_url)
		uniq.append(l)
	return uniq


def _suggest_name_from_url(pdf_url: str) -> str:
	path = urlparse(pdf_url).path
	base = Path(path).name or "document.pdf"
	if not base.lower().endswith(".pdf"):
		base = base + ".pdf"
	return _safe_filename(base)


def download_pdfs(
	links: list[PdfLink],
	out_dir: Path,
	manifest_path: Path,
	timeout_s: int = 60,
	sleep_s: float = 0.2,
	overwrite: bool = False,
) -> dict:
	out_dir.mkdir(parents=True, exist_ok=True)
	manifest_path.parent.mkdir(parents=True, exist_ok=True)

	entries: list[dict] = []
	ok = 0
	skipped = 0
	failed = 0

	for link in tqdm(links, desc="Downloading PDFs", unit="pdf"):
		name = _suggest_name_from_url(link.pdf_url)
		final_name = f"{link.url_hash}__{name}"
		dest = out_dir / final_name

		if dest.exists() and not overwrite:
			skipped += 1
			entries.append(
				{
					"status": "skipped_exists",
					"pdf_url": link.pdf_url,
					"source_page_url": link.source_page_url,
					"dest_path": str(dest),
					"link_text": link.link_text,
					"timestamp": time.time(),
				}
			)
			continue

		try:
			r = requests.get(
				link.pdf_url,
				headers={"User-Agent": _DEFAULT_UA},
				timeout=timeout_s,
				stream=True,
			)
			r.raise_for_status()

			tmp = dest.with_suffix(dest.suffix + ".part")
			with open(tmp, "wb") as f:
				for chunk in r.iter_content(chunk_size=1024 * 1024):
					if not chunk:
						continue
					f.write(chunk)
			tmp.replace(dest)

			ok += 1
			entries.append(
				{
					"status": "ok",
					"pdf_url": link.pdf_url,
					"source_page_url": link.source_page_url,
					"dest_path": str(dest),
					"link_text": link.link_text,
					"timestamp": time.time(),
				}
			)
		except Exception as e:
			failed += 1
			entries.append(
				{
					"status": "error",
					"pdf_url": link.pdf_url,
					"source_page_url": link.source_page_url,
					"dest_path": str(dest),
					"link_text": link.link_text,
					"error": repr(e),
					"timestamp": time.time(),
				}
			)

		if sleep_s > 0:
			time.sleep(sleep_s)

	manifest = {
		"created_at": time.time(),
		"count_total": len(links),
		"count_ok": ok,
		"count_skipped": skipped,
		"count_failed": failed,
		"entries": entries,
	}

	with open(manifest_path, "w", encoding="utf-8") as f:
		json.dump(manifest, f, indent=2, ensure_ascii=False)

	return manifest

