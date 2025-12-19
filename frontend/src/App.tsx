import React, { useMemo, useState } from "react";

import type { SearchResponse, SearchResult } from "./types";

function clampK(k: number): number {
	if (!Number.isFinite(k)) return 8;
	return Math.max(1, Math.min(25, Math.floor(k)));
}

function formatDistance(distance: number): string {
	if (!Number.isFinite(distance)) return "";
	return distance.toFixed(4);
}

function getSourceLabel(r: SearchResult): string {
	const s = r.meta?.source_pdf || r.meta?.source_text || "unknown";
	const parts = s.split("/");
	return parts[parts.length - 1] || s;
}

export function App(): React.ReactElement {
	const [q, setQ] = useState<string>("");
	const [k, setK] = useState<number>(8);
	const [loading, setLoading] = useState<boolean>(false);
	const [error, setError] = useState<string>("");
	const [results, setResults] = useState<SearchResult[]>([]);

	const canSearch = useMemo(() => q.trim().length > 0 && !loading, [q, loading]);

	async function onSearch(): Promise<void> {
		const qq = q.trim();
		if (!qq) return;

		setLoading(true);
		setError("");
		setResults([]);

		try {
			const kk = clampK(k);
			const url = `/api/search?q=${encodeURIComponent(qq)}&k=${encodeURIComponent(String(kk))}`;
			const r = await fetch(url, { method: "GET" });
			if (!r.ok) {
				const txt = await r.text().catch(() => "");
				throw new Error(`API error (${r.status}): ${txt || r.statusText}`);
			}
			const data = (await r.json()) as SearchResponse;
			setResults(data.results || []);
		} catch (e) {
			setError(e instanceof Error ? e.message : String(e));
		} finally {
			setLoading(false);
		}
	}

	return (
		<div className="container">
			<div className="header">
				<div>
					<div className="title">Epstein DOJ PDFs</div>
					<div className="subtitle">Semantic search (SWA frontend + /api/search)</div>
				</div>
				<div className="subtitle">
					<a href="https://github.com/lalonde302/epstein" target="_blank" rel="noreferrer">
						GitHub
					</a>
				</div>
			</div>

			<div className="panel">
				<div className="row">
					<input
						type="text"
						value={q}
						onChange={(e) => setQ(e.target.value)}
						onKeyDown={(e) => {
							if (e.key === "Enter") void onSearch();
						}}
						placeholder='Try: "victim statements", "flight logs", "Palm Beach"'
					/>
					<input
						type="text"
						value={String(k)}
						onChange={(e) => setK(Number(e.target.value))}
						placeholder="k"
						aria-label="Top K"
					/>
					<button onClick={() => void onSearch()} disabled={!canSearch}>
						{loading ? "Searching…" : "Search"}
					</button>
				</div>

				<div className="hint">
					This currently calls <span className="mono">/api/search</span>. Next step is wiring the API to the
					vector index (Azure AI Search or another hosted vector store for SWA).
				</div>

				{error ? <div className="error">{error}</div> : null}

				<div className="results">
					{results.map((r) => (
						<div key={r.id} className="result">
							<div className="resultTop">
								<div className="mono">{getSourceLabel(r)}</div>
								<div className="badge">distance: {formatDistance(r.distance)}</div>
							</div>
							<div className="excerpt">{r.text}</div>
						</div>
					))}
				</div>
			</div>
		</div>
	);
}


