"""GabCon Studio: local-only HTTP server using the real mcbuild engine.

Usage (from the GabCon-BuildAI repository root):
    uv run python gabcon-studio/server.py
Open http://127.0.0.1:8788

No AI API keys needed: ChatGPT generates code in chat, then you paste it here.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import threading
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from dotenv import load_dotenv

from studio_config import DETAILED_PREVIEW_MAX_BLOCKS, studio_block_limit

STUDIO_DIR = Path(__file__).resolve().parent
PROJECT_DIR = STUDIO_DIR.parent
STATIC_DIR = STUDIO_DIR / "static"
RUNS_DIR = STUDIO_DIR / "runs"
RUNS_DIR.mkdir(parents=True, exist_ok=True)
HOST = "127.0.0.1"
PORT = 8788
MAX_BODY = 550_000
BUILD_TIMEOUT = 900
ARTIFACTS = {"blueprint.py", "render.png", "final.schem", "stats.json", "voxels.json"}
EXT_MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".png": "image/png",
    ".schem": "application/octet-stream",
    ".py": "text/x-python; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".webmanifest": "application/manifest+json; charset=utf-8",
    ".svg": "image/svg+xml",
}
BUILD_LOCK = threading.Lock()


def clean_name(value: str) -> str:
    return (re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")[:35] or "construction")


def metadata_for(identifier: str) -> dict | None:
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,100}", identifier):
        return None
    d = RUNS_DIR / identifier
    stats = d / "stats.json"
    if not stats.is_file():
        return None
    try:
        data = json.loads(stats.read_text(encoding="utf-8"))
        details = json.loads((d / "project.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return {
        "id": identifier,
        "name": details["name"],
        "created_at": details["created_at"],
        "stats": data,
        "urls": {f.split(".")[0] if f != "final.schem" else "schem": f"/artifacts/{identifier}/{f}"
                 for f in sorted(ARTIFACTS) if (d / f).exists()},
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "GabConStudio/1.0"

    def log_message(self, fmt, *args):
        print("[studio] " + fmt % args)

    def send_json(self, status: int, obj: dict | list) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, target: Path, download: bool = False):
        if not target.is_file():
            return self.send_error(404)
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", EXT_MIME.get(target.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        if download:
            self.send_header("Content-Disposition", f'attachment; filename="{target.name}"')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        path = unquote(urlparse(self.path).path)
        if path == "/api/health":
            ready = (PROJECT_DIR / "pyproject.toml").is_file() and (PROJECT_DIR / "src" / "mcbuild").is_dir()
            return self.send_json(200, {
                "ok": True,
                "project_detected": ready,
                "api_required": False,
                "studio_max_blocks": studio_block_limit(),
                "detailed_preview_max_blocks": DETAILED_PREVIEW_MAX_BLOCKS,
            })
        if path == "/api/builds":
            ids = sorted((d.name for d in RUNS_DIR.iterdir() if d.is_dir()), reverse=True)
            builds = [m for identifier in ids[:30] if (m := metadata_for(identifier))]
            return self.send_json(200, builds)
        if path.startswith("/api/builds/"):
            item = metadata_for(path.split("/")[-1])
            return self.send_json(200, item) if item else self.send_error(404)
        if path.startswith("/artifacts/"):
            parts = path.split("/")
            if (len(parts) != 4 or not re.fullmatch(r"[a-zA-Z0-9_-]{1,100}", parts[2])
                    or parts[3] not in ARTIFACTS):
                return self.send_error(404)
            return self.send_file(RUNS_DIR / parts[2] / parts[3], download=parts[3] in ("blueprint.py", "final.schem", "stats.json"))
        if path == "/":
            path = "/index.html"
        target = (STATIC_DIR / path.lstrip("/")).resolve()
        if not target.is_relative_to(STATIC_DIR.resolve()):
            return self.send_error(403)
        return self.send_file(target)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/build":
            return self.send_error(404)
        # Browsers must send a JSON same-origin request. This prevents other sites
        # from silently triggering a local build (e.g. via a form or no-cors fetch).
        fetch_site = self.headers.get("Sec-Fetch-Site", "")
        if fetch_site and fetch_site not in ("same-origin", "none"):
            return self.send_json(403, {"error": "Requête intersite refusée."})
        media_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if media_type != "application/json":
            return self.send_json(415, {"error": "Type de requête non pris en charge : JSON requis."})
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self.send_json(400, {"error": "Taille de requête invalide."})
        if length <= 0 or length > MAX_BODY:
            return self.send_json(413, {"error": "Code trop volumineux (limite 550 Ko)."})
        try:
            data = json.loads(self.rfile.read(length))
            source = data.get("source", "")
            name = str(data.get("name", "Construction"))[:100].strip()
            seed = int(data.get("seed", 0))
            if not isinstance(source, str) or not source.strip():
                raise ValueError("Colle du code Python avant de lancer la génération.")
            if not 0 <= seed < 2**31:
                raise ValueError("La graine doit être comprise entre 0 et 2147483647.")
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            return self.send_json(400, {"error": str(exc)})
        if not (PROJECT_DIR / "src" / "mcbuild" / "dsl" / "sandbox.py").is_file():
            return self.send_json(400, {"error": "Place le dossier gabcon-studio directement à la racine de GabCon-BuildAI puis lance uv sync."})
        if not BUILD_LOCK.acquire(blocking=False):
            return self.send_json(409, {"error": "Une construction est déjà en cours."})
        try:
            now = datetime.now(timezone.utc)
            identifier = f"{now.strftime('%Y%m%d-%H%M%S')}-{clean_name(name)}-{uuid.uuid4().hex[:5]}"
            output = RUNS_DIR / identifier
            output.mkdir(parents=True, exist_ok=True)
            source_path = output / "blueprint.py"
            source_path.write_text(source, encoding="utf-8")
            (output / "project.json").write_text(json.dumps({
                "name": name or "Construction", "created_at": now.isoformat()
            }, ensure_ascii=False), encoding="utf-8")
            try:
                proc = subprocess.run(
                    [sys.executable, str(STUDIO_DIR / "worker.py"), str(source_path), str(output), str(seed)],
                    cwd=PROJECT_DIR, capture_output=True, text=True,
                    timeout=BUILD_TIMEOUT, check=False, stdin=subprocess.DEVNULL,
                )
            except subprocess.TimeoutExpired:
                print(f"[studio] Generation time-out: {identifier} ({BUILD_TIMEOUT}s)", flush=True)
                return self.send_json(408, {"error": (
                    f"Délai dépassé après {BUILD_TIMEOUT} secondes pendant le calcul ou l'export. "
                    "Essaie une construction plus petite ou moins complexe."
                )})
            if proc.returncode != 0:
                # Our worker always prints a JSON error line, but dependency errors can be plain text.
                details = proc.stdout.strip().splitlines()
                message = ""
                if details:
                    try:
                        message = json.loads(details[-1]).get("error", "")
                    except json.JSONDecodeError:
                        pass
                if not message:
                    message = (proc.stderr or "Échec du moteur BuildAI.")[-1200:]
                print(f"[studio] Build failed ({identifier}): {message}", flush=True)
                return self.send_json(422, {"error": message})
            item = metadata_for(identifier)
            if not item:
                return self.send_json(500, {"error": "Le moteur n'a pas produit de résultat exploitable."})
            return self.send_json(200, item)
        finally:
            BUILD_LOCK.release()


def main() -> None:
    load_dotenv(PROJECT_DIR / ".env")
    print("\n  GABCON STUDIO  /  interface locale BuildAI")
    print(f"  → http://{HOST}:{PORT}")
    print(f"  → Limite de blocs : {studio_block_limit():,} (configurable via .env)")
    print("  → Aucun appel API ChatGPT/OpenRouter depuis l'interface.")
    print("  → Ne pas exposer sur Internet (sandbox prévue contre les erreurs, pas le code hostile).\n")
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServeur arrêté.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
