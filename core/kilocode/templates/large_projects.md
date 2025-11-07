# PMOVES Large Project Playbook

- Split work into **scopes** (docs parsing, endpoints setup, tests).
- Break down into **modes** (Docling/Executor/Runner/Sentinel as appropriate for your configuration).
- Cache persistent context (model/provider prompt caching if available).
- Maintain a **task ledger** (what's done, what's next, blockers).
- Keep checkpoint artifacts after each phase.
- Cache partial results; verify with appropriate tools (VL Sentinel if available) before finalizing.
- Produce **artifacts** (collections, reports) after each phase.