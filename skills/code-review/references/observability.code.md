# Observability — code-review insights

Checklist for logging quality during code review.

---

## Logging presence

- [ ] Side-effecting operations (DB writes, external API calls, queue publishes, file I/O) log at DEBUG/INFO on the happy path and ERROR on failure — silent operations are ops blindspots
- [ ] `catch` blocks do not silently swallow exceptions — every caught error is either re-raised with added context OR logged with: message, stack trace, and relevant IDs (user_id, order_id, request_id)
- [ ] Every failed external call logs: what was called, what was sent (sanitized), and what was received

## Log level calibration

- [ ] `DEBUG` — internal flow, state snapshots, diagnostic detail; off by default in production
- [ ] `INFO` — business milestones (order placed, payment confirmed, user registered); not every function entry/exit
- [ ] `WARN` — recoverable unexpected conditions (retry triggered, fallback used, deprecated path hit)
- [ ] `ERROR` — unrecoverable failures requiring operator attention; not for expected validation failures
- [ ] Flag: everything logged at INFO or ERROR regardless of severity — level inflation destroys signal-to-noise ratio

## Log message quality

- [ ] Messages are actionable: they name the operation, the failure mode, and include correlation IDs — `"Payment authorization failed: order_id=123 provider=stripe reason=card_declined"` not `"Payment failed"`
- [ ] Structured fields or consistent templates used — no free-form string concatenation that breaks log aggregation/parsing
- [ ] Same event not logged twice (once in callee, once in caller) — pick the layer closest to the failure

## Security & privacy

- [ ] No PII, passwords, tokens, card numbers, or session identifiers in logs at INFO or above — DEBUG-level PII is acceptable for development diagnostics
- [ ] No full request/response bodies at INFO or above when they may carry sensitive data — log metadata (status codes, sizes, IDs) instead

## Performance

- [ ] No INFO/WARN/ERROR log calls inside tight loops or high-frequency hot paths — use DEBUG or sample
- [ ] Correlation ID / trace ID propagated through async boundaries (thread pools, queue consumers, background jobs)

## Duplication

- [ ] Not re-logging what framework middleware already captures (e.g. every HTTP request when the framework logs them centrally)
