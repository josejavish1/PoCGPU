#!/usr/bin/env python3
"""Generates tests/domain/test_actuarial_engine.py using gemini-4-argon."""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, "/home/jsanchhi/assessment_engine/src")

from assessment_engine.infrastructure.genai_client import (
    ModelTier,
    create_genai_client,
    get_model,
)

client = create_genai_client()
model = get_model(ModelTier.REASONING)

service_code = (REPO_ROOT / "src/domain/services/actuarial_engine.py").read_text(encoding="utf-8")
prompt = f"""
Write comprehensive unit tests in `tests/domain/test_actuarial_engine.py` for this domain service:
```python
{service_code}
```

Requirements:
- 100% Technical English, zero Spanish literals.
- Pure pytest test cases testing `evaluate_on_premise_hardware_risk` and `evaluate_cloud_spot_preemption_risk`.
- Test normal cases, edge cases (zero spare, invalid node counts, boolean validation, negative counts).
- Output ONLY valid Python code in a single markdown block.
"""

res = client.models.generate_content(model=model, contents=prompt)
match = re.search(r"```(?:python)?\s*\n(.*?)\n```", res.text, re.DOTALL)
code = match.group(1) if match else res.text
(REPO_ROOT / "tests/domain/test_actuarial_engine.py").write_text(code.strip() + "\n", encoding="utf-8")
print("Wrote tests/domain/test_actuarial_engine.py successfully!")
