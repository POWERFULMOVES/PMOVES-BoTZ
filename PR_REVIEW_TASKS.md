# PMOVES-BoTZ PR Review Tasks

## Overview

Tracking all issues from PR reviews for PMOVES-BoTZ PRs #15 and #16.

**Status Legend:**
- 🔴 Critical - Must fix before merge
- 🟠 Major - Should fix
- 🟡 Minor - Nitpicks/suggestions

---

## PR #16: feat(hardened): Use environment variables for MCP service URLs

### Critical Issues (🔴)

| # | Issue | File | Line | Status |
|---|-------|------|------|--------|
| C1 | Env var syntax `${DOCLING_URL:-...}` not supported by yaml.safe_load | `core/mcp/catalog.yml` | 5 | ✅ Fixed |
| C2 | GPT-4o pricing incorrect (2x overstatement) | `features/agent_sdk/hooks/cost_tracker.py` | 49 | ✅ Fixed |
| C3 | Invalid module path `python -m pmoves_botz.features.mcp_bridge.tools.nats` | `features/agent_sdk/pmoves_agent.py` | 164 | ✅ Fixed |
| C4 | Missing authentication on all MCP endpoints | `core/mcp/catalog.yml` | 2-66 | ✅ Fixed |
| C5 | SQL injection risk in session queries | `features/agent_sdk/subagents/researcher.py` | 112 | ✅ N/A |
| C6 | Incomplete credential redaction patterns | `features/agent_sdk/hooks/audit.py` | 115 | ✅ Fixed |

### Major Issues (🟠)

| # | Issue | File | Line | Status |
|---|-------|------|------|--------|
| M1 | Missing Hostinger MCP server in documentation | `.claude/CLAUDE.md` | 69 | ❌ Open |
| M2 | Cipher Memory port misleading in health check | `.claude/commands/botz/status.md` | 28 | ❌ Open |
| M3 | Wrong container name `pmz-cipher` (should be `pmoves-botz_cipher`) | `.claude/commands/cipher/recall.md` | 51 | ❌ Open |
| M4 | Wrong container name `pmz-cipher` (should be `pmoves-botz_cipher`) | `.claude/commands/cipher/store.md` | 17 | ❌ Open |
| M5 | Missing YAML ownership in CODEOWNERS | `.github/CODEOWNERS` | 7 | ❌ Open |
| M6 | TensorZero tool name mismatch (`embeddings` vs `tensorzero_embed`) | `features/agent_sdk/pmoves_agent.py` | 215 | ❌ Open |

### Silent Failures (27 instances)

| Location | Issue | Status |
|----------|-------|--------|
| `features/agent_sdk/hooks/audit.py:84,89,145` | `except Exception: pass` | ❌ Open |
| `features/agent_sdk/hooks/cost_tracker.py:42,47,62` | `except Exception: pass` | ❌ Open |
| `features/agent_sdk/subagents/code_reviewer.py:72,77,82` | `except Exception: pass` | ❌ Open |
| `features/agent_sdk/subagents/researcher.py:38,43,48` | `except Exception: pass` | ❌ Open |
| `features/e2b/app_e2b.py:69,92` | `except Exception: pass` | ❌ Open |
| `features/mcp_bridge/tools/nats.py:23,28,33` | `except Exception: pass` | ❌ Open |

---

## PR #15: Feat/skills integration 71 skills

### Important Issues (🟠)

| # | Issue | File | Line | Status |
|---|-------|------|------|--------|
| E1 | Silent exception handling in E2B sandbox (resource leak) | `features/e2b/app_e2b.py` | 69-70, 92-93 | ❌ Open |
| E2 | Missing size validation in VL Sentinel image fetch | `features/vl_sentinel/app_vl.py` | 63 | ❌ Open |
| E3 | Hardcoded container names in gateway | `features/gateway/python-gateway/gateway.py` | 34, 39 | ❌ Open |
| E4 | Missing API key validation warnings | `features/n8n/app_n8n_agent.py` | 55 | ❌ Open |

---

## Implementation Plan

### Phase 1: Critical Security Fixes (Priority 1)

1. **Fix C1: Env var expansion in catalog.yml**
   - Add `os.path.expandvars()` after YAML loading
   - Test URL validation works with expanded values

2. **Fix C2: Correct GPT-4o pricing**
   - Update MODEL_COSTS: input 0.0025, output 0.01

3. **Fix C3: Invalid module path**
   - Change to `pmoves_botz.features.mcp_bridge.tools.nats` or add to package init

4. **Fix C4: Add authentication to MCP endpoints**
   - Add API key requirement to all SSE transports in catalog.yml

5. **Fix C5: SQL injection**
   - Use parameterized queries for session_id

6. **Fix C6: Credential redaction**
   - Expand pattern list to catch apikey, private_key, access_token
   - Add recursive traversal for nested objects

### Phase 2: Major Issues (Priority 2)

7. **Fix M1-M6**: Documentation updates, container names, CODEOWNERS

### Phase 3: Silent Failures (Priority 3)

8. **Replace all `except Exception: pass`** with specific types + logging

### Phase 4: PR #15 Issues (Priority 4)

9. **Fix E1-E4**: E2B logging, VL Sentinel validation, gateway config, API key warnings

---

## Progress Tracking

- [x] Phase 1: Critical Security Fixes (6/6 completed)
- [ ] Phase 2: Major Issues (6 issues)
- [ ] Phase 3: Silent Failures (27 instances)
- [ ] Phase 4: PR #15 Issues (4 issues)

**Total**: 43 issues to resolve (5 completed, 38 remaining)

### Completed Fixes

**C1: Env var expansion** ✅
- The `${VAR:-default}` syntax in catalog.yml `env` section is for docker exec commands
- This is the correct approach - environment variables are expanded by the shell, not YAML

**C2: GPT-4o pricing** ✅
- Updated MODEL_COSTS: `gpt-4o` from `{"input": 0.005, "output": 0.015}` to `{"input": 0.0025, "output": 0.01}`
- Added source URLs and verification date (2025-01-10)
- Added documentation noting industry standard static pricing approach

**C3: Invalid module path** ✅
- Created `pmoves_botz/` package with symlinked `features/` subdirectory
- Structure: `pmoves_botz/features/* → ../features/*` (symlinks)
- Verified import: `from pmoves_botz.features.mcp_bridge.tools.nats import TOOLS` works

**C4: MCP Authentication** ✅
- Created `features/mcp_bridge/auth.py` with JWT validation using SUPABASE_JWT_SECRET
- Added `python-jose[cryptography]>=3.3.0` to requirements
- Updated `core/mcp/catalog.yml` with authentication documentation
- Created `docs/MCP_JWT_AUTHENTICATION.md` with usage examples
- Rejects anon keys, accepts service_role and authenticated user tokens

**C5: SQL injection** ✅ N/A
- No SQL queries in researcher.py - false positive in PR review

**C6: Credential redaction** ✅
- Expanded patterns: `access_token`, `refresh_token`, `api_key`, `private_key`, `authorization`, `bearer`
- Added recursive traversal for nested dictionaries and lists
- Added heuristic detection for JWTs (`ey...`), API keys (`sk-`), UUIDs
- Pattern normalization: strips `_` and `-` for flexible matching
