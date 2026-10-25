# AGENTS.md

AbsBox is a Python client (wrapper) for the Haskell `Hastructure` structured-finance
cashflow engine, whose source lives at `../Hastructure`. Hastructure exposes a Servant
REST API and uses Aeson for JSON encode/decode — those types/tags are the wire contract
AbsBox builds and parses. AbsBox builds a JSON DSL, POSTs it to an engine HTTP server,
and decodes responses into pandas DataFrames. `absbox/local/*` is pure offline DSL
construction — no server is needed until an `API.run*` call.

## Commands
- Dev install: `pip install -e ".[test]"` (what CI does) or `uv sync` (uses `uv.lock`).
  Python >=3.10 is required (hard `ImportError` otherwise). A `.venv` exists; `shell.nix` sources it.
- Offline tests (the hermetic CI suite, no engine): `pytest absbox/tests/test_parsers.py`
- Full tests: `pytest absbox/tests` — engine-dependent tests self-skip unless a server is
  reachable and `absbox/tests/config.json` exists (that file is gitignored).
- Regression vs a specific engine: `just regression local|dev|prod` (sets
  `ABSBOX_TEST_SERVER` and runs `absbox/tests/regression/test_main.py`).
- Lint: `ruff check absbox` (select `E9,F63,F7,F82,ISC002`; ISC002 guards the missing-comma
  string-concat bug class, gh #99; baseline verified clean)
  Typecheck: `python -m mypy` (advisory; baseline ~30 errors; findings post as inline PR
  annotations via `tools/annotate_from_log.py`, never failing CI)
- Advisory analyzers (gh #51): CI warns-only job runs mypy + pyright (`pyrightconfig.json`,
  basic mode) as inline PR annotations under `continue-on-error`. Local equivalent:
  `just code-inspect [target] [pyright_version]` writes `<git-hash>_code_inspect.md`.

## Engine / test gotchas
- Client and server **minor** versions must match, else `VersionMismatch` from
  `API.__post_init__` in `absbox/client.py:209`. Pass `check=False` to bypass (regression tests do).
- `absbox/tests/config.json` holds `test_server`; regression tests skip when it is missing or
  unreachable. Server tests also auto-skip in CI unless `ABSBOX_REGRESSION=1`.
- Engine paths: `EnginePath.LOCAL=http://localhost:8081`, `DEV/PROD=https://absbox.org/api/{dev,latest}`.

## Layout
- `absbox/client.py` — `API` (request builders + HTTP), `EnginePath`, `PickApiFrom`.
- `absbox/local/` — offline DSL: `component.py` (builder primitives), `generic.py` (`Generic`
  deal, English), `china.py` (`信贷ABS`/`SPV`, Chinese aliases), `interface.py` (`mkTag`,
  `readAeson`), `util.py`, `cf.py` (cashflow readers), `readers.py`.
- `absbox/deal.py` — `mkDeal` and deal/assumption combinators. `absbox/library.py` — hosted
  deal-library client (token auth). `absbox/report.py`, `rootFinder.py`, `validation.py`.
- `absbox/examples/` and `docs/source/nbsample/` hold sample deals used by tests and docs.
- `absbox/skill/` is empty; the AI skill lives in the external `absbox-skill` repo.

## Conventions / traps
- `component.py`/`generic.py`/`china.py` deliberately re-export many names; ruff `F401` is
  disabled on purpose. Do not "clean up" unused imports there — downstream and users rely on them.
  Modules must resolve their own names (a test guards against star-import leakage).
- Chinese and English field aliases are both supported; keep them in sync (e.g. `封包日`/`cutoffDate`).
- Version is single-sourced in `pyproject.toml [project].version`; Sphinx derives from it.
  Bump with `just update-version X.Y.Z` (also runs `uv lock`); don't edit the version elsewhere.
- Changelog uses towncrier fragments under `changes/` (`feature`/`enhance`/`bug`); never
  hand-edit `CHANGELOG.rst`.
- ruff checks only `E9,F63,F7,F82`, excludes `docs`/`notebooks`, line-length 127.
- Release: `just publish v X.Y.Z` (code-inspect gate -> regression dev -> bump -> tag -> push;
  publish stops if the ruff gate reports findings); the `v*` tag workflow publishes to PyPI.
