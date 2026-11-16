# Program source export — 2026-11-16

## Added scope

Study Room, Korea/US Stock Research plus its Workroom UI, Agent Runtime, two optional CLI bridges, and the Integration Router. Existing Stella skills and the previously published Memory UI are reused without replacement.

## Adaptations

Repository-relative skill/module paths replace personal installation paths. The Study Room gets a non-overwriting empty-registry initializer and synthetic Java viewer; private course sources and exercise archives are excluded. Its optional paid model API path now requires the explicit `STELLA_ENABLE_PAID_API=1` opt-in in addition to provider credentials. The Workroom uses a CSS background instead of distributing the original image. Stock import tests use the canonical repository skill. Optional graph providers use `STELLA_CODE_TOOLS_ROOT`; optional integration scripts use `NODE_EXE`/PATH. Windows account-bound locks are preserved.

English README entry points describe execution requirements, costs and limitations. Existing Korean UI/instructions and clearly dated public-data examples remain; this is not a claim of complete English localization. The Workroom animation and stored SCHD example are explicitly identified as demonstrations, not executing agents or live analysis.

## Exclusions and provenance

No actual user memories, accounts/holdings, course documents, source registries, real question banks, research caches, logs, authentication files, session metadata, installed packages, binaries, graph indexes or model weights are included. Host-specific migration and verification scripts that depend on private archives are omitted. External server source archives are referenced rather than republished; the Agency Agents adaptation license and existing skill provenance are retained. The originals are not deleted or changed.

## Validation boundary

The current check parses exported Python and JSON files, runs Node syntax checks, scans explicit source files for selected credential/private-reference patterns, checks bundled file types, checks fixed static-asset routes, and verifies the final uploaded file hashes against the GitHub tree. Checks do not import or execute the target programs, sign in to providers, launch model requests, install dependencies, or create a real memory store.

Fresh unit/integration tests, browser behavior, Windows DPAPI/launchers, live SEC/DART requests, third-party chart availability, MCP authentication, and CLI/SDK model execution remain unverified in this exported layout. Syntax checks and included test source are not passing runtime tests. Use disposable synthetic data and an appropriately isolated local environment for follow-up execution. No complete security audit or measured whole-task token/cost saving is claimed.

Static results: 30 Python files parsed, 9 JSON files parsed, 13 JavaScript/module files passed Node syntax checking, 6 PowerShell files parsed without errors, and 20 fixed asset routes had existing files. Selected credential/private-reference pattern matches: zero. These results apply to the staged public source, not the original private runtime data or an executing deployment.
