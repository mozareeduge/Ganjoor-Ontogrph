"""`ontograph` console script.

Spec §62 (CLI as reproducibility layer) and §78 (Claude Code invocation
pattern: every verb accepts --json, non-zero exit + stderr on failure,
never a silent empty-JSON success). Verb names deliberately avoid
`search`/`query` (spec §25 v2.3.0 disambiguation note -- those names belong
to the sibling persian-poetry-mcp skill's retrieval surface, not here).

Implemented in ledger rows P5.1-P5.3. This stub's `main()` exists only so
`pip install -e .`'s console_scripts entry point resolves; it is not yet
a working CLI.
"""


def main() -> None:
    raise NotImplementedError(
        "ontograph CLI is not implemented yet -- see IMPLEMENTATION_LEDGER.md Phase 5"
    )


if __name__ == "__main__":
    main()
