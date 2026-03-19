"""Allow `python -m capbench` to behave like the `capbench` console script."""

from .cli import main


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
