"""Allow `python -m my_cli_tool`."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
