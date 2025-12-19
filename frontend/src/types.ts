export type SearchResult = {
	id: string;
	distance: number;
	text: string;
	meta: {
		source_pdf?: string;
		source_text?: string;
		chunk_index?: number;
		chunk_count?: number;
	};
};

export type SearchResponse = {
	q: string;
	k: number;
	results: SearchResult[];
};

