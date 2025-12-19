import { app, HttpRequest, HttpResponseInit, InvocationContext } from "@azure/functions";

function clampK(k: number): number {
	if (!Number.isFinite(k)) return 8;
	return Math.max(1, Math.min(25, Math.floor(k)));
}

export async function search(request: HttpRequest, _context: InvocationContext): Promise<HttpResponseInit> {
	const q = (request.query.get("q") || "").trim();
	const k = clampK(Number(request.query.get("k") || "8"));

	if (!q) {
		return {
			status: 400,
			jsonBody: { error: "Missing required query param: q" },
		};
	}

	// TODO: Replace this stub with a real vector search.
	// For Azure SWA hosting, the durable option is Azure AI Search (vector index) or another hosted vector DB.
	return {
		status: 200,
		jsonBody: {
			q,
			k,
			results: [],
		},
	};
}

app.http("search", {
	methods: ["GET"],
	authLevel: "anonymous",
	route: "search",
	handler: search,
});

