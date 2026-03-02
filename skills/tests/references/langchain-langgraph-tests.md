# LangChain / LangGraph Testing Guide

Applies to: Projects using LangChain 0.3+ and LangGraph 0.2+ with pytest.

---

## Overview

LangChain and LangGraph applications require a layered testing strategy:

- **Unit tests**: Individual nodes, tools, prompt templates, output parsers — mocked LLM
- **Integration tests**: Full chain/graph execution — mocked LLM, real tools where safe
- **E2E tests**: Live LLM calls — expensive, slow, marked separately

---

## Test Organization

```
tests/
├── unit/
│   ├── test_nodes.py          # Individual graph node functions
│   ├── test_tools.py          # Tool definitions and behavior
│   ├── test_prompts.py        # Prompt template rendering
│   └── test_parsers.py        # Output parser logic
├── integration/
│   ├── test_chains.py         # Full chain execution (mocked LLM)
│   └── test_graphs.py         # Full graph execution (mocked LLM)
├── e2e/
│   └── test_live_llm.py       # Live LLM calls (marked slow/expensive)
└── conftest.py                # Shared fixtures
```

---

## Core Fixtures

### Fake LLM

```python
import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage

@pytest.fixture
def fake_llm():
    """Deterministic LLM that returns pre-defined responses in order."""
    return FakeListChatModel(
        responses=[
            AIMessage(content="Default fake response"),
        ]
    )

def make_fake_llm(*responses: str) -> FakeListChatModel:
    """Helper to create a fake LLM with specific responses."""
    return FakeListChatModel(
        responses=[AIMessage(content=r) for r in responses]
    )
```

### Mock Retriever

```python
from unittest.mock import AsyncMock, MagicMock
from langchain_core.documents import Document

@pytest.fixture
def mock_retriever():
    retriever = MagicMock()
    docs = [
        Document(page_content="Test content", metadata={"source": "test.md"}),
    ]
    retriever.invoke.return_value = docs
    retriever.ainvoke = AsyncMock(return_value=docs)
    return retriever
```

### In-Memory Checkpointer

```python
from langgraph.checkpoint.memory import MemorySaver

@pytest.fixture
def checkpointer():
    return MemorySaver()
```

---

## Unit Testing Patterns

### Testing Prompt Templates

```python
from langchain_core.prompts import ChatPromptTemplate

def test_prompt_renders_with_context():
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a {role}."),
        ("human", "{question}"),
    ])
    messages = prompt.invoke({"role": "assistant", "question": "Hello"})
    assert messages.messages[0].content == "You are a assistant."
    assert messages.messages[1].content == "Hello"
```

### Testing Output Parsers

```python
from langchain_core.output_parsers import JsonOutputParser

def test_json_parser_extracts_fields():
    parser = JsonOutputParser()
    result = parser.invoke('{"name": "Alice", "age": 30}')
    assert result == {"name": "Alice", "age": 30}

def test_json_parser_rejects_invalid_json():
    parser = JsonOutputParser()
    with pytest.raises(Exception):
        parser.invoke("not json")
```

### Testing Tools

```python
from langchain_core.tools import tool

@tool
def calculate(expression: str) -> str:
    """Evaluate a math expression."""
    return str(eval(expression))  # simplified for example

def test_calculate_tool():
    result = calculate.invoke("2 + 3")
    assert result == "5"

def test_calculate_tool_schema():
    schema = calculate.args_schema.model_json_schema()
    assert "expression" in schema["properties"]
```

### Testing Graph Nodes

```python
from langchain_core.messages import HumanMessage

def test_classify_node_returns_category():
    state = {"messages": [HumanMessage(content="I want a refund")]}
    result = classify_node(state)
    assert "category" in result
    assert result["category"] in ("billing", "technical", "general")
```

### Testing Conditional Edges

```python
from langchain_core.messages import AIMessage

def test_route_to_tools_when_tool_calls_present():
    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[{"name": "search", "args": {"q": "test"}, "id": "1"}],
            )
        ]
    }
    assert should_continue(state) == "tools"

def test_route_to_end_when_no_tool_calls():
    state = {"messages": [AIMessage(content="Here is your answer.")]}
    assert should_continue(state) == "end"
```

---

## Integration Testing Patterns

### Testing a Full Chain

```python
def test_rag_chain_produces_answer(fake_llm, mock_retriever):
    chain = build_rag_chain(llm=fake_llm, retriever=mock_retriever)
    result = chain.invoke({"question": "What is X?"})
    assert isinstance(result, str)
    assert len(result) > 0
    mock_retriever.invoke.assert_called_once()
```

### Testing a Full Graph

```python
def test_agent_graph_completes(fake_llm, checkpointer):
    graph = build_agent_graph(llm=fake_llm).compile(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "test-1"}}

    result = graph.invoke(
        {"messages": [HumanMessage(content="hello")]},
        config,
    )

    assert len(result["messages"]) >= 2
    assert isinstance(result["messages"][-1], AIMessage)
```

### Testing Graph State Transitions

```python
def test_graph_visits_expected_nodes(fake_llm):
    visited_nodes = []

    def tracking_callback(node_name):
        def wrapper(state):
            visited_nodes.append(node_name)
            return original_nodes[node_name](state)
        return wrapper

    graph = build_graph_with_tracking(fake_llm, tracking_callback)
    graph.invoke({"messages": [HumanMessage(content="test")]})

    assert "classify" in visited_nodes
    assert "respond" in visited_nodes
```

### Testing Human-in-the-Loop

```python
def test_graph_interrupts_for_approval(fake_llm, checkpointer):
    graph = build_graph(llm=fake_llm).compile(
        checkpointer=checkpointer,
        interrupt_before=["execute_action"],
    )
    config = {"configurable": {"thread_id": "test-hitl"}}

    # First invocation — should pause before execute_action
    result = graph.invoke(
        {"messages": [HumanMessage(content="delete my account")]},
        config,
    )

    # Resume with approval
    result = graph.invoke(
        {"messages": [HumanMessage(content="yes, proceed")]},
        config,
    )
    assert "deleted" in result["messages"][-1].content.lower()
```

---

## E2E Tests (Live LLM)

```python
@pytest.mark.e2e
@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="Live LLM tests require API key",
)
def test_chain_with_live_llm():
    chain = build_chain()  # Uses real LLM
    result = chain.invoke({"question": "What is 2+2?"})
    assert "4" in result
```

Mark these tests so they are excluded from CI by default:

```ini
# pyproject.toml
[tool.pytest.ini_options]
markers = [
    "e2e: live LLM tests (deselect with '-m not e2e')",
]
```

---

## Running Tests

```bash
# All unit + integration tests (no live LLM)
pytest -m "not e2e"

# Only graph tests
pytest tests/integration/test_graphs.py -v

# With coverage
pytest --cov=src --cov-report=term-missing -m "not e2e"

# Run e2e tests (requires API keys)
pytest -m e2e -v
```
