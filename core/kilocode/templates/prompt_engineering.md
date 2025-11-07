# PMOVES Prompt Engineering Cheatsheet

- Define the **goal** and **constraints** explicitly.
- State goal, input data, constraints, and required **output format** (JSON/Markdown/tables/cURL).
- Provide **source context** (doc URLs, files) and expected **output format**.
- Ask for **assumptions** and **unknowns** before execution.
- For API tasks: request **auth scheme**, **required params**, **rate limits**.
- Prefer **tool-using plans** (Docling → Postman → E2B → VL Sentinel as available in your configuration).
- Use **chain-of-verification**: extract → draft → verify → finalize.