# Example Flow: Docling → Postman (PMOVES)

1) **Convert & parse docs (Docling)**  
   - Input: OpenAPI file or PDF manual  
   - Tools: `docling.*` → convert → extract endpoints/auth/examples

2) **Generate a collection (Postman)**  
   - Use Postman MCP: create workspace (optional), create collection, add requests from Docling output.

3) **Run tests & validate**  
   - Send requests; compare responses with examples/spec (status, schema).

4) **Report**  
   - Summarize mismatches; post to Slack/Discord via shim or Actions.