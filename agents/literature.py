"""
agents/literature.py — sync version
Fetches PubMed abstracts and summarises with Groq.
"""
import requests, os
import xml.etree.ElementTree as ET
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))

EUTILS  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
HEADERS = {"User-Agent": "BioResearchCopilot/1.0"}


def _search_pubmed(term: str, retmax: int = 4) -> list:
    try:
        r = requests.get(f"{EUTILS}/esearch.fcgi",
            params={"db":"pubmed","term": term + " AND hasabstract[text] NOT (proceedings[Title] OR symposium[Title])",
                    "retmax":retmax,
                    "retmode":"json","sort":"relevance"},
            headers=HEADERS, timeout=15)
        return r.json().get("esearchresult", {}).get("idlist", [])
    except Exception as e:
        print(f"[Literature] Search error: {e}")
        return []


import re as _re

# Titles that are conference proceedings/symposia listings rather than
# actual research papers — these have no real single-paper abstract.
_PROCEEDINGS_RE = _re.compile(
    r"\b(symposium|proceedings|annual meeting|conference abstracts?|"
    r"\d+(st|nd|rd|th)\s+(international|annual))\b",
    _re.IGNORECASE,
)


def _is_real_paper(paper: dict) -> bool:
    """Filter out conference proceedings/symposia and abstract-less entries."""
    title = paper.get("title", "")
    if _PROCEEDINGS_RE.search(title):
        return False
    if not paper.get("abstract", "").strip():
        return False
    return True


def _fetch_abstracts(pmids: list) -> list:
    if not pmids:
        return []
    try:
        r = requests.get(f"{EUTILS}/efetch.fcgi",
            params={"db":"pubmed","id":",".join(pmids),"retmode":"xml"},
            headers=HEADERS, timeout=20)
        root = ET.fromstring(r.content)
    except Exception as e:
        print(f"[Literature] Fetch error: {e}")
        return []

    papers = []
    for article in root.findall(".//PubmedArticle"):
        pmid_el  = article.find(".//PMID")
        title_el = article.find(".//ArticleTitle")
        abs_el   = article.find(".//AbstractText")
        year_el  = article.find(".//PubDate/Year")
        jour_el  = article.find(".//Journal/Title")
        auth_els = article.findall(".//Author")

        authors = []
        for a in auth_els[:3]:
            ln = a.find("LastName")
            if ln is not None:
                authors.append(ln.text)
        author_str = ", ".join(authors) + (" et al." if len(auth_els) > 3 else "")

        papers.append({
            "pmid":     pmid_el.text  if pmid_el  is not None else "",
            "title":    (title_el.text or "No title") if title_el is not None else "No title",
            "abstract": (abs_el.text  or "")          if abs_el  is not None else "",
            "year":     (year_el.text or "")          if year_el is not None else "",
            "journal":  (jour_el.text or "")          if jour_el is not None else "",
            "authors":  author_str,
        })
    return papers


import re

# Matches leading meta-commentary like "Here is a summary..." or
# "Here's a 2-sentence summary of the abstract for a computational biologist:"
# that smaller/instruction-loose models sometimes prepend despite instructions.
_PREAMBLE_RE = re.compile(
    r"^(here'?s?\s+(is\s+)?(a\s+)?(\d+[\s-]?(sentence|line)\s+)?summary[^:]*:\s*)",
    re.IGNORECASE,
)


def _strip_preamble(text: str) -> str:
    """Remove leaked 'Here is a summary...' style preamble from model output."""
    text = text.strip()
    text = _PREAMBLE_RE.sub("", text).strip()
    # Also handle the case where it's on its own line followed by a blank line
    lines = text.split("\n")
    if lines and _PREAMBLE_RE.match(lines[0] + ":"):
        lines = lines[1:]
    text = "\n".join(lines).strip()
    return text


def _summarise_paper(paper: dict) -> dict:
    abstract = paper.get("abstract", "")
    if not abstract:
        paper["summary"] = "No abstract available."
        return paper
    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content":
                    "You summarise scientific abstracts for computational biologists. "
                    "Output ONLY the summary itself in 1-2 sentences. "
                    "Do NOT include any preamble, introduction, or phrases like "
                    "'Here is a summary' or 'Here's a 2-sentence summary' — "
                    "start directly with the scientific content."},
                {"role": "user", "content":
                    f"Summarise this abstract in 1-2 sentences, focusing on the key finding:\n\n{abstract[:800]}"},
            ],
            temperature=0.2, max_tokens=120,
        )
        raw = resp.choices[0].message.content.strip()
        paper["summary"] = _strip_preamble(raw)
    except Exception:
        paper["summary"] = abstract[:200] + "…"
    return paper


def fetch_literature(plan: dict) -> dict:
    search_terms = plan.get("search_terms", [])
    if not search_terms:
        return {"papers": []}

    all_pmids, seen = [], set()
    for term in search_terms[:2]:
        for pmid in _search_pubmed(term, retmax=6):  # fetch extra to survive filtering
            if pmid not in seen:
                seen.add(pmid)
                all_pmids.append(pmid)
    all_pmids = all_pmids[:10]

    if not all_pmids:
        return {"papers": []}

    raw_papers = _fetch_abstracts(all_pmids)
    quality_papers = [p for p in raw_papers if _is_real_paper(p)][:6]

    papers = [_summarise_paper(p) for p in quality_papers]
    return {"papers": papers}
