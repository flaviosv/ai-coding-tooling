# LangChain / LangGraph Code Review Checklist

Supplements the generic `review-checklist.md` for projects using LangChain and LangGraph.

Applies to: LangChain 0.3+ / langchain-core 0.3+, LangGraph 0.2+

---

## Security

- [ ] API keys and secrets loaded from environment variables — never hardcoded in chain definitions
- [ ] No user input passed directly into system prompt strings via f-strings, `.format()`, or `%` formatting (prompt injection risk)
- [ ] User input routed exclusively through `("human", "{variable}")` placeholders in `ChatPromptTemplate.from_messages()`
- [ ] `allow_dangerous_requests=True` not set unless explicitly justified and reviewed
- [ ] `PythonREPLTool`, `ShellTool`, and `BashProcess` not present in any code path — use purpose-built tools
- [ ] All tool `args_schema` defined as Pydantic models — no unvalidated free-form string inputs
- [ ] Tool implementations validate inputs independently — no assumption that LLM-supplied values are safe
- [ ] File-access tools validate paths against an allowlisted directory (path traversal prevention)
- [ ] Sensitive data (PII, credentials, internal system details) not included in prompts, state, or LangSmith traces
- [ ] `LANGCHAIN_HIDE_INPUTS` / `LANGCHAIN_HIDE_OUTPUTS` configured for production workflows with sensitive data

### LLM Output Handling

- [ ] LLM outputs validated before being used in downstream logic (parsed JSON, tool calls, routing decisions)
- [ ] `with_structured_output()` used with a Pydantic model for structured responses — not manual JSON parsing
- [ ] `OutputFixingParser` or `RetryWithErrorOutputParser` in place where parse failures would break the workflow
- [ ] No `eval()` or `exec()` on LLM-generated content anywhere in the call chain

### RAG / Retrieval Security

- [ ] Vector store retrieval filtered by user/tenant permissions at the store level — not post-retrieval in Python
- [ ] Ingested document content treated as untrusted — not blindly injected into system prompts
- [ ] Access control not delegated to the LLM ("only show the user documents they can see" in a prompt is not a control)

---

## Architecture & Design

- [ ] Chains composed using LCEL — not legacy `LLMChain`, `SequentialChain`, or `SimpleSequentialChain`
- [ ] Runnables used as the primary abstraction (`RunnableSequence`, `RunnableParallel`, `RunnableLambda`, `RunnablePassthrough`)
- [ ] Graph state schema defined as `TypedDict` (with `Annotated` reducers) or a Pydantic model — not a raw `dict`
- [ ] `add_messages` or `operator.add` reducer used for message accumulation fields
- [ ] Graph nodes are pure functions or thin wrappers — business logic not embedded in graph definition files
- [ ] Conditional edges use clearly named functions — not inline lambdas with branching logic
- [ ] `END` (or `END` from `langgraph.graph`) explicitly referenced as a terminal node — no implicit termination
- [ ] `START` used as the graph entry edge — not `add_edge` to a hardcoded first-node name as sole entry
- [ ] Checkpointing configured (`InMemorySaver` for tests, persistent saver for production) when state must survive between invocations
- [ ] `RetryPolicy` applied on nodes that call external APIs or LLMs — not bare try/except inside nodes

### Separation of Concerns

- [ ] Prompt templates defined separately from chain/graph logic (dedicated modules or constants)
- [ ] Tool definitions isolated from graph construction — tools are independently testable and reusable
- [ ] LLM model configuration (model name, temperature, `max_tokens`, `request_timeout`) externalized — not hardcoded in chain or graph files
- [ ] Retriever/vector store construction separated from chain composition
- [ ] State schema (`state.py`) lives in a separate module from graph construction (`graph.py`) and node logic (`nodes.py`)

---

## Error Handling

- [ ] `with_retry()` applied on LLM calls to handle transient API errors — `stop_after_attempt` explicitly set
- [ ] `with_fallbacks()` configured for critical chains (e.g. fallback to a cheaper or different model)
- [ ] Graph nodes handle `OutputParserException` explicitly — not silently corrupting state on parse failure
- [ ] Rate limit errors from LLM providers handled with backoff — not caught with a bare `except:` clause
- [ ] `request_timeout` configured on LLM clients — no unbounded blocking calls
- [ ] `RetryPolicy` used on `add_node()` for nodes with transient failures — not hand-rolled retry loops inside node bodies

```python
# Good — declarative retry at graph level
workflow.add_node(
    "search_documentation",
    search_documentation,
    retry_policy=RetryPolicy(max_attempts=3),
)

# Bad — error-prone manual retry inside a node
def search_documentation(state):
    for attempt in range(3):
        try:
            return {"results": searcher.search(state["query"])}
        except Exception:
            pass
```

---

## Performance

- [ ] `RunnableParallel` used for independent operations — not sequential calls that could run concurrently
- [ ] `batch()` used when processing multiple inputs — not a `for` loop calling `invoke()` per item
- [ ] `max_concurrency` set on `batch()` to prevent overwhelming LLM provider rate limits
- [ ] Streaming (`stream()` / `astream()` / `astream_events()`) used for user-facing responses — not blocking `invoke()` returning the full response
- [ ] `stream_mode="messages"` or `stream_mode="updates"` used appropriately for agent/graph streaming
- [ ] Embedding computations cached (`CacheBackedEmbeddings`) — not recomputed on every request
- [ ] `max_tokens` explicitly set on all LLM instances — no unbounded generation
- [ ] Token usage tracked — no silent runaway context windows
- [ ] State objects contain only references (IDs, keys) for large data — not full documents or raw HTML blobs

---

## LangGraph-Specific

### State Management

- [ ] State reducers defined for all fields that accumulate values — `operator.add` for lists, `add_messages` for message histories
- [ ] Nodes return partial state dicts — not full state replacements (only changed keys)
- [ ] No mutable default values in state schema — `Annotated` + `field(default_factory=...)` pattern used
- [ ] State fields documented — each field has a clear purpose; no orphaned keys
- [ ] Sensitive data not stored in checkpointed state — checkpoints serialize to persistent storage

### Graph Structure

- [ ] No cycles without a termination condition — all loops have a guarded exit via conditional edges
- [ ] `interrupt` / `interrupt_before` / `interrupt_after` used for human-in-the-loop steps — not polling or `sleep`
- [ ] Human input resumed via `Command(resume=...)` — not by re-invoking with a new initial state
- [ ] Subgraphs used for complex multi-step logic — single monolithic graph avoided when node count exceeds ~10
- [ ] Graph structure verified via `graph.get_graph().draw_mermaid()` and reviewed for unexpected paths

```python
# Good — typed state with reducer and correct imports
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import START, END, StateGraph
from langgraph.graph.message import add_messages

class State(TypedDict):
    messages: Annotated[list, add_messages]
    current_step: str

# Bad — raw dict state, no reducers, no typing
state = {"messages": [], "step": "start"}
```

---

## Observability

- [ ] LangSmith tracing enabled in non-trivial production applications (`LANGCHAIN_TRACING_V2=true`)
- [ ] Custom run names set on chains/graphs for navigable trace trees (`with_config({"run_name": "..."})`)
- [ ] Token usage and latency visible in traces
- [ ] Callbacks used exclusively for logging, tracing, and monitoring — never for business logic
- [ ] LangSmith API key (`LANGCHAIN_API_KEY`) not logged, printed, or included in error reports

---

## Anti-Patterns

- [ ] `LLMChain`, `SequentialChain`, `ConversationChain` — superseded by LCEL; flag any usage
- [ ] `AgentExecutor` with legacy `initialize_agent()` — superseded by LangGraph; flag for migration
- [ ] `MemoryBuffer` / `ConversationBufferMemory` from `langchain.memory` — superseded by LangGraph checkpointing and `add_messages` reducer
- [ ] Tool definitions without `args_schema` Pydantic models — free-form string inputs bypass type safety
- [ ] Calling `chain.run()` instead of `chain.invoke()` — `.run()` is deprecated
- [ ] Direct `openai` client usage inside LangChain/LangGraph code — bypasses tracing, retry, and fallback integration
