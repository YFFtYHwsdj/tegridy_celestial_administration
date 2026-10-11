#!/usr/bin/env python3
"""Backward-compatible entry point for the general vanilla override check."""
from check_upstream_overrides import body, check, main, tokens


if __name__ == "__main__":
    raise SystemExit(main())
