from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from tqdm import tqdm


def _sha1(s: str) -> str:
	return hashlib.sha1(s.encode("utf-8")).hexdigest()


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 200) -> list[str]:
	text = text.replace("\r\n", "\n").replace("\r", "\n")
	text = "\n".join([line.rstrip() for line in text.split("\n")]).strip()
	if not text:
		return []

	chunks: list[str] = []
	i = 0
	n = len(text)
	while i < n:
		j = min(n, i + chunk_size)
		chunks.append(text[i:j])
		if j >= n:
			break
		i = max(0, j - overlap)
	return chunks


@dataclass(frozen=True)
class IndexConfig:
	collection: str = "epstein_pdfs"
	embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"


class PdfIndex:
	def __init__(self, persist_dir: Path, cfg: IndexConfig):
		self._persist_dir = persist_dir
		self._cfg = cfg
		self._client = chromadb.PersistentClient(
			path=str(persist_dir),
			settings=Settings(anonymized_telemetry=False),
		)
		self._collection = self._client.get_or_create_collection(name=cfg.collection)
		self._model = SentenceTransformer(cfg.embedding_model)

	def add_text_file(self, text_path: Path, source_pdf_path: Path) -> int:
		text = text_path.read_text(encoding="utf-8", errors="ignore")
		chunks = chunk_text(text)
		if not chunks:
			return 0

		ids: list[str] = []
		metas: list[dict] = []
		docs: list[str] = []

		for idx, chunk in enumerate(chunks):
			doc_id = _sha1(f"{source_pdf_path}::{text_path}::{idx}::{chunk[:64]}")
			ids.append(doc_id)
			docs.append(chunk)
			metas.append(
				{
					"source_pdf": str(source_pdf_path),
					"source_text": str(text_path),
					"chunk_index": idx,
					"chunk_count": len(chunks),
				}
			)

		embeddings = self._model.encode(docs, normalize_embeddings=True).tolist()
		self._collection.upsert(ids=ids, documents=docs, embeddings=embeddings, metadatas=metas)
		return len(ids)

	def add_all_text_files(self, text_dir: Path, mapping_path: Path | None = None) -> dict:
		"""
		Indexes every `.txt` file in `text_dir`. If `mapping_path` exists, it can map text->pdf.
		Otherwise, assumes the corresponding pdf lives in `data/pdfs/` or `data/ocr_pdfs/` with the same stem.
		"""
		mapping: dict[str, str] = {}
		if mapping_path is not None and mapping_path.exists():
			mapping = json.loads(mapping_path.read_text(encoding="utf-8"))

		added = 0
		files = sorted(text_dir.glob("*.txt"))
		for t in tqdm(files, desc="Indexing text files", unit="file"):
			pdf_str = mapping.get(t.name, "")
			source_pdf = Path(pdf_str) if pdf_str else Path(t.stem)
			added += self.add_text_file(t, source_pdf)

		return {"files": len(files), "chunks_added": added}

	def query(self, q: str, k: int = 8) -> list[dict]:
		q_emb = self._model.encode([q], normalize_embeddings=True).tolist()[0]
		res = self._collection.query(
			query_embeddings=[q_emb],
			n_results=k,
			include=["documents", "metadatas", "distances", "ids"],
		)

		out: list[dict] = []
		for i in range(len(res["ids"][0])):
			out.append(
				{
					"id": res["ids"][0][i],
					"distance": res["distances"][0][i],
					"text": res["documents"][0][i],
					"meta": res["metadatas"][0][i],
				}
			)
		return out

