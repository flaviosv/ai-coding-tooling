# LangChain / LangGraph Coding Style Guide

## Chain Composition

- Use LCEL (LangChain Expression Language) for all chain composition — never legacy `LLMChain`, `SequentialChain`, or `SimpleSequentialChain`
- Compose with the pipe operator `|` for readability: `prompt | llm | parser`
- Extract reusable sub-chains into named variables — avoid deeply nested inline pipes
- Use `RunnablePassthrough.assign()` to add computed fields to the chain context
- Prefer `RunnableLambda` over raw lambdas for named, debuggable steps

```python
# Good — clear, composable LCEL
retrieval_chain = (
    RunnablePassthrough.assign(context=retriever | format_docs)
    | prompt
    | llm
    | StrOutputParser()
)

# Bad — legacy API
chain = LLMChain(llm=llm, prompt=prompt)
```

## Prompt Management

- Define prompts in dedicated modules or constants — not inline in chain definitions
- Use `ChatPromptTemplate.from_messages()` for chat models — not raw string templates
- Include clear system messages that define role, constraints, and output format
- Use input variables consistently — document expected keys in the prompt module
- Never interpolate user input directly into system prompts — use `("human", "{user_input}")` placeholders

```python
# Good — separated, typed
CLASSIFY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Classify the user message into one of: {categories}"),
    ("human", "{message}"),
])

# Bad — inline, untyped
chain = prompt_from_string("Classify this: {message}") | llm
```

## LangGraph State Design

- Define state as `TypedDict` with `Annotated` fields for reducers — not raw dicts
- Use `operator.add` reducer for accumulating lists (e.g. messages)
- Keep state minimal — store references (IDs), not large objects (full documents)
- Never use mutable default values in state fields

```python
from typing import Annotated, TypedDict
from langchain_core.messages import BaseMessage
import operator

# Good — typed, with reducer
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    current_step: str
    iteration_count: int

# Bad — raw dict, no types
# state = {"messages": [], "step": ""}
```

## Graph Construction

- Define node functions as standalone functions — not methods on a class (unless state management requires it)
- Name nodes descriptively — `"classify_intent"` not `"node_1"`
- Define conditional edge functions separately with clear names — not inline lambdas
- Use `END` explicitly — never rely on implicit termination
- Add `interrupt_before` / `interrupt_after` for human-in-the-loop — not polling patterns
- Limit graphs to 8-10 nodes — use subgraphs for larger workflows

```python
# Good — clear structure
def should_continue(state: AgentState) -> str:
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return "end"

graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})

# Bad — inline lambda, unclear routing
graph.add_conditional_edges("agent", lambda s: "tools" if s["messages"][-1].tool_calls else "end")
```

## Tool Definitions

- Use the `@tool` decorator for simple tools — `BaseTool` subclass only when you need custom parsing or async behavior
- Write clear docstrings — the LLM reads them to decide when to use the tool
- Use Pydantic models for complex tool input schemas (`args_schema`)
- Keep tools focused — one action per tool
- Return strings from tools — the framework handles message wrapping

```python
from langchain_core.tools import tool
from pydantic import BaseModel, Field

class SearchInput(BaseModel):
    query: str = Field(description="The search query")
    max_results: int = Field(default=5, description="Maximum results to return")

@tool(args_schema=SearchInput)
def search(query: str, max_results: int = 5) -> str:
    """Search the knowledge base for relevant information."""
    results = knowledge_base.search(query, limit=max_results)
    return "\n".join(r.content for r in results)
```

## LLM Configuration

- Externalize model name, temperature, and max_tokens — never hardcode in chain definitions
- Use factory functions or dependency injection for LLM instances
- Set `max_tokens` explicitly — avoid unbounded generation
- Set `request_timeout` on all LLM clients
- Use `with_structured_output()` for JSON responses — not manual parsing prompts

```python
# Good — configurable, bounded
def get_llm(model: str = "gpt-4o", temperature: float = 0.0) -> BaseChatModel:
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        max_tokens=2048,
        request_timeout=30,
    )

# Bad — hardcoded everywhere
llm = ChatOpenAI(model="gpt-4o")  # scattered across files
```

## Error Handling

- Use `with_retry()` for transient LLM API errors — configure max attempts and backoff
- Use `with_fallbacks()` for critical paths — e.g. fall back to a cheaper model
- Handle `OutputParserException` explicitly — provide a recovery path
- Never use bare `except:` on LLM calls — catch specific exceptions
- Log failed LLM calls with input context for debugging (redact sensitive data)

```python
# Good — resilient chain
chain = (
    prompt
    | llm.with_retry(stop_after_attempt=3)
    | parser.with_retry(stop_after_attempt=2)
).with_fallbacks([prompt | fallback_llm | parser])
```

## Naming Conventions

- Chain/graph variables: `snake_case` describing the workflow — `classify_chain`, `rag_pipeline`
- Node functions: `snake_case` verbs — `classify_intent`, `retrieve_documents`, `generate_response`
- State classes: `PascalCase` with `State` suffix — `AgentState`, `RAGState`
- Prompt constants: `UPPER_SNAKE_CASE` — `CLASSIFY_PROMPT`, `SYSTEM_TEMPLATE`
- Tool functions: `snake_case` verbs — `search_documents`, `calculate_price`
- Config keys: `snake_case` — `thread_id`, `max_retries`

## File Organization

```
src/
├── agents/
│   ├── graph.py             # Graph definition and compilation
│   ├── nodes.py             # Node functions
│   ├── state.py             # State TypedDict
│   └── edges.py             # Conditional edge functions
├── chains/
│   ├── rag.py               # RAG chain composition
│   └── summarize.py         # Summarization chain
├── prompts/
│   ├── classify.py          # Classification prompts
│   └── generate.py          # Generation prompts
├── tools/
│   ├── search.py            # Search tool
│   └── calculator.py        # Calculator tool
└── config.py                # LLM and model configuration
```
