#!/usr/bin/env python3
"""Create a Minecraft .schem directly from a description or a ChatGPT blueprint.

No GabCon Studio required. Natural-language mode uses the already configured
mcbuild LLM backend (OpenRouter or Ollama); blueprint mode requires no AI key.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

from build_blueprint import build as build_blueprint
from dotenv import load_dotenv


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Direct Minecraft schematic creator: description → AI → .schem, or blueprint.py → .schem."
    )
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--prompt", help="Building description; requires a configured OpenRouter/Ollama model.")
    input_group.add_argument("--prompt-file", type=Path, help="UTF-8 file containing the building description.")
    input_group.add_argument("--blueprint", type=Path, help="Existing ChatGPT/mcbuild Python DSL file; no AI key.")
    parser.add_argument("--out", type=Path, default=Path("generated/direct-build"), help="Destination directory.")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--preview", choices=("none", "fast", "quality"), default="fast")
    parser.add_argument("--model", help="LLM model for --prompt or --prompt-file (e.g. qwen3.5:9b on Ollama).")
    parser.add_argument("--max-iters", type=int, default=4, help="Maximum AI refinement iterations (1..12).")
    parser.add_argument("--reasoning", choices=("off", "low", "medium", "high"), default="medium")
    parser.add_argument("--registry", type=Path, help="Optional server block-registry JSON.")
    parser.add_argument("--force", action="store_true", help="Replace a previous final.schem at the destination.")
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> Path:
    """Build and return the exact exported schematic path, or raise an actionable error."""
    load_dotenv()
    out = args.out.expanduser().resolve()
    schematic = out / "final.schem"
    if schematic.exists() and not args.force:
        raise FileExistsError(f"{schematic} already exists. Use a different --out or add --force.")

    if args.blueprint is not None:
        result = build_blueprint(args.blueprint, out, args.seed, registry=args.registry, preview=args.preview)
        if not result["schem"].is_file():
            raise RuntimeError("Blueprint finished without a schematic.")
        return result["schem"]

    if not 1 <= args.max_iters <= 12:
        raise ValueError("--max-iters must be between 1 and 12.")
    prompt = args.prompt
    if args.prompt_file is not None:
        file_path = args.prompt_file.expanduser()
        if not file_path.is_file() or file_path.stat().st_size > 20_000:
            raise ValueError("--prompt-file must be an existing UTF-8 description (max 20 KB).")
        prompt = file_path.read_text(encoding="utf-8").strip()
    if not prompt or not prompt.strip():
        raise ValueError("Provide a non-empty building description.")
    if len(prompt) > 12_000:
        raise ValueError("Description is too long (12,000 characters maximum).")

    # Give each call a unique destination: no ambiguity about which AI run won.
    agent_root = out / "_agent_runs" / uuid.uuid4().hex[:12]
    command = [
        sys.executable, "-m", "mcbuild.cli", prompt,
        "--out", str(agent_root), "--display", "off", "--no-stream",
        "--max-iters", str(args.max_iters), "--seed", str(args.seed),
        "--reasoning", args.reasoning,
    ]
    if args.model:
        command.extend(("--model", args.model))
    if args.registry:
        command.extend(("--registry", str(args.registry)))

    print("Starting the existing mcbuild AI agent (no Studio).")
    print("This mode uses the LLM backend configured in .env; it may incur API charges.")
    sys.stdout.flush()
    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            f"AI generation failed (exit {result.returncode}). Check LLM configuration, model and logs above."
        )
    outputs = list(agent_root.glob("*/final.schem"))
    if len(outputs) != 1:
        raise RuntimeError(
            "The agent did not produce a final.schem. Inspect the run logs inside "
            f"{agent_root} (model output may have failed validation)."
        )
    completed = outputs[0].parent
    if outputs[0].stat().st_size == 0:
        raise RuntimeError("The generated schematic is empty.")
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy2(outputs[0], schematic)
    final_code = completed / "final_blueprint.py"
    if final_code.is_file():
        shutil.copy2(final_code, out / "blueprint.py")
    render = sorted(completed.glob("iter_*/render.png"))
    if render and args.preview != "none":
        shutil.copy2(render[-1], out / "render.png")
    stats = sorted(completed.glob("iter_*/stats.json"))
    if stats:
        shutil.copy2(stats[-1], out / "stats.json")
    (out / "prompt.txt").write_text(prompt + "\n", encoding="utf-8")
    return schematic


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        result = run(args)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"WorldEdit schematic ready: {result}")
    print(f"Output directory: {result.parent}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
