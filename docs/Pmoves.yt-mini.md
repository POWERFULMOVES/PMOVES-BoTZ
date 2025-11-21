PMOVES.YT Mini Agent - Design Notes

Goal
- Define a lightweight PMOVES-BoTZ-compatible **YT mini** agent – one of the CLI mini agents on the PMOVES-BoTZ team – focused on YouTube/media workflows, with a local-first, Ollama-friendly footprint.

Relationship to PMOVES-BoTZ
- PMOVES.YT is part of the layered PMOVES-BoTZ architecture:
  - **CLI mini agent layer**: A local `yt-mini` CLI that can:
    - Bootstrap the YT service it is responsible for (e.g., prepare a local media index, run a one-shot analysis job).
    - Be invoked directly by users or by orchestration agents (gateway / MCP modes).
  - **Service/overlay layer** in this repo:
    - A small Dockerized service wired as an optional `features/yt` overlay, sitting alongside `features/cipher`, `features/docling`, etc.
  - **Gateway / big-bro agents**:
    - MCP modes in `core/mcp/modes/` can call into the YT mini agent via MCP or HTTP to compose workflows (Docling + Cipher + YT, etc.).
- The primary focus is local media indexing and playlist/channel intelligence; cloud APIs (YouTube Data API, etc.) are layered in after the local/Ollama path is healthy.

Local-First Plan (Ollama)
- Embed PMOVES.YT mini as:
  - A local CLI for playlist and channel snapshots (using `yt-dlp` or Invidious where appropriate).
  - An MCP tool or HTTP endpoint for:
    - "Summarize this channel/playlist"
    - "Suggest the next 3 videos given this history"
  - LLM reasoning provided by the same VL/Ollama stack used by PMOVES-BoTZ (no cloud key required).
- Validation hook in this repo (once `features/yt` exists):
  - Add a dedicated smoke test:
    - Verifies the YT mini container/CLI is callable from the BoTZ stack.
    - Ensures basic commands (e.g., dry-run metadata fetch against a test playlist URL) return structured JSON.

Cloud Layering (Later)
- Once local behavior is stable:
  - Add optional bindings for YouTube Data API keys and any recommended media intelligence APIs.
  - Extend smoke tests to:
    - Check API quota usage endpoints.
    - Validate end-to-end flows (playlist fetch → summary via Cipher/Docling → stored memory in Cipher).

Next Steps
- Stand up the `PMOVES.YT` repo with:
  - Minimal CLI skeleton for "yt-mini" workflows (the mini agent itself).
  - A simple docker-compose snippet suitable for a future `features/yt/docker-compose.yml` overlay in PMOVES-BoTZ.
- Wire initial smoke tests here once the first YT mini container/CLI is available, and link them from `docs/SMOKE_TESTS_AND_STAGING.md` and `docs/PMOVES.AI-Edition-Hardened.md` as another team member in the BoTZ mini-agents layer.
