"""Serve the static PWA locally using only the Python standard library."""

from __future__ import annotations

import argparse
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.dont_write_bytecode = True

from scripts.export_pages_data import main as export_pages_data

DOCS_DIR = Path(__file__).resolve().parent / "docs"


class PWAHandler(SimpleHTTPRequestHandler):
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".mjs": "text/javascript",
        ".webmanifest": "application/manifest+json",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the 539 PWA locally")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    export_pages_data()
    handler = partial(PWAHandler, directory=str(DOCS_DIR))
    with ThreadingHTTPServer((args.host, args.port), handler) as server:
        print(f"Open http://{args.host}:{args.port}/", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
