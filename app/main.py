from __future__ import annotations

from app.bootstrap import bootstrap


def main() -> int:
    runtime = bootstrap()
    return runtime.start()


if __name__ == "__main__":
    raise SystemExit(main())
