"""Entry point: python -m susu  or  python -m susu --demo"""

import sys
from .cli import run_demo, run_interactive


def main() -> None:
    if "--demo" in sys.argv:
        run_demo()
    else:
        run_interactive()


if __name__ == "__main__":
    main()
