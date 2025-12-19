from __future__ import annotations

import json
import time
from pathlib import Path

import click

from epstein.downloader import download_pdfs, find_pdf_links_many
from epstein.extract import extract_text_to_file
from epstein.index import IndexConfig, PdfIndex
from epstein.paths import Paths


def _repo_root() -> Path:
	return Path(__file__).resolve().parent.parent


@click.group()
def cli() -> None:
	"""
	Epstein DOJ PDFs: download + OCR + semantic search.
	"""


@cli.command("download")
@click.option("--url", "urls", multiple=True, required=True, help="Justice.gov page URL(s) containing PDF links.")
@click.option("--overwrite", is_flag=True, default=False, help="Re-download even if file exists.")
@click.option("--timeout-s", type=int, default=60)
def cmd_download(urls: tuple[str, ...], overwrite: bool, timeout_s: int) -> None:
	paths = Paths(root=_repo_root())
	paths.ensure_dirs()

	links = find_pdf_links_many(urls, timeout_s=timeout_s)
	ts = int(time.time())
	manifest_path = paths.manifests / f"download_manifest_{ts}.json"

	manifest = download_pdfs(
		links=links,
		out_dir=paths.pdfs,
		manifest_path=manifest_path,
		timeout_s=timeout_s,
		overwrite=overwrite,
	)
	click.echo(json.dumps({"manifest": str(manifest_path), **manifest}, indent=2))


@cli.command("ingest")
@click.option("--ocr", is_flag=True, default=False, help="Attempt OCR via `ocrmypdf` when text is missing.")
@click.option("--min-chars-before-ocr", type=int, default=200)
@click.option("--collection", type=str, default="epstein_pdfs")
@click.option("--embedding-model", type=str, default="sentence-transformers/all-MiniLM-L6-v2")
def cmd_ingest(ocr: bool, min_chars_before_ocr: int, collection: str, embedding_model: str) -> None:
	paths = Paths(root=_repo_root())
	paths.ensure_dirs()

	pdfs = sorted(paths.pdfs.glob("*.pdf"))
	if not pdfs:
		raise click.ClickException(f"No PDFs found in {paths.pdfs}")

	mapping: dict[str, str] = {}
	for pdf in click.progressbar(pdfs, label="Extracting text"):
		txt = paths.text / (pdf.stem + ".txt")
		ocr_pdf = paths.ocr_pdfs / pdf.name
		res = extract_text_to_file(
			pdf_path=pdf,
			out_text_path=txt,
			ocr_pdf_out_path=ocr_pdf,
			ocr=ocr,
			min_chars_before_ocr=min_chars_before_ocr,
		)
		mapping[txt.name] = str((ocr_pdf if res.used_ocr else pdf).resolve())

	mapping_path = paths.data / "text_to_pdf_map.json"
	mapping_path.write_text(json.dumps(mapping, indent=2), encoding="utf-8")

	idx = PdfIndex(
		persist_dir=paths.chroma,
		cfg=IndexConfig(collection=collection, embedding_model=embedding_model),
	)
	stats = idx.add_all_text_files(paths.text, mapping_path=mapping_path)
	click.echo(json.dumps({"mapping": str(mapping_path), **stats}, indent=2))


@cli.command("query")
@click.option("--q", required=True, help="Query string.")
@click.option("--k", type=int, default=8, help="Top K results.")
@click.option("--collection", type=str, default="epstein_pdfs")
@click.option("--embedding-model", type=str, default="sentence-transformers/all-MiniLM-L6-v2")
def cmd_query(q: str, k: int, collection: str, embedding_model: str) -> None:
	paths = Paths(root=_repo_root())
	paths.ensure_dirs()

	idx = PdfIndex(
		persist_dir=paths.chroma,
		cfg=IndexConfig(collection=collection, embedding_model=embedding_model),
	)
	results = idx.query(q=q, k=k)
	click.echo(json.dumps({"q": q, "k": k, "results": results}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
	cli()

