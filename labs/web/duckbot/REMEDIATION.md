# DuckBot Remediation
Do not treat user-controlled content as trusted instructions.

For a real LLM-backed application:
- Keep system/developer instructions separate from untrusted user content.
- Never place long-lived secrets or flags in model-visible prompts.
- Apply strict output filtering and authorization around sensitive operations.
- Treat retrieved documents, tool results, and user content as untrusted data.
- Use explicit allowlists for sensitive actions.
- Add adversarial prompt-injection tests to the application's security test suite.
- Do not rely on the model to enforce access control for secrets.

The primary remediation is architectural: secrets should not be exposed to the model in the first place.
