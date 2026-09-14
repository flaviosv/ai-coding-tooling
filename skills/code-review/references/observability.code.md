# Observability — code-review insights

Checklist for logging quality during code review.

---

## Logging presence

- [ ] Side-effecting operations (DB writes, external API calls, queue publishes, file I/O) log at DEBUG/INFO on the happy path and ERROR on failure — silent operations are ops blindspots
- [ ] `catch` blocks do not silently swallow exceptions — every caught error is either re-raised with added context OR logged with: message, stack trace, and relevant IDs (user_id, order_id, request_id)
- [ ] Every failed external call logs: what was called, what was sent (sanitized), and what was received

## Log levels

- [ ] Log levels calibrated — ERROR only for operator-actionable failures; no level inflation

## Security & privacy

- [ ] No passwords, tokens, session IDs, card numbers, email addresses, or first/last names in logs at any level; redact or hash other PII even at DEBUG
- [ ] No full request/response bodies at INFO or above when they may carry sensitive data — log metadata (status codes, sizes, IDs) instead

