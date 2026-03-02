# LangChain / LangGraph Code Review Checklist

Supplements the generic `review-checklist.md` for projects using LangChain and LangGraph.

---

## Security

- [ ] API keys and secrets loaded from environment variables — never hardcoded in chain definitions
- [ ] No user input passed directly into prompt templates without sanitization (prompt injection risk)
- [ ] `allow_dangerous_requests=True` not set unless explicitly justified and reviewed
- [ ] Tool definitions do not expose shell access, file system writes, or database mutations without authorization checks
- [ ] `PythonREPLTool` or `ShellTool` not used in production — use purpose-built tools instead
- [ ] Sensitive data (PII, credentials) not included in chain/graph state that gets logged or traced

### LLM Output Handling

- [ ] LLM outputs validated before being used in downstream logic (e.g. parsed JSON, tool calls)
- [ ] Output parsers have fallback handling — `OutputFixingParser` or `RetryWithErrorOutputParser` used where appropriate
- [ ] No `eval()` or `exec()` on LLM-generated content

---

## Architecture & Design

- [ ] Chains composed using LCEL (LangChain Expression Language) — not legacy `LLMChain` / `SequentialChain`
- [ ] Runnables used as the primary abstraction (`RunnableSequence`, `RunnableParallel`, `RunnableLambda`)
- [ ] Graph state schema defined as a `TypedDict` or Pydantic model — not a raw dict
- [ ] Graph nodes are pure functions or thin wrappers — business logic not embedded in graph definition
- [ ] Conditional edges use clearly named functions — not inline lambdas with complex logic
- [ ] `END` node explicitly defined — no implicit graph termination
- [ ] Checkpointing configured for graphs that need human-in-the-loop or retry semantics

### Separation of Concerns

- [ ] Prompt templates defined separately from chain/graph logic (in dedicated files or constants)
- [ ] Tool definitions isolated from graph construction — tools are reusable across graphs
- [ ] LLM model configuration (model name, temperature, max tokens) externalized — not hardcoded in chain definitions
- [ ] Retriever logic separated from chain composition

---

## Error Handling

- [ ] `with_retry()` used on LLM calls to handle transient API errors
- [ ] `with_fallbacks()` configured for critical chains (e.g. fallback to a cheaper model)
- [ ] Graph nodes handle exceptions gracefully — errors don't silently corrupt state
- [ ] Rate limit errors from LLM providers handled with backoff — not bare `except`
- [ ] Timeout configured on LLM calls (`request_timeout` parameter)

---

## Performance

- [ ] `RunnableParallel` used for independent operations — not sequential calls that could be parallel
- [ ] `batch()` used when processing multiple inputs — not a loop of `invoke()` calls
- [ ] Streaming (`stream()` / `astream()`) used for user-facing responses where latency matters
- [ ] Embedding computations cached — not recomputed on every request
- [ ] `max_concurrency` set on batch operations to avoid overwhelming LLM provider rate limits
- [ ] Token usage tracked and logged — no unbounded `max_tokens` on expensive models

---

## LangGraph-Specific

### State Management

- [ ] State reducers defined for fields that accumulate values (e.g. `operator.add` for message lists)
- [ ] State updates are additive — nodes return partial state dicts, not full state replacements
- [ ] No mutable default values in state schema (use `field(default_factory=...)`)
- [ ] State schema documented — all fields have clear purpose

### Graph Structure

- [ ] No cycles without a termination condition — infinite loops are guarded
- [ ] `interrupt_before` or `interrupt_after` used for human-in-the-loop steps — not polling
- [ ] Subgraphs used for complex workflows — single monolithic graph avoided when > 8-10 nodes
- [ ] Graph visualization (`graph.get_graph().draw_mermaid()`) reviewed for correctness

---

## Observability

- [ ] LangSmith tracing enabled in non-trivial applications (`LANGCHAIN_TRACING_V2=true`)
- [ ] Custom run names set on chains/graphs for easier trace navigation (`with_config({"run_name": "..."})`)
- [ ] Token usage and latency visible in traces
- [ ] Callbacks not used for business logic — only for logging, tracing, and monitoring
