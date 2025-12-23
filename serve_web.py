import sys
from pathlib import Path
from textual_serve.server import Server

if __name__ == "__main__":
    tui_path = Path(__file__).parent / "tui.py"
    server = Server(f"{sys.executable} {tui_path}", host="0.0.0.0", port=8889)
    server.serve()
