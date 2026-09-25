from __future__ import annotations

import argparse
from observability.dashboard import launch_dashboard


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch Day 10 Observability & Drift Dashboard")
    parser.add_argument("--port", type=int, default=8501, help="Port to bind server (default: 8501)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open browser")
    args = parser.parse_args()

    launch_dashboard(port=args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
