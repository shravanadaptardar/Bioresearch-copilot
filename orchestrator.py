"""
orchestrator.py
Runs all agents sequentially — avoids asyncio conflicts inside Streamlit.
Caches full results per-query to avoid burning API tokens on repeat runs.
"""
import os
from dotenv import load_dotenv

# Load .env from this file's own directory, regardless of the
# working directory Streamlit was launched from.
_ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(dotenv_path=_ENV_PATH, override=True)

from agents.planner    import plan_query
from agents.literature import fetch_literature
from agents.datasets   import fetch_datasets
from agents.workflow   import generate_workflow
from agents.code_gen   import generate_code
from cache              import get_cached, set_cached


def run_pipeline(query: str, use_cache: bool = True) -> dict:
    """
    Main entry point. Fully synchronous — safe inside Streamlit.
    Checks cache first; only calls the agents on a cache miss.

    Agent order is deliberately: planner -> code_gen -> workflow -> literature -> datasets.
    code_gen is the single most expensive LLM call (1800 max_tokens), so it
    runs right after planning while quota is most likely to still be available.
    If planner itself hits a rate limit, we stop immediately rather than
    burning further tokens on agents that will likely fail too.
    """
    if use_cache:
        cached = get_cached(query)
        if cached is not None:
            cached["_from_cache"] = True
            return cached

    # Step 1: Understand the query
    plan = plan_query(query)

    # Only short-circuit if the planner itself threw an exception.
    # The _error key is set by plan_query()'s except block.
    # Do NOT short-circuit based on content (domain/genes/disease) — a
    # legitimate query like "best practices for scRNA-seq preprocessing"
    # has no genes or disease context but is a perfectly valid plan.
    if "_error" in plan:
        err = plan["_error"]
        return {
            "plan": plan,
            "literature": [], "datasets": [], "dataset_note": "",
            "workflow": [], "tools": [],
            "marker_interpretation": "", "experimental_notes": "",
            "code_template": f"# Skipped — planner failed: {err}",
            "_from_cache": False,
        }

    # Step 2: Literature + datasets (no LLM cost, run while fast APIs are available)
    literature = fetch_literature(plan)

    needs_datasets = plan.get("needs_datasets", True)  # default True for back-compat
    if needs_datasets:
        datasets = fetch_datasets(plan)
    else:
        datasets = {"datasets": [], "note": "Not applicable — this looks like a methods/concept question rather than a dataset search."}

    # Step 3: Workflow agent — runs before code_gen so code can mirror its steps
    workflow_result = generate_workflow(plan, literature)

    # Step 4: Code generation — receives plan AND workflow so generated code
    # is consistent with the recommended tools and steps above.
    # This is the most expensive LLM call (1800 max_tokens).
    code_result = generate_code(plan, workflow_result)

    result = {
        "plan":                  plan,
        "literature":            literature.get("papers", []),
        "datasets":              datasets.get("datasets", []),
        "dataset_note":          datasets.get("note", ""),
        "workflow":              workflow_result.get("steps", []),
        "tools":                 workflow_result.get("tools", []),
        "marker_interpretation": workflow_result.get("marker_interpretation", ""),
        "experimental_notes":    workflow_result.get("experimental_notes", ""),
        "code_template":         code_result.get("code", ""),
        "_from_cache":           False,
    }

    # Only cache genuinely successful results. A failed agent call returns
    # an error string starting with "#" (see code_gen.py / others) — caching
    # that would freeze the failure in place for 24h even after the
    # underlying problem (bad key, rate limit, network) is fixed.
    code_failed = result["code_template"].strip().startswith("# Code generation failed")

    if use_cache and not code_failed:
        set_cached(query, result)

    return result
