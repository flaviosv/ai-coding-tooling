# Performance Review Checklist

Generic baseline checklist for reviewing code for performance issues across any technology stack.
Technology-specific checklists extend this file.

---

## Algorithmic Complexity

- [ ] No O(n²) or worse patterns where a better algorithm exists
- [ ] No unnecessary nested loops over large collections
- [ ] No redundant calculations repeated inside loops — precompute where possible
- [ ] Appropriate data structures used for the access pattern (e.g. set/map for lookups, not list scan)
- [ ] String concatenation inside loops replaced with a buffer or join approach — repeated concatenation causes repeated allocations

## Memory Management

- [ ] No resource leaks — connections, file handles, streams, and buffers are properly closed
- [ ] No unnecessary copying of large data structures
- [ ] Large collections streamed or paginated rather than loaded fully into memory
- [ ] Iterators or lazy sequences used when data is consumed once
- [ ] Expensive objects or resources initialized lazily rather than eagerly on every request — defer construction until first use
- [ ] Reusable buffers or object pools used in hot paths rather than allocating fresh instances per request

## Database & Storage

- [ ] No N+1 query patterns — related data fetched in bulk
- [ ] Queries select only the fields needed — not all fields when a subset suffices
- [ ] Pagination or limits applied to all queries that can return unbounded results
- [ ] Indexes exist on columns used in frequent filters, sorts, or joins
- [ ] No expensive queries executed inside loops
- [ ] Connection pooling in use where applicable
- [ ] Existence and count checks performed at the data layer — not by fetching all records into memory
- [ ] Filtering, sorting, and aggregation pushed to the data layer — not performed in application code after loading a full result set

## I/O & Network

- [ ] Blocking I/O is not on hot synchronous paths where async is possible
- [ ] Timeouts set on all outbound network calls
- [ ] Connections reused where possible — no per-request connection creation
- [ ] No unnecessary file system reads in hot paths
- [ ] External API calls batched or cached where appropriate
- [ ] Request cancellation signals propagated to all downstream I/O calls — downstream work does not outlive a cancelled or disconnected client
- [ ] Inbound request and payload sizes bounded to prevent unbounded memory consumption under load

## Async & Concurrency

- [ ] Heavy or long-running operations deferred to background jobs or queues
- [ ] Bulk operations used instead of per-item loops (e.g. bulk insert/update)
- [ ] Independent operations run in parallel where safe to do so
- [ ] Async code does not block the event loop

## Caching & Memoization

- [ ] Repeated expensive computations identified and cached
- [ ] Cache invalidation strategy is correct — no stale data risks
- [ ] Redundant external calls (API, DB) eliminated with appropriate caching
- [ ] Cached values are minimal representations (IDs, summaries) rather than large raw objects — oversized cache entries waste memory and increase serialization overhead

## Serialization & Data Transfer

- [ ] Serialization avoids reflection-heavy generic maps on hot paths where the stack makes that costly
- [ ] Only the fields required by the consumer are included in serialized payloads — no wildcard or select-all patterns when a subset suffices
- [ ] Large payloads streamed incrementally rather than buffered fully in memory before sending

## Profiling & Measurement

- [ ] Profiling endpoints or debug tools are not exposed on public-facing interfaces in production
