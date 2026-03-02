# LangChain / LangGraph Performance Best Practices

Applies to: LangChain 0.3+ and LangGraph 0.2+

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

```python
# Good — first token arrives fast, better UX
async for chunk in chain.astream({"query": user_input}):
    yield chunk.content

# Bad — user waits for full response
response = await chain.ainvoke({"query": user_input})
return response.content
```

### Use `astream_events` for Complex Chains

```python
# Good — stream intermediate steps from a graph
async for event in graph.astream_events(inputs, version="v2"):
    if event["event"] == "on_chat_model_stream":
        print(event["data"]["chunk"].content, end="")
```

---

## Caching

### Cache LLM Responses for Repeated Queries

```python
from langchain_core.globals import set_llm_cache
from langchain_community.cache import SQLiteCache

# Good — avoids redundant API calls
set_llm_cache(SQLiteCache(database_path=".langchain_cache.db"))
```

### Cache Embeddings

```python
from langchain.embeddings import CacheBackedEmbeddings
from langchain.storage import LocalFileStore

# Good — embeddings computed once, cached on disk
store = LocalFileStore("./embedding_cache/")
cached_embedder = CacheBackedEmbeddings.from_bytes_store(
    underlying_embeddings=embeddings,
    document_embedding_cache=store,
    namespace=embeddings.model,
)
```

---

## Token Management

### Set Appropriate `max_tokens`

```python
# Good — bounded output, predictable cost
llm = ChatOpenAI(model="gpt-4o", max_tokens=1024)

# Bad — unbounded, risk of excessive token usage
llm = ChatOpenAI(model="gpt-4o")
```

### Use Cheaper Models for Simple Tasks

```python
# Good — route by complexity
from langchain_core.runnables import RunnableParallel

classifier = ChatOpenAI(model="gpt-4o-mini", max_tokens=10)
generator = ChatOpenAI(model="gpt-4o", max_tokens=2048)
```

### Trim Message History

```python
from langchain_core.messages import trim_messages

# Good — prevent context window overflow
trimmed = trim_messages(
    messages,
    max_tokens=4000,
    token_counter=llm.get_num_tokens_from_messages,
    strategy="last",
    include_system=True,
)
```

---

## LangGraph State Performance

### Keep State Minimal

```python
# Good — only essential data in state
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    current_step: str

# Bad — storing large documents in state
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    all_documents: list[Document]  # Bloats checkpoint size
    raw_html: str                  # Unnecessary in state
```

### Use External Storage for Large Data

```python
# Good — store reference, not content
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    document_ids: list[str]  # Fetch from store when needed

def retrieve_node(state: AgentState) -> dict:
    docs = vector_store.get_by_ids(state["document_ids"])
    summary = summarize(docs)
    return {"messages": [AIMessage(content=summary)]}
```

---

## Retrieval Performance

### Use Metadata Filtering Before Similarity Search

```python
# Good — reduce search space first
results = vectorstore.similarity_search(
    query,
    k=5,
    filter={"category": "technical", "year": 2024},
)

# Bad — search everything then filter in Python
results = vectorstore.similarity_search(query, k=100)
results = [r for r in results if r.metadata["category"] == "technical"]
```

### Set Appropriate Chunk Sizes

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Good — balanced chunk size for retrieval quality
splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
)

# Bad — chunks too large (poor retrieval precision) or too small (lost context)
splitter = RecursiveCharacterTextSplitter(chunk_size=5000, chunk_overlap=0)
```
