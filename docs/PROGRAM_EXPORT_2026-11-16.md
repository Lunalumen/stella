# User-edition program source verification — 2026-11-16

## Audience and privacy

This report concerns the public package that users can download. It is not a description of an individual's computer, accounts, installed services, or private security settings. Users choose their own local data directories and credentials; neither is included in the public package.

## Added scope

Study Room, Korea/US Stock Research plus its Workroom UI, Agent Runtime, two optional CLI bridges, and the Integration Router. Existing Stella skills and the previously published Memory UI are reused without replacement.

## Adaptations

User installations use repository-relative skill/module paths rather than an individual's installation layout. The Study Room gets a non-overwriting empty-registry initializer and synthetic Java viewer; private course sources and exercise archives are excluded. Its optional paid model API path now requires the explicit `STELLA_ENABLE_PAID_API=1` opt-in in addition to provider credentials. The Workroom uses a CSS background instead of distributing the original image. Stock import tests use the canonical repository skill. Optional graph providers use `STELLA_CODE_TOOLS_ROOT`; optional integration scripts use `NODE_EXE`/PATH. Windows account-bound locks are preserved.

English README entry points describe execution requirements, costs and limitations. Existing Korean UI/instructions and clearly dated public-data examples remain; this is not a claim of complete English localization. The Workroom animation and stored SCHD example are explicitly identified as demonstrations, not executing agents or live analysis.

## Exclusions and provenance

No actual user memories, accounts/holdings, course documents, source registries, real question banks, research caches, logs, authentication files, session metadata, installed packages, binaries, graph indexes or model weights are included. Migration and verification scripts that require a user's private archives are excluded from the public package. External server source archives are referenced rather than republished; the Agency Agents adaptation license and existing skill provenance are retained. The export contains source copies only; users' original data and private archives are outside its scope.

## Validation boundary

The publication check parsed exported Python and JSON files, ran Node syntax checks, scanned explicit source files for selected credential/private-reference patterns, checked bundled file types and fixed static-asset routes, and verified the final uploaded file hashes against the GitHub tree. Checks do not import or execute the target programs, sign in to providers, launch model requests, install dependencies, or create a real memory store.

Fresh unit/integration tests, browser behavior, Windows DPAPI/launchers, live SEC/DART requests, third-party chart availability, MCP authentication, and CLI/SDK model execution remain unverified in this exported layout. Syntax checks and included test source are not passing runtime tests. Use disposable synthetic data and an appropriately isolated local environment for follow-up execution. No complete security audit or measured whole-task token/cost saving is claimed.

Static results: 30 Python files parsed, 9 JSON files parsed, 13 JavaScript/module files passed Node syntax checking, 6 PowerShell files parsed without errors, and 20 fixed asset routes had existing files. Selected credential/private-reference pattern matches: zero. These results apply to the distributed public source. They do not establish the safety, authentication state, or runtime behavior of any user's installation.
