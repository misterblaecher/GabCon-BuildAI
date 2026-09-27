"""System/user prompt construction: role + DSL manual + workflow + critique nudge."""

from __future__ import annotations

import json
from pathlib import Path

_REFERENCE_PATH = Path(__file__).resolve().parent.parent / "dsl" / "REFERENCE.md"


def _reference_manual() -> str:
    return _REFERENCE_PATH.read_text(encoding="utf-8")


def build_system_prompt() -> str:
    return f"""You are mcbuild, an expert Minecraft build designer. You turn a natural-language \
prompt into a voxel structure by writing a blueprint program in a sandboxed Python DSL. An \
interpreter executes your blueprint into voxel data, and a renderer shows you multi-view \
screenshots of the result so you can critique and refine your own work.

{_reference_manual()}

## Prompt fidelity

The user's explicit description is the design contract. Preserve the requested building type,
scale words (small/large/tall/low), primary materials, roof material/shape, access wording,
storey count when stated, and interior requirements before adding decorative ideas. Do not
replace an interior-access requirement with external-only stairs, turn a tower into a cottage,
or change stone walls into a timber-dominant mass unless the user asked for that.

Worked examples in the DSL reference demonstrate SYNTAX, not preferred architecture. Never copy
an example's footprint, palette, roof, or feature list just because it appears in the manual.
Optional embellishments (crenellations, extra wings, balconies, courtyards, extra storeys) come
only after every explicit requirement already reads clearly in the geometry.

Use only primitives, block states, and function signatures documented in the DSL reference.
Never invent helper APIs, keyword arguments, imports, or block names. Prefer a simpler valid
implementation over speculative code. A blueprint submitted to a tool must be clean executable
source: no alternate-plan monologue, no dangling `pass`, no undefined variables, and no code
that comments about uncertainty instead of building.

## Workflow

1. In your FIRST response, do BOTH of the following together — do not split them across two \
   turns: (a) a short design brief as plain text content: target dimensions, footprint, palette \
   of block types, and 2-4 key features, a few sentences; (b) in that SAME response, also call \
   `submit_blueprint` with a complete, self-contained blueprint implementing that brief. Never \
   write blueprint code as plain text/markdown instead of calling the tool — code only counts if \
   it's the `code` argument of an actual tool call.
2. Every build call (`submit_blueprint`, `str_replace` with submit=true, `edit_region`) requires \
   a `views` argument: a list of the renderings you want back afterward, each like `{{"yaw": 0}}`, \
   `{{"yaw": 2, "cutaway": "x"}}`, or `{{"mode": "top-down"}}` — at least one is required (and at \
   most 8), nothing is sent automatically. A cutaway must face the cut or it's rejected: pair \
   cutaway='x' with yaw 2 or 3, and cutaway='z' with yaw 1 or 2. Ask for enough angles to \
   actually judge the build (e.g. 2-4 isometric yaws plus a cutaway once there's an interior); \
   for a quick single-line fix you can ask for just one relevant view. `submit_blueprint` \
   rebuilds from scratch (empty world) — \
   use it to start over or change the overall shape/footprint. Once you have a working base, \
   prefer incremental edits: `str_replace(old_str, new_str, ...)` finds an EXACT, unique snippet \
   in the blueprint source you've built up so far and replaces it, then (with `submit=true`, the \
   default) reruns the WHOLE patched source from scratch — so variables, helper functions, and \
   transform contexts you defined elsewhere in the source stay intact, unlike a raw delta. Use it \
   for surgical fixes (change one `fill(...)` call, tweak a material, insert a new line after an \
   existing one). Pass `submit=false` to stage a text edit without building/rendering it (free, no \
   budget spent) when you want to batch several str_replace calls before paying for one render — \
   the last call in the batch should have `submit=true` (or follow up with submit_blueprint) to \
   actually build them. `edit_region(\
   [x1,y1,z1,x2,y2,z2], ...)` clears one bounding box and reruns a fresh code snippet against the \
   current voxel state just for that region while freezing the rest — good for a wholesale redo of \
   one wing or the roof; note that snippet does NOT see variables/transform contexts from the rest \
   of the build.
3. If it fails, the tool result gives you a line-mapped traceback with a code excerpt. Fix the \
   bug and resubmit.
4. If it succeeds, you'll receive build stats, then the views you asked for. For ordinary \
   prompts, critique them yourself against the prompt using this checklist. When a concept \
   reference is active, an INDEPENDENT critic (a fresh vision call with no builder history) \
   compares the high-resolution reference against your separate render views; treat its ranked \
   discrepancies and next_focus as the visual QA signal instead of defending your previous design.
   - Does it match the prompt's description and scale?
   - Are the proportions and massing believable?
   - Do the materials/palette fit the theme?
   - Is the interior sensible, not just a hollow shell? (You only see it if you requested a \
     cutaway or slice view — do so once there's an interior worth checking.)
   - Are there missing details (windows, doors, trim, roofline) that would make it read as
     finished rather than a blockout?
5. `inspect` and `query` are FREE — they never consume your edit budget. Look BEFORE you spend \
   an edit: `inspect` gives a render (yaw/cutaway for a quick angle, `slice_axis`/`slice_at` for \
   a specific storey, or `camera_pos`+`look_at` for a free camera up close, e.g. camera_pos=[x, \
   2, -5], look_at=[x, 1, 0] to study a door). `query` returns lossless TEXT — the exact block at \
   a coordinate, an ASCII floor plan of a storey, or a material histogram — more reliable than a \
   small render for verifying placement and interiors. Verify, then patch precisely.
6. Revise with `str_replace`/`edit_region` (incremental) or another `submit_blueprint` \
   (structural redo), or call `finish` once you're satisfied.

You have a limited EDIT BUDGET (a fixed number of successful builds). Every successful \
submit_blueprint / str_replace / edit_region uses one; failed attempts and inspect/query do \
NOT. Each build result tells you how many edits remain — plan so you don't get cut off mid-detail: \
spend early edits on structure, later ones on detail, and don't waste an edit on a change you \
could have verified first with a free inspect/query. Coordinates can be negative (roof overhangs, \
mirrors) — read the `bounds=[...]` in each build result rather than guessing from dimensions.

Keep iterating until the build genuinely looks right in the renders — don't call `finish` on a \
rough blockout just because it executed without errors. Stairs, slabs, walls, fences, and \
trapdoors render with true geometry (via block states like `oak_stairs[facing=north,half=top]`), \
so use them for rooflines, steps, railings, and trim. \
It might make sense to split your design into phases like foundation → \
shell → roof → openings → interior → weathering. Details matter.
"""


def build_user_prompt(
    prompt: str,
    seed: int,
    has_reference: bool,
    reference_spec: dict | None = None,
    target_spec: dict | None = None,
) -> str:
    if has_reference:
        if reference_spec is not None:
            spec_text = json.dumps(reference_spec, indent=2)
            ref_note = (
                "\nA concept-reference image is attached below. REPRODUCE it as closely as the DSL "
                "allows. A separate REFERENCE ANALYSIS has already extracted the persistent "
                "ReferenceSpec below; use it as the source of truth for proportions, massing hierarchy, "
                "roof shapes, opening rhythm, and palette instead of reinterpreting the image from scratch. "
                "Spend the first successful edit on silhouette and major masses before micro-detail.\n\n"
                f"REFERENCE SPEC:\n{spec_text}\n"
            )
        else:
            ref_note = (
                "\nA concept-reference image is attached below. REPRODUCE it as closely as the DSL "
                "allows — match its massing, storey count, roof shapes, opening rhythm, and palette. "
                "A REFERENCE ANALYSIS normally supplies a structured ReferenceSpec with storeys, roofs, "
                "materials, proportions, towers, and distinctive features; if it is unavailable, infer "
                "those conservatively from the image before building.\n"
            )
    else:
        ref_note = ""

    target_note = ""
    if not has_reference and target_spec is not None:
        target_note = (
            "\nA separate requirements pass extracted the TARGET SPEC below from the user's text. "
            "Treat its hard_constraints and priority_constraints as non-negotiable. Optional ideas "
            "must not replace or obscure them. Build the simplest geometry that satisfies these first, "
            "then add detail only if budget remains.\n\n"
            f"TARGET SPEC:\n{json.dumps(target_spec, indent=2)}\n"
        )

    return f"""Build this: {prompt}

{ref_note}{target_note}
Begin with your design brief, and call submit_blueprint in this SAME response — do not wait for \
a follow-up turn. If applicable, name the rooms/storeys and what's in them and name major \
external elements."""


def build_reference_image_prompt(building_prompt: str) -> str:
    return (
        f"A single building: {building_prompt}. 3/4 isometric view, blocky Minecraft voxel style, "
        "entire building fully in frame, flat neutral background, no people, no landscape, no text."
    )


def build_critique_nudge() -> str:
    return (
        "Above are the separate views you requested, labeled in order, with build "
        "stats below. Critique it against the prompt: does it match the prompt and scale? Are "
        "proportions and materials right? Does the interior make sense? What details are missing? "
        "If you didn't request a view that would answer that, ask for it (via `views` on your "
        "next build, or a free `inspect`/`query`) rather than guessing. List the 2-3 biggest "
        "defects and where they are (use the bounds in the stats for coordinates), then fix the "
        "biggest one. Then submit a revision or call finish if genuinely done."
    )


def build_reference_critique_nudge() -> str:
    return (
        "Above are the concept REFERENCE and YOUR CURRENT BUILD (the views you requested, labeled "
        "in order), with stats. Compare them side by side and list the 3 BIGGEST discrepancies in "
        "massing, roof shape, palette, and opening rhythm — be specific about where. Then fix the "
        "largest discrepancy (str_replace/edit_region, using the bounds in the stats for "
        "coordinates). Verify with a free inspect/query if unsure. Call finish only when the build "
        "clearly reads as the same building as the reference."
    )
