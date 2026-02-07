# TensorZero 2026.1.1 Schema Migration

This document covers the schema migration from TensorZero legacy format to the 2026.1.1 schema used in PMOVES-BoTZ.

---

## Schema Changes Overview

TensorZero 2026.1.1 introduces a restructured configuration format that changes how models, providers, and embedding models are defined.

### Key Structural Differences

| Component | Old Format | New Format |
|-----------|------------|------------|
| Providers | `[[providers.X]]` or `[providers.X]` | `[models.X.providers.Y]` |
| Models | Implicit in provider | `[models.X]` with `routing` array |
| Embeddings | `[functions.embed]` as chat type | `[embedding_models.X]` dedicated section |
| Variants | `type` not always required | `type = "chat_completion"` required |

---

## Migration Examples

### Model and Provider Definition

**Old Format (Pre-2026.1.1):**
```toml
[models.gpt-4o]
routing = ["openai-gpt-4o"]

[providers.openai-gpt-4o]
type = "openai"
model = "gpt-4o"
api_key = "${env.OPENAI_API_KEY}"
```

**New Format (2026.1.1+):**
```toml
[models.orchestrator]
routing = ["ollama"]

[models.orchestrator.providers.ollama]
type = "openai"
api_base = "http://host.docker.internal:11434/v1"
model_name = "nemotron-mini"
api_key_location = "none"
```

Key changes:
- Providers are now nested under `[models.X.providers.Y]` instead of separate `[providers.Y]`
- `model` renamed to `model_name`
- `api_key` replaced with `api_key_location` (values: `none`, `env::VAR_NAME`, `literal::key`)
- `api_base` used for non-standard endpoints (Ollama, vLLM, etc.)

### Embedding Models

**Old Format:**
```toml
[functions.embed]
type = "chat"

[functions.embed.variants.primary]
type = "chat_completion"
model = "text-embedding-ada-002"
```

**New Format (2026.1.1+):**
```toml
[embedding_models.qwen_embed]
routing = ["ollama"]

[embedding_models.qwen_embed.providers.ollama]
type = "openai"
api_base = "http://host.docker.internal:11434/v1"
model_name = "qwen2.5:7b"
api_key_location = "none"
```

Embedding models now have their own dedicated `[embedding_models.X]` section with the same provider nesting pattern as chat models.

### Function Variants

**Old Format:**
```toml
[functions.agent_chat]
type = "chat"
```

**New Format (2026.1.1+):**
```toml
[functions.orchestrator]
type = "chat"

[functions.orchestrator.variants.primary_cloud]
type = "chat_completion"
model = "orchestrator"
weight = 1.0
```

Variants now require:
- Explicit `type = "chat_completion"` declaration
- `model` reference pointing to a `[models.X]` definition
- Optional `weight` for load balancing (defaults to 1.0)

---

## PMOVES-BoTZ Configuration

The current `config/tensorzero.toml` implements the 2026.1.1 schema with the following architecture:

### Primary: Local Ollama (Standalone Mode)

```toml
[models.orchestrator]
routing = ["ollama"]

[models.orchestrator.providers.ollama]
type = "openai"
api_base = "http://host.docker.internal:11434/v1"
model_name = "nemotron-mini"
api_key_location = "none"
```

- Uses `host.docker.internal` for Docker-to-host communication
- `type = "openai"` because Ollama exposes an OpenAI-compatible API at `/v1`
- No API key required for local Ollama

### Optional: OpenRouter Cloud Fallback

```toml
# Uncomment when API key is available:
# [models.orchestrator.providers.openrouter]
# type = "openrouter"
# model_name = "nvidia/nemotron-4-340b-instruct"
# api_key_location = "env::OPENROUTER_API_KEY"
```

To enable cloud fallback, update routing and uncomment the provider:
```toml
[models.orchestrator]
routing = ["ollama", "openrouter"]
```

### Embedding via Qwen 2.5:7b

```toml
[embedding_models.qwen_embed]
routing = ["ollama"]

[embedding_models.qwen_embed.providers.ollama]
type = "openai"
api_base = "http://host.docker.internal:11434/v1"
model_name = "qwen2.5:7b"
api_key_location = "none"
```

Uses local Ollama with Qwen 2.5:7b for embeddings, avoiding external API costs.

---

## Configuration File Location

```
PMOVES-BoTZ/
└── config/
    └── tensorzero.toml    # Active TensorZero configuration
```

---

## API Key Configuration

| Provider | Environment Variable | Required |
|----------|---------------------|----------|
| Ollama (local) | None | No |
| OpenRouter | `OPENROUTER_API_KEY` | Only for cloud fallback |

---

## Validation

After modifying `tensorzero.toml`, validate the configuration:

```bash
# Start TensorZero with new config
docker compose up tensorzero

# Check logs for config errors
docker logs pmz-tensorzero 2>&1 | grep -i error
```

---

## Reference Links

- TensorZero Documentation: https://www.tensorzero.com/docs
- PMOVES-tensorzero Schema Migration PR: https://github.com/POWERFULMOVES/PMOVES-tensorzero/pull/1
- TensorZero Configuration Reference: https://www.tensorzero.com/docs/gateway/configuration

---

## Migration Checklist

- [ ] Update `[providers.X]` to `[models.X.providers.Y]` nesting
- [ ] Rename `model` to `model_name` in provider configs
- [ ] Replace `api_key` with `api_key_location`
- [ ] Move embedding configs to `[embedding_models.X]` section
- [ ] Add `type = "chat_completion"` to all function variants
- [ ] Verify `routing` arrays reference correct provider names
- [ ] Test with local Ollama before enabling cloud fallback
