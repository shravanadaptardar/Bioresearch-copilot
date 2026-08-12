"""
agents/datasets.py — sync version
Searches NCBI GEO for relevant datasets.
"""
import requests

EUTILS  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
HEADERS = {"User-Agent": "BioResearchCopilot/1.0"}

# Domain-to-GEO-filter mapping. Keeps the search relevant without
# hardcoding "single cell" for every query type.
_DOMAIN_GEO_FILTER = {
    "marker_annotation":  "AND single cell[All Fields]",
    "cell_type_study":    "AND single cell[All Fields]",
    "general_scrna":      "AND single cell[All Fields]",
    "dataset_discovery":  "",   # user asked for datasets broadly — don't filter
    "pathway_analysis":   "",   # could be bulk or single-cell
    "methods_concept":    "",   # irrelevant for method questions (shouldn't reach here)
}


def _search_geo(term: str, domain: str = "general_scrna", retmax: int = 12) -> list:
    geo_filter = _DOMAIN_GEO_FILTER.get(domain, "AND single cell[All Fields]")
    full_term  = f"{term} {geo_filter}".strip()
    try:
        r = requests.get(f"{EUTILS}/esearch.fcgi",
            params={"db":"gds","term": full_term,
                    "retmax":retmax,"retmode":"json","sort":"relevance"},
            headers=HEADERS, timeout=15)
        return r.json().get("esearchresult", {}).get("idlist", [])
    except Exception as e:
        print(f"[Datasets] Search error: {e}")
        return []


def _fetch_geo_summaries(uids: list) -> list:
    if not uids:
        return []
    try:
        r = requests.get(f"{EUTILS}/esummary.fcgi",
            params={"db":"gds","id":",".join(uids),"retmode":"json"},
            headers=HEADERS, timeout=20)
        data   = r.json()
        result = data.get("result", {})
        uids_  = result.get("uids", [])
    except Exception as e:
        print(f"[Datasets] Summary error: {e}")
        return []

    datasets = []
    for uid in uids_:
        item = result.get(uid, {})
        acc  = item.get("accession", "")
        if not acc.startswith("GSE"):
            continue
        datasets.append({
            "accession": acc,
            "title":     (item.get("title") or "")[:120],
            "samples":   item.get("n_samples", "?"),
            "taxon":     item.get("taxon", ""),
            "gdstype":   item.get("gdstype", ""),
        })
    return datasets


def fetch_datasets(plan: dict) -> dict:
    terms   = plan.get("geo_search_terms", []) or plan.get("search_terms", [])
    disease = plan.get("disease_context", "")
    domain  = plan.get("domain", "general_scrna")

    if not terms:
        return {"datasets": [], "note": ""}

    search_str = f"{disease} {terms[0]}".strip() if disease else terms[0]
    uids       = _search_geo(search_str, domain=domain, retmax=12)
    datasets   = _fetch_geo_summaries(uids)

    seen, unique = set(), []
    for d in datasets:
        if d["accession"] not in seen:
            seen.add(d["accession"])
            unique.append(d)
    unique = unique[:8]

    if unique:
        note = (f"Showing datasets for '{disease or search_str}'. "
                "Click any accession to open in GEO. "
                "Download with: pip install GEOparse")
    else:
        note = "No GEO datasets found. Try a broader query."

    return {"datasets": unique, "note": note}
