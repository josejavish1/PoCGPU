#!/usr/bin/env python3
"""
Adversarial Mathematical & Physical Audit via gemini-4-argon
============================================================
Submits `calculators/sizing/src/sizing/domain/model.py` and the empirical
extrapolation claims to `gemini-4-argon` for an uncompromised, zero-flattery
peer review on physical realism, statistical validity, and architectural limits.

Target: Console output & `docs/engineering-constitution/ADVERSARIAL_SIZING_AUDIT.md`
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from run_autonomous_mission import (  # type: ignore # noqa: E402
    ARCHITECT_FALLBACK,
    ARCHITECT_MODEL,
    call_model_with_fallback,
    get_genai_client,
)

SIZING_MODEL_PATH = REPO_ROOT / "calculators" / "sizing" / "src" / "sizing" / "domain" / "model.py"
OUTPUT_AUDIT_PATH = REPO_ROOT / "docs" / "engineering-constitution" / "ADVERSARIAL_SIZING_AUDIT.md"


def main() -> None:
    print("[*] Starting Adversarial Audit of Sizing Engine with gemini-4-argon...")

    if not SIZING_MODEL_PATH.exists():
        print(f"[!] Error: {SIZING_MODEL_PATH} does not exist.", file=sys.stderr)
        sys.exit(1)

    code_content = SIZING_MODEL_PATH.read_text(encoding="utf-8")

    prompt = f"""You are a Principal Hardware Systems Architect at NVIDIA / Google DeepMind specializing in large-scale distributed LLM inference and Roofline performance modeling.
Conduct a rigorous, brutally honest, and deeply technical adversarial audit of the mathematical formulas and architectural assumptions in our sizing calculator code (`calculators/sizing/src/sizing/domain/model.py`).

The user is questioning whether our claim of extrapolating performance from a 4x NVIDIA L4 cluster in Zurich (Ada Lovelace, GDDR6, PCIe 4.0) to all other GPUs (A100, H100, B200) and all models (LLaMA-3, DeepSeek, MoE) is physically sound, or if it is a flawed oversimplification / fallacy.

### SOURCE CODE UNDER AUDIT (`calculators/sizing/src/sizing/domain/model.py`):
```python
{code_content}
```

### SPECIFIC CRITICAL QUESTIONS YOU MUST ANSWER:
1. **The Extrapolation Fallacy:** Is it physically valid to extrapolate a single empirical efficiency factor (or formulas calibrated on NVIDIA L4 across PCIe 4.0) to NVIDIA A100 (Ampere/HBM2e), H100 (Hopper/HBM3 with TMA & NVSwitch), or B200? What specific microarchitectural differences break this assumption?
2. **Attention Architecture Divergence:** How do the memory and throughput formulas in `calculate_dynamic_kv_cache_vram_gb` and `calculate_roofline_latencies` fail when confronted with:
   - DeepSeek Multi-Head Latent Attention (MLA)?
   - Sparse Mixture-of-Experts (MoE) where active parameters != total parameters?
3. **Flaws & Vulnerabilities in the Current Python Code:** Identify exact mathematical bugs, missing terms (e.g., KV-cache overhead per sequence vs token, KV-cache quantization scaling factors, prefill chunking interaction, AllReduce latency as a function of TP), or unrealistic constants in `calculate_roofline_latencies`, `calculate_silicon_topology`, or `calculate_activation_vram_gb`.
4. **Concrete Corrective Architecture:** What exact mathematical formulation and catalog parameters MUST be added to make this calculator truly Tier-1 and audit-grade, aligned with MLPerf Inference v6.1 standards?

Be direct, objective, uncompromising, and strictly technical. No polite filler. Provide concrete mathematical formulas and Python snippets for the corrections.
"""

    client = get_genai_client()
    print(f"[*] Dispatching adversarial audit prompt to {ARCHITECT_MODEL}...")

    verdict = call_model_with_fallback(
        client=client,
        primary_model=ARCHITECT_MODEL,
        fallback_model=ARCHITECT_FALLBACK,
        prompt=prompt,
        temperature=0.0,
    )

    OUTPUT_AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_AUDIT_PATH.write_text(verdict, encoding="utf-8")

    print("\n" + "=" * 90)
    print("                    GEMINI-4-ARGON ADVERSARIAL AUDIT VERDICT")
    print("=" * 90)
    print(verdict[:2500])
    if len(verdict) > 2500:
        print(f"\n... [Truncated. Full report ({len(verdict)} chars) saved to {OUTPUT_AUDIT_PATH}] ...")
    print("=" * 90)


if __name__ == "__main__":
    main()
