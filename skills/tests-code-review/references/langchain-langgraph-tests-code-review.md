# LangChain / LangGraph Test Code Review Guide

Supplements `test-review-checklist.md` for projects using LangChain and LangGraph.

---

## Test Structure Anti-Patterns

### ❌ Testing Against Live LLMs Without Mocking

```python
# Bad — flaky, slow, expensive, non-deterministic
def test_summarize_chain():
    chain = create_summarize_chain()
    result = chain.invoke({"text": "Some long text..."})
    assert "summary" in result.content.lower()

# Good — mock the LLM for deterministic tests
def test_summarize_chain(mock_llm):
    mock_llm.responses = [AIMessage(content="This is a summary.")]
    chain = create_summarize_chain(llm=mock_llm)
    result = chain.invoke({"text": "Some long text..."})
    assert result.content == "This is a summary."
```

### ❌ No Assertion on Chain Structure

```python
# Bad — only tests happy path output, not composition
def test_chain():
    result = my_chain.invoke({"query": "test"})
    assert result is not None

# Good — verify the chain is composed correctly
def test_chain_structure():
    assert hasattr(my_chain, "first")  # RunnableSequence
    assert isinstance(my_chain.first, ChatPromptTemplate)
```

### ❌ Testing Graph Without Verifying State Transitions

```python
# Bad — only checks final output
def test_agent_graph():
    result = graph.invoke({"messages": [HumanMessage(content="hello")]})
    assert len(result["messages"]) > 1

# Good — verify intermediate state and node traversal
def test_agent_graph_routes_to_tool_node():
    result = graph.invoke(
        {"messages": [HumanMessage(content="what's the weather?")]},
        config={"configurable": {"thread_id": "test-1"}},
    )
    # Verify the tool node was visited
    assert any(isinstance(m, ToolMessage) for m in result["messages"])
```

---

## Mocking Patterns

### Use `FakeListLLM` or `FakeListChatModel` for Unit Tests

```python
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage

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
# Good — test graph logic with controlled tool behavior
@pytest.fixture
def mock_search_tool():
    @tool
    def search(query: str) -> str:
        """Search for information."""
        return f"Mock result for: {query}"
    return search

def test_graph_with_mock_tool(mock_search_tool, fake_llm):
    graph = build_graph(llm=fake_llm, tools=[mock_search_tool])
    result = graph.invoke({"messages": [HumanMessage(content="search for X")]})
    assert "Mock result for:" in result["messages"][-2].content
```

### Mock Retrievers for RAG Chains

```python
@pytest.fixture
def mock_retriever():
    docs = [
        Document(page_content="Relevant content", metadata={"source": "test.md"}),
    ]
    retriever = MagicMock()
    retriever.invoke.return_value = docs
    retriever.ainvoke = AsyncMock(return_value=docs)
    return retriever
```

---

## Graph Testing Patterns

### Test Individual Nodes in Isolation

```python
# Good — unit test a single node function
def test_classify_node():
    state = {"messages": [HumanMessage(content="I need help with billing")]}
    result = classify_node(state)
    assert result["category"] == "billing"
```

### Test Conditional Edges

```python
# Good — verify routing logic independently
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

### Test Graph With Checkpointing

```python
from langgraph.checkpoint.memory import MemorySaver

def test_graph_resumes_from_checkpoint():
    checkpointer = MemorySaver()
    graph = build_graph().compile(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "test-resume"}}

    # First invocation — interrupted
    graph.invoke({"messages": [HumanMessage(content="start")]}, config)

    # Resume with new input
    result = graph.invoke({"messages": [HumanMessage(content="continue")]}, config)
    assert len(result["messages"]) > 2  # Includes history
```

---

## What to Flag in Review

- [ ] Tests that call live LLM APIs without clear `@pytest.mark.integration` marker
- [ ] No mock/fake LLM fixtures in the test suite
- [ ] Graph tests that only check final output — not intermediate state or node traversal
- [ ] Missing tests for conditional edge routing functions
- [ ] Tests that assert on exact LLM output text (brittle even with mocks — prefer structural assertions)
- [ ] No tests for error/retry paths (e.g. what happens when the LLM returns unparseable output)
- [ ] State schema changes not reflected in test fixtures
- [ ] Callback/tracing tests that depend on side effects rather than explicit assertions
