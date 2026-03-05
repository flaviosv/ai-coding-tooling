# LangChain / LangGraph Test Code Review Guide

Supplements `test-review-checklist.md` for projects using LangChain and LangGraph.

Applies to: LangChain 0.3+ / langchain-core 0.3+, LangGraph 0.2+

---

## Test Structure Anti-Patterns

### Live LLM Calls Without Isolation Marker

```python
# Bad — flaky, slow, expensive, non-deterministic; will fail in CI without credentials
def test_summarize_chain():
    chain = create_summarize_chain()
    result = chain.invoke({"text": "Some long text..."})
    assert "summary" in result.content.lower()

# Good — mock the LLM for deterministic, fast, free tests
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage

def test_summarize_chain(fake_llm):
    fake_llm.responses = [AIMessage(content="This is a summary.")]
    chain = create_summarize_chain(llm=fake_llm)
    result = chain.invoke({"text": "Some long text..."})
    assert result.content == "This is a summary."
```

### Asserting on Exact LLM Output Text

Even with fake LLMs, asserting on exact response strings is brittle. Prefer structural assertions.

```python
# Bad — brittle; breaks if fake response wording changes
def test_agent_response(fake_llm):
    result = agent.invoke({"input": "hello"})
    assert result == "Hello! How can I help you today?"

# Good — assert on structure and type
def test_agent_response(fake_llm):
    result = agent.invoke({"input": "hello"})
    assert isinstance(result["messages"][-1], AIMessage)
    assert len(result["messages"]) >= 2
```

### Testing Only Final Output, Ignoring State Transitions

```python
# Bad — only checks the final message, misses whether the graph routed correctly
def test_agent_graph(fake_llm, checkpointer):
    graph = build_graph(llm=fake_llm).compile(checkpointer=checkpointer)
    result = graph.invoke({"messages": [HumanMessage(content="hello")]})
    assert len(result["messages"]) > 1

# Good — also verify intermediate state (tool calls happened, correct node was visited)
from langchain_core.messages import ToolMessage

def test_agent_graph_calls_tool_when_requested(fake_llm, checkpointer):
    graph = build_graph(llm=fake_llm).compile(checkpointer=checkpointer)
    result = graph.invoke(
        {"messages": [HumanMessage(content="what's the weather?")]},
        config={"configurable": {"thread_id": "test-1"}},
    )
    assert any(isinstance(m, ToolMessage) for m in result["messages"])
```

### Missing Tests for Conditional Edge Functions

Conditional edge routing is the control flow of the graph. Every branch must be tested independently.

```python
# Bad — no dedicated tests for the routing function
# (covered implicitly only via full graph integration tests)

# Good — explicit unit tests for every branch of the routing function
from langchain_core.messages import AIMessage

def test_should_continue_routes_to_tools():
    state = {
        "messages": [
            AIMessage(content="", tool_calls=[{"name": "search", "args": {}, "id": "1"}])
        ]
    }
    assert should_continue(state) == "tools"

def test_should_continue_routes_to_end():
    state = {"messages": [AIMessage(content="Final answer.")]}
    assert should_continue(state) == "end"
```

---

## Mocking Patterns

### Use `FakeListChatModel` — Not `unittest.mock.patch` on the LLM

```python
# Bad — patching internals; brittle and bypasses LCEL's invoke contract
with patch("langchain_openai.ChatOpenAI.invoke") as mock_invoke:
    mock_invoke.return_value = AIMessage(content="answer")
    result = chain.invoke({"query": "test"})

# Good — use the official fake; it implements the full Runnable interface
from langchain_core.language_models.fake_chat_models import FakeListChatModel

@pytest.fixture
def fake_llm():
    return FakeListChatModel(
        responses=[
            AIMessage(content='{"action": "search", "query": "test"}'),
            AIMessage(content="Final answer based on search results."),
        ]
    )
```

### Mock Tools, Not the Entire Graph

```python
# Good — test graph routing and state handling with controlled tool behavior
from langchain_core.tools import tool

@pytest.fixture
def mock_search_tool():
    @tool
    def search(query: str) -> str:
        """Search the web for information."""
        return f"Mock result for: {query}"
    return search

def test_graph_uses_search_tool(mock_search_tool, fake_llm, checkpointer):
    graph = build_graph(llm=fake_llm, tools=[mock_search_tool]).compile(checkpointer=checkpointer)
    result = graph.invoke(
        {"messages": [HumanMessage(content="search for X")]},
        config={"configurable": {"thread_id": "tool-test-1"}},
    )
    tool_messages = [m for m in result["messages"] if isinstance(m, ToolMessage)]
    assert len(tool_messages) >= 1
    assert "Mock result for:" in tool_messages[0].content
```

### Mock Retrievers for RAG Chains

```python
from unittest.mock import AsyncMock, MagicMock
from langchain_core.documents import Document

@pytest.fixture
def mock_retriever():
    docs = [Document(page_content="Relevant content", metadata={"source": "test.md"})]
    retriever = MagicMock()
    retriever.invoke.return_value = docs
    retriever.ainvoke = AsyncMock(return_value=docs)
    return retriever

def test_rag_chain_retrieves_documents(mock_retriever, fake_llm):
    chain = build_rag_chain(llm=fake_llm, retriever=mock_retriever)
    chain.invoke({"question": "What is X?"})
    mock_retriever.invoke.assert_called_once()
```

---

## Graph Testing Patterns

### Test Individual Nodes as Pure Functions

```python
from langchain_core.messages import HumanMessage

# Good — unit test a single node function directly
def test_classify_node_routes_billing_queries():
    state = {"messages": [HumanMessage(content="I need a refund")]}
    result = classify_node(state)
    assert result["category"] == "billing"
```

### Test Graph With `update_state` for Partial Execution

```python
from langgraph.checkpoint.memory import MemorySaver

def test_graph_handles_pre_classified_state():
    checkpointer = MemorySaver()
    compiled = build_graph().compile(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "partial-exec-1"}}

    # Inject state as if node "classify" already ran
    compiled.update_state(
        config=config,
        values={"category": "billing"},
        as_node="classify",
    )

    result = compiled.invoke(None, config=config)
    assert result["category"] == "billing"
```

### Test Human-in-the-Loop Interrupt and Resume

```python
from langgraph.types import Command

def test_graph_pauses_at_interrupt_before(checkpointer):
    graph = build_graph().compile(
        checkpointer=checkpointer,
        interrupt_before=["execute_action"],
    )
    config = {"configurable": {"thread_id": "hitl-test-1"}}

    result = graph.invoke(
        {"messages": [HumanMessage(content="perform dangerous action")]},
        config,
    )
    # Graph should have paused — check interrupt is surfaced
    assert "__interrupt__" in result or result.get("pending_action") is not None

def test_graph_resumes_with_command_resume(checkpointer):
    graph = build_graph().compile(
        checkpointer=checkpointer,
        interrupt_before=["execute_action"],
    )
    config = {"configurable": {"thread_id": "hitl-resume-1"}}

    graph.invoke({"messages": [HumanMessage(content="perform action")]}, config)
    result = graph.invoke(Command(resume=True), config)

    assert isinstance(result["messages"][-1], AIMessage)
```

### Test Checkpointed State Accumulation

```python
def test_messages_accumulate_across_graph_invocations(checkpointer):
    graph = build_graph().compile(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "accumulate-1"}}

    graph.invoke({"messages": [HumanMessage(content="First")]}, config)
    result = graph.invoke({"messages": [HumanMessage(content="Second")]}, config)

    human_messages = [m.content for m in result["messages"] if isinstance(m, HumanMessage)]
    assert "First" in human_messages
    assert "Second" in human_messages
```

---

## What to Flag in Review

- [ ] Unit or integration tests calling live LLM APIs without `@pytest.mark.e2e` and a `skipif` guard on the API key environment variable
- [ ] No `FakeListChatModel` (or equivalent fake) in the test suite — all chain/graph tests hit real APIs
- [ ] Graph tests that only assert on final output length or type — no verification of intermediate state, tool call messages, or node traversal
- [ ] No dedicated unit tests for conditional edge routing functions — branches only tested implicitly via full graph runs
- [ ] Assertions on exact LLM response strings — brittle even with deterministic fakes; prefer structural type checks
- [ ] No tests for error paths: what happens when the LLM returns unparseable output, a tool raises, or the graph hits a retry limit
- [ ] State schema changes (new fields, changed reducers) not reflected in test fixtures or state setup
- [ ] Tests using `unittest.mock.patch` on LLM internals instead of `FakeListChatModel`
- [ ] `InMemorySaver` / `MemorySaver` fixture not reset between tests — shared checkpointer state causes test interdependence
- [ ] Human-in-the-loop flows tested without exercising the `Command(resume=...)` path
- [ ] Missing parametrized tests for conditional routing when 3+ branches exist
- [ ] E2E tests mixed into the unit/integration test suite with no marker to exclude from CI
