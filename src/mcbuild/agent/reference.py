"""Reference-image preflight analysis and independent visual critique.

The builder should not have to rediscover the reference architecture on every turn.
This module extracts a persistent ReferenceSpec once, keeps model-facing images at a
useful resolution, and runs a stateless critic after each successful build.
"""

from __future__ import annotations

import json
import re
from typing import Any

from PIL import Image

from mcbuild.llm.client import image_to_data_url

REFERENCE_SPEC_VERSION = 1
DEFAULT_REFERENCE_MAX_SIDE = 1024
DEFAULT_VIEW_MAX_SIDE = 768


def fit_image_for_model(img: Image.Image, max_side: int) -> Image.Image:
    """Return an RGB copy whose longest edge is at most max_side.

    Never upscales: generated references that are already smaller stay pixel-identical
    apart from RGB conversion.
    """
    out = img.convert("RGB")
    if max(out.size) <= max_side:
        return out.copy()
    out = out.copy()
    out.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    return out


def _message_text(message: Any) -> str:
    return str(getattr(message, "content", None) or "").strip()


def _extract_json_object(text: str) -> dict[str, Any] | None:
    """Best-effort parse of a JSON object, tolerating fenced model output."""
    if not text:
        return None
    cleaned = text.strip()
    cleaned = re.sub(r"^\s*```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned)
    try:
        value = json.loads(cleaned)
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        value = json.loads(cleaned[start : end + 1])
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        return None


def _reference_analysis_prompt(building_prompt: str) -> str:
    return f"""Analyze the attached Minecraft-style architectural reference before any
blueprint is written. The target request is: {building_prompt!r}

Return JSON ONLY. Do not write Python and do not propose DSL code. Estimate geometry from
the image rather than inventing hidden details. Ratios and relative positions matter more
than exact absolute dimensions.

Use this schema:
{{
  "version": {REFERENCE_SPEC_VERSION},
  "target_dimensions": {{"width": int, "depth": int, "height": int}},
  "proportions": {{
    "width_to_depth": number,
    "height_to_width": number,
    "vertical_emphasis": "low|medium|high|extreme"
  }},
  "storeys": int,
  "symmetry": "string",
  "primary_masses": [
    {{
      "name": "string",
      "relative_position": "string",
      "footprint_fraction": [number, number],
      "height_fraction": number,
      "roof": "string"
    }}
  ],
  "towers": [
    {{
      "role": "string",
      "count": int,
      "relative_positions": ["string"],
      "height_fraction": number,
      "roof": "string"
    }}
  ],
  "roof_system": ["string"],
  "facade_rhythm": {{
    "window_shape": "string",
    "window_density": "sparse|medium|dense",
    "vertical_bays": "string",
    "buttresses_or_piers": "string"
  }},
  "palette": [
    {{
      "visual_material": "string",
      "minecraft_blocks": ["string"],
      "role": "string"
    }}
  ],
  "distinctive_features": ["string"],
  "priority_constraints": [
    "ordered, measurable visual facts the build must preserve"
  ],
  "uncertainties": ["details not actually visible or ambiguous in the image"]
}}

Choose practical Minecraft dimensions large enough to preserve the visible silhouette,
normally below roughly 160 blocks on any axis unless the reference clearly needs more.
The first priority_constraints should describe the largest silhouette/massing facts.
"""


def analyze_reference(
    llm: Any,
    model: str,
    building_prompt: str,
    reference_image: Image.Image,
    *,
    reasoning: str = "medium",
) -> dict[str, Any]:
    """Run a fresh, tool-free vision call and return a persistent ReferenceSpec."""
    messages = [
        {
            "role": "system",
            "content": (
                "You are a strict architectural vision analyst for Minecraft reconstruction. "
                "Your job is measurement and decomposition, not design. Return valid JSON only."
            ),
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": _reference_analysis_prompt(building_prompt)},
                {"type": "image_url", "image_url": {"url": image_to_data_url(reference_image)}},
            ],
        },
    ]
    result = llm.chat(
        model=model,
        messages=messages,
        tools=None,
        reasoning=reasoning,
        stream=False,
    )
    text = _message_text(result.message)
    spec = _extract_json_object(text)
    if spec is None:
        return {
            "version": REFERENCE_SPEC_VERSION,
            "parse_status": "unparsed",
            "raw_analysis": text,
            "priority_constraints": [
                "Match the reference silhouette, massing hierarchy, roof shapes, opening rhythm, and palette."
            ],
        }
    spec.setdefault("version", REFERENCE_SPEC_VERSION)
    spec["parse_status"] = "ok"
    return spec


def _critic_prompt(reference_spec: dict[str, Any], stats: dict, labels: list[str]) -> str:
    return f"""Compare the REFERENCE against the CURRENT BUILD views as an independent visual QA critic.
Do not write blueprint code. Do not praise the build. Focus on discrepancies that are visible
and actionable. The builder will receive your JSON verbatim.

REFERENCE SPEC:
{json.dumps(reference_spec, indent=2)}

CURRENT BUILD STATS:
{json.dumps(stats, indent=2)}

VIEW LABELS:
{json.dumps(labels)}

Return JSON ONLY with:
{{
  "same_build_read": "yes|partial|no",
  "biggest_discrepancies": [
    {{
      "rank": 1,
      "category": "massing|proportions|roof|towers|openings|palette|detail",
      "observation": "specific visible mismatch",
      "evidence": "which reference/build feature or view shows it",
      "suggested_change": "geometric/material change, no code"
    }}
  ],
  "preserve": ["things already close enough that the next edit should not regress"],
  "next_focus": "single highest-leverage correction"
}}

Return at most 3 discrepancies, ordered by visual importance. Prefer large silhouette and
massing errors over micro-detail. Be strict: execution success is irrelevant to similarity.
"""


def critique_reference(
    llm: Any,
    model: str,
    reference_image: Image.Image,
    reference_spec: dict[str, Any],
    renderings: list[tuple[str, Image.Image]],
    stats: dict,
    *,
    reasoning: str = "medium",
) -> dict[str, Any]:
    """Run a fresh critic call with no builder conversation/history."""
    labels = [label for label, _ in renderings]
    content: list[dict[str, Any]] = [
        {"type": "text", "text": _critic_prompt(reference_spec, stats, labels)},
        {"type": "text", "text": "REFERENCE:"},
        {"type": "image_url", "image_url": {"url": image_to_data_url(reference_image)}},
    ]
    for i, (label, image) in enumerate(renderings, start=1):
        content.append({"type": "text", "text": f"CURRENT BUILD VIEW {i}: {label}"})
        content.append({"type": "image_url", "image_url": {"url": image_to_data_url(image)}})

    result = llm.chat(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an independent visual critic. You did not author the build. "
                    "Compare geometry objectively and return valid JSON only."
                ),
            },
            {"role": "user", "content": content},
        ],
        tools=None,
        reasoning=reasoning,
        stream=False,
    )
    text = _message_text(result.message)
    critique = _extract_json_object(text)
    if critique is None:
        return {"parse_status": "unparsed", "raw_critique": text}
    critique["parse_status"] = "ok"
    return critique
