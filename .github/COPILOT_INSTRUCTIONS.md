Project: VCC-Covina (Compliance & Automation)
Language: Python (FastAPI) + Frontend

Purpose:
- GDPR-compliant document management, workflows and AI-assisted analysis.

What Copilot should help with:
- Implement backend endpoints, document processing pipelines and safe LLM integrations.
- Ensure privacy-preserving defaults and data minimization in code suggestions.

Coding style and constraints:
- Use secure defaults: encryption at rest, opt-in logging, and least-privilege access patterns.
- All changes touching data handling must update `docs/privacy.md` and `docs/data-flow.md`.

Documentation duties (./docs):
- Maintain `docs/compliance.md` with reference to legal/organizational controls and proof points.
- Document workflow steps and acceptance criteria for automated processes.

Todo.md continuation:
- Add granular todos (owner, acceptance criteria) and keep `todo.md` near top-level for tracking.

Examples for Copilot prompts:
- "Create an API to upload a document, extract metadata, and store sanitized text for analysis."
- "Add unit tests that verify PII redaction for the document parser."

Testing & CI:
- Add security-focused tests, contract tests for document schemas, and run static analysis in CI.
