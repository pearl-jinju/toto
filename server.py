from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os

if __name__ == "__main__":
    directory = Path(__file__).resolve().parent / "public"
    handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
    with ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "8000"))), handler) as server:
        server.serve_forever()
