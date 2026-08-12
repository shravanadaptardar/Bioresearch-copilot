"""
agents/code_gen.py — sync version
"""
import json, os
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))

SYSTEM_PROMPT = """You are an expert computational biologist writing clean Python/Scanpy code.

Given a research plan AND the recommended workflow steps and tools, generate a Python
code template that:
1. Is ready to run with minor path edits
2. Uses scanpy (sc), anndata (ad), pandas (pd), numpy (np)
3. Has clear comments explaining each step
4. Implements the EXACT workflow steps provided — do not invent different steps
5. Uses the EXACT tools listed in the workflow where they have Python APIs
6. For batch correction uses: import harmonypy as hm; ho = hm.run_harmony(adata.obsm['X_pca'], adata.obs, 'batch'); adata.obsm['X_pca_harmony'] = ho.Z_corr.T
7. If genes are provided, includes: sc.pl.dotplot(adata, var_names=genes, groupby='leiden')
8. Is 60-100 lines — every line does something real

Return ONLY the Python code. No markdown fences. No explanation outside comments."""


def generate_code(plan: dict, workflow_result: dict = None) -> dict:
    """
    Generate a Python/Scanpy code template.
    workflow_result is now passed in so the generated code mirrors
    the recommended workflow steps and tools exactly.
    """
    # Build user content combining plan + workflow so code is consistent
    user_content = {
        "research_plan": plan,
        "workflow_steps": (workflow_result or {}).get("steps", []),
        "recommended_tools": (workflow_result or {}).get("tools", []),
    }
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role":"system","content":SYSTEM_PROMPT},
                {"role":"user",  "content":f"Generate code for this plan and workflow:\n{json.dumps(user_content, indent=2)}"},
            ],
            temperature=0.2, max_tokens=1800,
        )
        code = response.choices[0].message.content.strip()
        if code.startswith("```"):
            lines = code.split("\n")
            code  = "\n".join(lines[1:-1]) if lines[-1].strip()=="```" else "\n".join(lines[1:])
        return {"code": code}
    except Exception as e:
        print(f"[CodeGen] Error: {e}")
        return {"code": f"# Code generation failed: {e}"}
