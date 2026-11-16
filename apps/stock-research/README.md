# Korea and US stock research

A source-oriented research CLI with issuer resolution, official-source fetching, refresh-aware caching, local text/fact imports, SEC/DART data processing, selected financial calculations, and page-preserving PDF lookup. It does not connect to a broker or place orders. The existing command descriptions and research policy include Korean.

From this directory use Python 3.12+: `python -B -X utf8 -m stock_agent --data-dir ./private/research status`. Issuer matching: `python -B -X utf8 -m stock_agent --data-dir ./private/research resolve AAPL`. `status` describes configuration; it does not prove live authentication. See `python -m stock_agent --help` and [research policy](config/research-policy.md) for supported operations.

The stdlib core has no paid AI model API dependency. Actual remote retrieval depends on network availability, provider rules, and user configuration. SEC requests use a user-supplied `SEC_USER_AGENT`; DART features may require the user's `DART_API_KEY`. Do not commit either credentials or local configuration. No live quotes, current pricing, unlimited free quota, or provider authentication was verified for this export.

PDF extraction/tests optionally require `pypdf`; rendering requires Poppler on PATH. Document import reuses `../../skills/sources/study-cache/scripts/study_cache.py`. Local data goes into ignored `private/`; no collected reports, holdings, account records or source documents are bundled.

Synthetic test sources are in `tests/`: `python -B -X utf8 -m unittest discover -s tests -v`. The PDF tests need the optional document tools. These commands were not run in the current publication check; no passed-test count is claimed.

The separate [workroom](workroom/README.md) is a demonstration interface. Its animation is not an executing analyst team and its saved example is not live research.
