import os
import sys


def _bootstrap_src_path() -> None:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    src_path = os.path.join(repo_root, "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)


def main() -> None:
    _bootstrap_src_path()
    from ambient_agent.cli import main as cli_main

    cli_main()


if __name__ == "__main__":
    main()