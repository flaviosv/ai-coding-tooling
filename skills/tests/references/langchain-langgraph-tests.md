# LangChain / LangGraph Testing Guide

Applies to: Projects using LangChain 0.3+ / langchain-core 0.3+ and LangGraph 0.2+ with pytest.

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

## Core Fixtures

### Fake LLM

`FakeListChatModel` returns pre-defined responses in sequence — no network calls, fully deterministic.

```python
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage

@pytest.fixture
def fake_llm():
    """Deterministic LLM that returns pre-defined responses in order."""
    return FakeListChatModel(
        responses=[AIMessage(content="Default fake response")]
    )

def make_fake_llm(*responses: str) -> FakeListChatModel:
    """Create a FakeListChatModel with specific response strings."""
    return FakeListChatModel(
        responses=[AIMessage(content=r) for r in responses]
    )
```

### Fake LLM with Tool Calls

```python
def make_fake_llm_with_tool_call(tool_name: str, args: dict, call_id: str = "call_1") -> FakeListChatModel:
    """Fake LLM that produces a tool call on the first response."""
    return FakeListChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[{"name": tool_name, "args": args, "id": call_id}],
            ),
            AIMessage(content="Final answer after tool use."),
        ]
    )
```

### Mock Retriever

```python
from unittest.mock import AsyncMock, MagicMock
from langchain_core.documents import Document

@pytest.fixture
def mock_retriever():
    docs = [Document(page_content="Test content", metadata={"source": "test.md"})]
    retriever = MagicMock()
    retriever.invoke.return_value = docs
    retriever.ainvoke = AsyncMock(return_value=docs)
    return retriever
```

### In-Memory Checkpointer

```python
from langgraph.checkpoint.memory import InMemorySaver

@pytest.fixture
def checkpointer():
    return InMemorySaver()
```

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

def test_prompt_raises_on_missing_variable():
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a {role}."),
        ("human", "{question}"),
    ])
    with pytest.raises(KeyError):
        prompt.invoke({"role": "assistant"})  # missing "question"
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

### Testing Structured Output Parsing

```python
from pydantic import BaseModel
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage

class ExtractedEntity(BaseModel):
    name: str
    category: str

def test_structured_output_extraction():
    fake_llm = FakeListChatModel(
        responses=[AIMessage(content='{"name": "ACME Corp", "category": "company"}')]
    )
    chain = fake_llm.with_structured_output(ExtractedEntity)
    result = chain.invoke("Extract: ACME Corp is a company.")
    assert result.name == "ACME Corp"
    assert result.category == "company"
```

### Testing Tools

```python
from langchain_core.tools import tool

@tool
def add_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b

def test_add_numbers_tool_returns_correct_sum():
    result = add_numbers.invoke({"a": 3, "b": 7})
    assert result == 10

def test_add_numbers_tool_schema():
    schema = add_numbers.args_schema.model_json_schema()
    assert "a" in schema["properties"]
    assert "b" in schema["properties"]

def test_tool_rejects_invalid_input_type():
    with pytest.raises(Exception):
        add_numbers.invoke({"a": "three", "b": 7})
```

### Testing Graph Nodes

Test node functions as ordinary Python functions — pass in a state dict, assert the returned dict.

```python
from langchain_core.messages import HumanMessage

def test_classify_node_returns_valid_category():
    state = {"messages": [HumanMessage(content="I want a refund")]}
    result = classify_node(state)
    assert "category" in result
    assert result["category"] in ("billing", "technical", "general")

def test_classify_node_handles_empty_messages():
    state = {"messages": []}
    result = classify_node(state)
    assert result["category"] == "general"  # default / fallback
```

### Testing Conditional Edge Functions

```python
from langchain_core.messages import AIMessage

def test_should_continue_routes_to_tools_when_tool_calls_present():
    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[{"name": "search", "args": {"q": "test"}, "id": "1"}],
            )
        ]
    }
    assert should_continue(state) == "tools"

def test_should_continue_routes_to_end_when_no_tool_calls():
    state = {"messages": [AIMessage(content="Here is your answer.")]}
    assert should_continue(state) == "end"
```

## Integration Testing Patterns

### Testing a Full LCEL Chain

```python
def test_rag_chain_produces_non_empty_answer(fake_llm, mock_retriever):
    chain = build_rag_chain(llm=fake_llm, retriever=mock_retriever)
    result = chain.invoke({"question": "What is X?"})
    assert isinstance(result, str)
    assert len(result) > 0
    mock_retriever.invoke.assert_called_once()
```

### Testing a Full Graph

```python
from langchain_core.messages import HumanMessage, AIMessage

def test_agent_graph_completes_and_returns_ai_message(fake_llm, checkpointer):
    graph = build_agent_graph(llm=fake_llm).compile(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "test-1"}}
    result = graph.invoke(
        {"messages": [HumanMessage(content="hello")]},
        config,
    )
    assert len(result["messages"]) >= 2
    assert isinstance(result["messages"][-1], AIMessage)
```

### Testing Graph State Transitions with `update_state`

`update_state` lets you inject state mid-graph to test partial execution paths.

```python
from langgraph.checkpoint.memory import MemorySaver

def test_partial_execution_from_classify_node():
    checkpointer = MemorySaver()
    compiled = build_graph().compile(checkpointer=checkpointer)
    # Simulate state as if "parse_input" node already ran
    compiled.update_state(
        config={"configurable": {"thread_id": "partial-1"}},
        values={"messages": [HumanMessage(content="billing issue")], "category": "billing"},
        as_node="parse_input",
    )
    # Resume from "classify" onward
    result = compiled.invoke(
        None,
        config={"configurable": {"thread_id": "partial-1"}},
    )
    assert result["category"] == "billing"
```

### Testing Human-in-the-Loop Interrupts

```python
from langgraph.types import Command

def test_graph_interrupts_before_destructive_action(checkpointer):
    graph = build_graph().compile(
        checkpointer=checkpointer,
        interrupt_before=["execute_action"],
    )
    config = {"configurable": {"thread_id": "hitl-1"}}
    result = graph.invoke(
        {"messages": [HumanMessage(content="delete my account")]},
        config,
    )
    assert result.get("__interrupt__") is not None or \
           "execute_action" not in [m.name for m in result["messages"] if hasattr(m, "name")]

def test_graph_resumes_after_approval(checkpointer):
    graph = build_graph().compile(
        checkpointer=checkpointer,
        interrupt_before=["execute_action"],
    )
    config = {"configurable": {"thread_id": "hitl-2"}}
    graph.invoke({"messages": [HumanMessage(content="delete my account")]}, config)
    # Resume with human approval
    result = graph.invoke(Command(resume=True), config)
    assert isinstance(result["messages"][-1], AIMessage)
```

### Testing Checkpointed State Persistence

```python
def test_graph_accumulates_messages_across_invocations(checkpointer):
    graph = build_graph().compile(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "persist-1"}}
    graph.invoke({"messages": [HumanMessage(content="First message")]}, config)
    result = graph.invoke({"messages": [HumanMessage(content="Second message")]}, config)
    all_human_messages = [
        m.content for m in result["messages"] if isinstance(m, HumanMessage)
    ]
    assert "First message" in all_human_messages
    assert "Second message" in all_human_messages
```

## E2E Tests (Live LLM)

```python
import os
import pytest

@pytest.mark.e2e
@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="Live LLM tests require OPENAI_API_KEY",
)
def test_chain_with_live_llm():
    chain = build_chain()  # Uses real LLM — no fake
    result = chain.invoke({"question": "What is 2+2?"})
    assert "4" in result
```

Mark these tests so they are excluded from CI by default:

```ini
# pyproject.toml
[tool.pytest.ini_options]
markers = [
    "e2e: live LLM tests, require API keys (deselect with '-m not e2e')",
]
```

## Parametrize Patterns

```python
@pytest.mark.parametrize("input_text,expected_category", [
    ("I need a refund", "billing"),
    ("My account is locked", "account"),
    ("How do I use the API?", "technical"),
    ("", "general"),
])
def test_classify_node_covers_all_intents(input_text, expected_category):
    state = {"messages": [HumanMessage(content=input_text)]}
    result = classify_node(state)
    assert result["category"] == expected_category
```

## Running Tests

```bash
# All unit + integration tests (no live LLM)
pytest -m "not e2e"

# Only graph integration tests
pytest tests/integration/test_graphs.py -v

# With coverage
pytest --cov=src --cov-report=term-missing -m "not e2e"

# Run e2e tests (requires API keys set in environment)
pytest -m e2e -v
```
