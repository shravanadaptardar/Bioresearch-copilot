# BioResearch Copilot

An AI-powered research assistant for computational biologists — describe a gene panel, disease, or method question in plain English and get back a literature summary, relevant public datasets, a suggested analysis workflow, and a runnable Scanpy code template.

**Live demo:** [add your Streamlit Community Cloud link here]

## How it works

A 5-stage synchronous agent pipeline (see `orchestrator.py`) turns a natural-language query into a structured research brief:

```
Planner  →  Literature  →  Datasets  →  Workflow  →  Code Generation
(Groq)      (PubMed)       (NCBI GEO)   (Groq)        (Groq)
```

1. **Planner** (`agents/planner.py`) — classifies the query (marker annotation, pathway analysis, dataset discovery, methods/concept, etc.), extracts genes/disease/cell-type context, and produces optimised search terms.
2. **Literature** (`agents/literature.py`) — searches PubMed via NCBI E-utilities, filters out conference proceedings/abstract-less entries, and summarises each abstract with an LLM call.
3. **Datasets** (`agents/datasets.py`) — searches NCBI GEO for relevant public datasets, domain-aware (e.g. only filters to "single cell" when the query calls for it).
4. **Workflow** (`agents/workflow.py`) — proposes a concrete 5–8 step analysis workflow with specific tools, plus marker interpretation and experimental caveats.
5. **Code Generation** (`agents/code_gen.py`) — writes a Python/Scanpy code template that mirrors the exact workflow steps and tools recommended above.

Results are cached to disk (`cache.py`, 24h TTL) so repeat queries don't burn API tokens, and a full report can be exported as a formatted PDF (`report_pdf.py`, via ReportLab).

## Setup (one time)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your Groq API key
cp .env.example .env
# then edit .env and paste in your key
```

Get a free Groq API key at: https://console.groq.com

## Run

```bash
streamlit run app.py
```

Then open http://localhost:8501 in your browser.

## Project Structure

```
bioresearch_copilot/
├── app.py              # Streamlit UI
├── orchestrator.py     # Wires all agents together
├── requirements.txt
└── agents/
    ├── planner.py      # Interprets user query → structured plan
    ├── literature.py   # PubMed search + LLM summarisation
    ├── datasets.py     # GEO/NCBI dataset search
    ├── workflow.py     # Workflow + tools + marker interpretation
    └── code_gen.py     # Scanpy code template generation
```

## Example queries

- "I have macrophage markers: CD68, CD163, MRC1"
- "I want to study KRAS signaling in PDAC"
- "How do I annotate T cell subtypes in scRNA-seq?"
- "Find datasets for pancreatic cancer tumor microenvironment"

## APIs Used (all free)

| API | Purpose | Key needed? |
|-----|---------|-------------|
| Groq | LLM reasoning | Yes (free tier) |
| PubMed E-utilities | Literature search | No |
| NCBI GEO E-utilities | Dataset search | No |
