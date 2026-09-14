# Observability — coding-guidelines insights

Rules for instrumenting code with logging at write time.

---

1. Inject a logger whenever a class performs I/O or has side effects — classes with no I/O rarely need one.

2. Log at the layer closest to the failure. The caller should not need to log what the callee already logged — one log entry per event.

3. Every `catch` block must either: (a) re-raise the exception with added context, or (b) log it at ERROR with message + stack trace + all IDs needed to trace the event. Silent `catch {}` is always wrong.

4. Calibrate log levels precisely — INFO only for business milestones, WARN for recovered anomalies, ERROR only when an operator must act.

5. Write actionable log messages. Include: operation name, outcome, and any IDs needed to reproduce or trace the event. Avoid messages like "failed" or "error occurred" with no context.

6. Use structured logging (key-value fields or JSON) over string interpolation — log aggregators parse fields, not sentences.

7. Never log passwords, tokens, session IDs, or card numbers at any level; redact or hash PII even at DEBUG.

8. Never emit INFO or above inside tight loops or hot paths. Use DEBUG or a counter/metric instead — per-iteration INFO logging at scale is a throughput and storage killer.

9. Propagate a correlation ID (request_id, trace_id) through all layers including async boundaries — without it, logs from the same request cannot be joined in an aggregator.
