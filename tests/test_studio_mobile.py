"""Check that the mobile Studio PWA has installable, safe static assets."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "gabcon-studio" / "static"


def test_mobile_manifest_and_icons():
    manifest = json.loads((ROOT / "manifest.webmanifest").read_text(encoding="utf-8"))
    assert manifest["display"] == "standalone"
    assert manifest["start_url"] == "/"
    sizes = {icon["sizes"] for icon in manifest["icons"]}
    assert sizes == {"192x192", "512x512"}
    for icon in manifest["icons"]:
        icon_path = ROOT / icon["src"].lstrip("/")
        assert icon_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_mobile_shell_assets_and_no_api_cache():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    script = (ROOT / "sw.js").read_text(encoding="utf-8")
    app_js = (ROOT / "app.js").read_text(encoding="utf-8")
    assert "/manifest.webmanifest" in html
    assert "/icon-192.png" in html
    assert 'id="installBtn"' in html
    assert "navigator.serviceWorker.register('/sw.js')" in app_js
    assert "url.origin !== self.location.origin" in script
    assert "/api/" not in script
    assert "/artifacts/" not in script
