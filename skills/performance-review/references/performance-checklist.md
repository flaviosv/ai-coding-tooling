# Performance Review Checklist

Generic baseline checklist for reviewing code for performance issues across any technology stack.
Technology-specific checklists extend this file.

---

## Algorithmic Complexity

- [ ] No O(n²) or worse patterns where a better algorithm exists
- [ ] No unnecessary nested loops over large collections
- [ ] No redundant calculations repeated inside loops — precompute where possible
- [ ] Appropriate data structures used for the access pattern (e.g. set/map for lookups, not list scan)

---

## Memory Management

- [ ] No resource leaks — connections, file handles, streams, and buffers are properly closed
- [ ] No unnecessary copying of large data structures
- [ ] Large collections streamed or paginated rather than loaded fully into memory
- [ ] Iterators or lazy sequences used when data is consumed once

---

## Database & Storage

- [ ] No N+1 query patterns — related data fetched in bulk
- [ ] Queries select only the fields needed — not all fields when a subset suffices
- [ ] Pagination or limits applied to all queries that can return unbounded results
- [ ] Indexes exist on columns used in frequent filters, sorts, or joins
- [ ] No expensive queries executed inside loops
- [ ] Connection pooling in use where applicable

---

## I/O & Network

- [ ] Blocking I/O is not on hot synchronous paths where async is possible
- [ ] Timeouts set on all outbound network calls
- [ ] Connections reused where possible — no per-request connection creation
- [ ] No unnecessary file system reads in hot paths
- [ ] External API calls batched or cached where appropriate

---

## Async & Concurrency

- [ ] Heavy or long-running operations deferred to background jobs or queues
- [ ] Bulk operations used instead of per-item loops (e.g. bulk insert/update)
- [ ] Independent operations run in parallel where safe to do so
- [ ] Async code does not block the event loop

---

## Caching & Memoization

- [ ] Repeated expensive computations identified and cached
- [ ] Cache invalidation strategy is correct — no stale data risks
- [ ] Redundant external calls (API, DB) eliminated with appropriate caching

---

## General Principles

1. **Measure before optimising** — profile to confirm the bottleneck before changing anything
2. **Hot path first** — optimise code that runs frequently or handles high-volume requests
3. **Trade-offs** — consider performance vs readability; do not sacrifice clarity without clear gain
4. **Scalability** — prefer stateless design, background processing, and circuit breakers for
   external dependencies
