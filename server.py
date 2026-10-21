#!/usr/bin/env python3
"""Serve the ECHO website and proxy /api/ask to the local Zoom-bot AI stack."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
ECHO_API = os.environ.get("ECHO_API_BASE", "http://127.0.0.1:3000").rstrip("/")
PORT = int(os.environ.get("PORT", "8080"))
ASK_TIMEOUT = float(os.environ.get("ASK_TIMEOUT", "180"))


def fetch_json(url: str, timeout: float = 8.0) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/status":
            return self._status()
        if path in ("/chat", "/chat/"):
            self.path = "/chat.html"
        return super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/ask":
            return self._ask()
        self.send_error(404, "Not Found")

    def _json(self, code: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _status(self):
        out = {
            "ok": True,
            "website": True,
            "echoApi": ECHO_API,
            "bot": None,
            "ai": None,
            "ready": False,
            "detail": "",
        }
        try:
            bot = fetch_json(f"{ECHO_API}/health", timeout=5)
            out["bot"] = {"ok": bool(bot.get("ok")), "state": bot.get("state")}
        except Exception as exc:  # noqa: BLE001
            out["detail"] = f"bot unreachable: {exc}"
            return self._json(200, out)

        try:
            ai = fetch_json(f"{ECHO_API}/ai/health", timeout=8)
            out["ai"] = ai
            enabled = bool((ai.get("ai") or {}).get("enabled", ai.get("ok")))
            out["ready"] = bool(ai.get("ok")) and enabled
            if not out["ready"]:
                out["detail"] = "AI stack reported not ready"
        except Exception as exc:  # noqa: BLE001
            out["detail"] = f"ai health unreachable: {exc}"
        return self._json(200, out)

    def _ask(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return self._json(400, {"ok": False, "error": "invalid JSON"})

        question = str(payload.get("question") or "").strip()
        if not question:
            return self._json(400, {"ok": False, "error": "question is required"})
        if len(question) > 2000:
            return self._json(400, {"ok": False, "error": "question too long"})

        body = json.dumps(
            {
                "question": question,
                "senderName": "web-visitor",
                "replyType": "manual",
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{ECHO_API}/ai/ask",
            data=body,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=ASK_TIMEOUT) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            try:
                data = json.loads(exc.read().decode("utf-8"))
            except Exception:  # noqa: BLE001
                data = {"ok": False, "error": f"upstream HTTP {exc.code}"}
            return self._json(502, data if isinstance(data, dict) else {"ok": False, "error": str(data)})
        except Exception as exc:  # noqa: BLE001
            return self._json(
                503,
                {
                    "ok": False,
                    "error": f"AI backend unavailable ({exc}). The answer LLM / VLM services may still be starting.",
                },
            )

        answer = (
            data.get("finalAnswer")
            or data.get("answer")
            or data.get("reply")
            or data.get("text")
            or ""
        )
        return self._json(
            200,
            {
                "ok": bool(data.get("ok", True)) and bool(answer),
                "answer": answer,
                "error": data.get("error") or ("" if answer else "empty answer"),
                "latencyMs": data.get("latencyMs") or data.get("elapsedMs"),
                "rawKeys": sorted(list(data.keys()))[:24],
            },
        )

    def log_message(self, fmt: str, *args):
        sys_stderr = __import__("sys").stderr
        sys_stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"ECHO website + /api/ask proxy on http://0.0.0.0:{PORT} -> {ECHO_API}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
