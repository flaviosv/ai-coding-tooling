# LangChain / LangGraph Performance Best Practices

Applies to: LangChain 0.3+ / langchain-core 0.3+, LangGraph 0.2+

---

## LLM Call Optimization

### Use `RunnableParallel` for Independent Operations

```python
# Good — runs retrieval and classification concurrently
from langchain_core.runnables import RunnableParallel

parallel = RunnableParallel(
    context=retriever,
    classification=classify_chain,
)
result = parallel.invoke({"query": user_input})

# Bad — sequential when operations are independent
context = retriever.invoke({"query": user_input})
classification = classify_chain.invoke({"query": user_input})
```

### Use `batch()` Instead of Looping `invoke()`

```python
# Good — batches requests with concurrency control
results = chain.batch(
    [{"query": q} for q in queries],
    config={"max_concurrency": 5},
)

# Bad — sequential, no concurrency
results = [chain.invoke({"query": q}) for q in queries]
```

### Use `async` for I/O-Bound Workloads

```python
# Good — non-blocking concurrent execution
import asyncio

results = await asyncio.gather(
    chain.ainvoke(input_1),
    chain.ainvoke(input_2),
)

# Bad — blocking sequential calls in an async context
result_1 = chain.invoke(input_1)
result_2 = chain.invoke(input_2)
```

---

## Streaming

### Stream User-Facing Responses

Stream output as tokens arrive rather than waiting for the complete response. This is the single highest-impact latency improvement for interactive applications.

```python
# Good — first token arrives fast, better UX
async for chunk in chain.astream({"query": user_input}):
    yield chunk.content

# Bad — user waits for full response before seeing anything
response = await chain.ainvoke({"query": user_input})
return response.content
```

### Use `astream_events` for Complex Chains and Graphs

```python
# Good — stream intermediate steps with event metadata
async for event in graph.astream_events(inputs, version="v2"):
    if event["event"] == "on_chat_model_stream":
        print(event["data"]["chunk"].content, end="", flush=True)
    elif event["event"] == "on_tool_start":
        print(f"\n[Calling tool: {event['name']}]")
```

### Use `stream_mode` on Graphs

```python
# stream_mode="messages" — stream individual LLM tokens as they are produced
for token, metadata in graph.stream(
    {"messages": [{"role": "user", "content": "What is the weather in SF?"}]},
    stream_mode="messages",
):
    print(token.content, end="", flush=True)

# stream_mode="updates" — receive state diffs after each node completes
for chunk in graph.stream(inputs, stream_mode="updates"):
    for node_name, node_output in chunk.items():
        print(f"[{node_name}] produced update")
```

---

## Caching

### Cache LLM Responses for Repeated Queries

```python
from langchain_core.globals import set_llm_cache
from langchain_community.cache import SQLiteCache

# Good — avoids redundant API calls for identical prompts
set_llm_cache(SQLiteCache(database_path=".langchain_cache.db"))
```

### Cache Embeddings

```python
from langchain.embeddings import CacheBackedEmbeddings
from langchain.storage import LocalFileStore

# Good — embeddings computed once, served from disk on subsequent calls
store = LocalFileStore("./embedding_cache/")
cached_embedder = CacheBackedEmbeddings.from_bytes_store(
    underlying_embeddings=embeddings,
    document_embedding_cache=store,
    namespace=embeddings.model,
)

# Bad — recomputing embeddings on every request
docs = vectorstore.add_documents(documents)  # no cache backing
```

---

## Token Management

### Set Explicit `max_tokens`

```python
# Good — bounded output, predictable cost and latency
from langchain.chat_models import init_chat_model

llm = init_chat_model("gpt-4o", max_tokens=1024)

# Bad — unbounded generation, unpredictable latency and cost
llm = init_chat_model("gpt-4o")
```

### Use Cheaper Models for Simple Tasks

```python
# Good — route by task complexity
from langchain.chat_models import init_chat_model

classifier = init_chat_model("gpt-4o-mini", max_tokens=10)   # cheap, fast
generator = init_chat_model("gpt-4o", max_tokens=2048)       # expensive, capable
```

### Trim Message History Before Sending

```python
from langchain_core.messages import trim_messages

# Good — prevent context window overflow and token waste
trimmed = trim_messages(
    messages,
    max_tokens=4000,
    token_counter=llm.get_num_tokens_from_messages,
    strategy="last",
    include_system=True,
)

# Bad — passing the entire conversation history with no limit
response = llm.invoke(all_messages_ever)
```

---

## LangGraph State Performance

### Keep State Minimal

Large state objects bloat checkpoint size and increase serialization overhead on every node transition.

```python
# Good — only essential references in state
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    current_step: str

# Bad — storing large payloads in state
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    all_documents: list   # Bloats every checkpoint
    raw_html: str         # Should be fetched on demand, not persisted in state
```

### Store References, Not Large Objects

```python
# Good — store IDs, fetch when needed
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    document_ids: list[str]

def retrieve_node(state: AgentState) -> dict:
    docs = vector_store.get_by_ids(state["document_ids"])
    summary = summarize(docs)
    return {"messages": [{"role": "assistant", "content": summary}]}
```

### Use `InMemorySaver` for Testing, Persistent Savers for Production

`InMemorySaver` / `MemorySaver` keep all state in process memory — fine for tests and short-lived sessions. For production, use a persistent saver (Postgres, Redis, SQLite) to avoid unbounded memory growth.

```python
from langgraph.checkpoint.memory import InMemorySaver

# Test / development
memory = InMemorySaver()
app = graph.compile(checkpointer=memory)
```

---

## Retrieval Performance

### Use Metadata Filtering Before Similarity Search

```python
# Good — reduce the search space at the store level
results = vectorstore.similarity_search(
    query,
    k=5,
    filter={"category": "technical", "year": 2024},
)

# Bad — retrieve many results, then filter in Python (data transferred unnecessarily)
results = vectorstore.similarity_search(query, k=100)
filtered = [r for r in results if r.metadata["category"] == "technical"]
```

### Set Appropriate Chunk Sizes

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Good — balanced chunk size for retrieval quality vs. context efficiency
splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
)

# Bad — chunks too large degrade precision; chunks too small lose context
splitter = RecursiveCharacterTextSplitter(chunk_size=5000, chunk_overlap=0)
```

---

## Anti-Patterns

- Calling `invoke()` in a loop instead of `batch()` — eliminates all concurrency benefits
- Streaming disabled for interactive responses — forces the user to wait for full generation
- Unbounded `max_tokens` on expensive models — unpredictable latency and cost spikes
- Full document content stored in LangGraph state — bloats checkpoints on every node transition
- Embeddings recomputed on every request without a `CacheBackedEmbeddings` layer
- Post-retrieval Python filtering instead of vector store metadata filters — defeats index pushdown
- `trim_messages` not applied when conversation history is unbounded — context overflow degrades quality and increases cost
- Synchronous `chain.invoke()` called inside an async request handler — blocks the event loop
