"""
agents/workflow.py — sync version
"""
import json, os
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))

SYSTEM_PROMPT = """You are a senior computational biologist specialising in single-cell RNA-seq.

Given a research plan JSON, return a single JSON object:
{
  "steps": [
    {"step": "what to do", "tool": "primary tool"},
    ...
  ],
  "tools": ["Tool1", "Tool2", ...],
  "marker_interpretation": "If genes listed: what cell type/state they indicate. Empty string if no genes.",
  "experimental_considerations": "2-3 practical caveats as plain text (QC, batch correction, validation)."
}

Rules:
- 5-8 workflow steps tailored to the domain and disease context.
- 6-10 specific tools/packages.
- Be concrete, not generic.
- Return ONLY valid JSON. No markdown fences, no explanation."""


def generate_workflow(plan: dict, literature: dict) -> dict:
    paper_titles = [p.get("title","") for p in literature.get("papers",[])[:3]]
    user_content = json.dumps({"plan": plan, "top_papers": paper_titles}, indent=2)
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role":"system","content":SYSTEM_PROMPT},
                {"role":"user",  "content":user_content},
            ],
            temperature=0.3, max_tokens=1200,
        )
        raw  = response.choices[0].message.content.strip()
        raw  = raw.replace("```json","").replace("```","").strip()
        data = json.loads(raw)
        return {
            "steps":                 data.get("steps", []),
            "tools":                 data.get("tools", []),
            "marker_interpretation": data.get("marker_interpretation", ""),
            "experimental_notes":    data.get("experimental_considerations", ""),
        }
    except Exception as e:
        print(f"[Workflow] Error: {e}")
        return {"steps":[],"tools":[],"marker_interpretation":"","experimental_notes":""}
