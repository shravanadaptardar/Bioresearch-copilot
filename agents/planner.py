"""
agents/planner.py — sync version
"""
import json, os
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))

SYSTEM_PROMPT = """You are a computational biology research planner.

Given a user query, output a JSON object with these exact keys:
{
  "domain": one of ["marker_annotation", "pathway_analysis", "dataset_discovery", "cell_type_study", "methods_concept", "general_scrna"],
  "genes": ["list", "of", "gene", "symbols", "mentioned"],
  "disease_context": "e.g. PDAC, breast cancer, or empty string",
  "cell_types": ["any cell types mentioned"],
  "search_terms": ["2-4 optimised PubMed search strings"],
  "geo_search_terms": ["1-2 GEO search strings, or empty list if not applicable"],
  "needs_datasets": true or false,
  "agents_to_run": ["literature", "datasets", "workflow", "code"]
}

IMPORTANT — distinguish two query types:

1. BIOLOGICAL queries (mention specific genes, cell types, or a disease):
   e.g. "I have macrophage markers CD68" or "KRAS in PDAC"
   -> search_terms should combine the gene/disease/cell-type with
      "single cell RNA-seq" for PubMed, e.g. "CD68 macrophage PDAC single cell"
   -> needs_datasets: true
   -> domain: marker_annotation / pathway_analysis / cell_type_study / dataset_discovery

2. METHODS/CONCEPT queries (about algorithms, tools, or techniques, no specific
   gene/disease/cell-type mentioned):
   e.g. "Leiden vs Louvain clustering", "how does Harmony batch correction work",
   "what is UMAP"
   -> domain: methods_concept
   -> search_terms should target the SPECIFIC algorithm/method name plus
      "single cell" or "scRNA-seq", e.g. "Leiden algorithm clustering single cell"
      and "Louvain community detection single cell RNA-seq"
      NEVER use a vague generic term like "single cell RNA sequencing clustering"
      alone — always anchor to the named method.
   -> needs_datasets: false (datasets are irrelevant for a pure method question)
   -> geo_search_terms: []

Return ONLY valid JSON. No explanation, no markdown fences."""


def plan_query(query: str) -> dict:
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": query},
            ],
            temperature=0.1,
            max_tokens=600,
        )
        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)
    except Exception as e:
        print(f"[Planner] Error: {e}")
        return {
            "domain": "general_scrna",
            "genes": [],
            "disease_context": "",
            "cell_types": [],
            "search_terms": [query],
            "geo_search_terms": [query],
            "needs_datasets": True,
            "agents_to_run": ["literature", "datasets", "workflow", "code"],
            "_error": str(e),
        }
