# LangChain / LangGraph Coding Style Guide

Applies to: LangChain 0.3+ / langchain-core 0.3+, LangGraph 0.2+

---

## General LangChain / LangGraph Patterns

Rules that apply across all supported versions.

### Chain Composition

- Use LCEL (LangChain Expression Language) for all chain composition — `LLMChain`, `SequentialChain`, `SimpleSequentialChain`, and `ConversationChain` are deprecated; never use them in new code
- Compose with the pipe operator `|` for readability: `prompt | llm | parser`
- Extract reusable sub-chains into named variables — avoid deeply nested inline pipes
- Use `RunnablePassthrough.assign()` to add computed fields to the chain context without breaking the pipeline
- Prefer `RunnableLambda` over raw Python lambdas for named, debuggable, and traceable steps

```python
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# Good — clear, composable LCEL with named steps
retrieval_chain = (
    RunnablePassthrough.assign(context=retriever | format_docs)
    | prompt
    | llm
    | StrOutputParser()
)

# Bad — legacy API
from langchain.chains import LLMChain  # Do not use
chain = LLMChain(llm=llm, prompt=prompt)
```

### Prompt Management

- Define prompts in dedicated modules or constants — not inline in chain definitions
- Use `ChatPromptTemplate.from_messages()` for all chat model interactions — not raw string templates
- Include a clear system message that defines role, constraints, and expected output format
- Use input variables consistently — document expected keys at the top of the prompt module
- Never interpolate user input directly into system prompt strings — always use `("human", "{variable}")` placeholders

```python
from langchain_core.prompts import ChatPromptTemplate

# Good — separated, typed, safe
CLASSIFY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Classify the user message into one of: {categories}. Respond with only the category name."),
    ("human", "{message}"),
])

# Bad — f-string injection into system prompt (prompt injection risk)
prompt = f"Classify this: {user_message}"
```

### LLM Configuration

- Externalize model name, temperature, and `max_tokens` — never hardcode in chain or graph files
- Use factory functions or dependency injection for LLM instances; do not instantiate `ChatOpenAI` / `ChatAnthropic` scattered across files
- Set `max_tokens` explicitly on every LLM instance to prevent unbounded generation
- Set `request_timeout` on all LLM clients to prevent indefinite blocking
- Use `with_structured_output()` with a Pydantic model for structured responses — not manual JSON-parsing prompts

```python
from langchain.chat_models import init_chat_model

# Good — configurable, bounded, injectable
def get_llm(model: str = "gpt-4o", temperature: float = 0.0) -> BaseChatModel:
    return init_chat_model(
        model,
        temperature=temperature,
        max_tokens=2048,
        timeout=30,
    )

# Bad — hardcoded everywhere
llm = ChatOpenAI(model="gpt-4o")  # no bounds, scattered across files
```

### Tool Definitions

- Use the `@tool` decorator for simple tools — subclass `BaseTool` only when you need custom async behavior or complex parsing
- Write clear, specific docstrings — the LLM uses the docstring to decide when and how to call the tool
- Define `args_schema` as a Pydantic model for all tools with more than one input or complex validation
- Keep tools focused — one action per tool; combine only when the combined operation is genuinely atomic
- Return strings from tools — the framework handles message wrapping into `ToolMessage`
- Validate all tool inputs at the function boundary — never trust that the LLM will supply safe values

```python
from langchain_core.tools import tool
from pydantic import BaseModel, Field

class SearchInput(BaseModel):
    query: str = Field(description="The search query to execute")
    max_results: int = Field(default=5, description="Maximum number of results to return", ge=1, le=20)

@tool(args_schema=SearchInput)
def search_knowledge_base(query: str, max_results: int = 5) -> str:
    """Search the internal knowledge base for information relevant to the query."""
    results = knowledge_base.search(query, limit=max_results)
    return "\n".join(r.content for r in results)
```

### Error Handling

- Use `with_retry()` on LLM calls for transient API errors — set `stop_after_attempt` explicitly
- Use `with_fallbacks()` for critical paths — e.g. fall back to a lighter model on primary failure
- Handle `OutputParserException` explicitly — provide a recovery path, do not let it bubble silently
- Never use bare `except:` on LLM calls — catch specific exceptions from the provider library
- Use `RetryPolicy` on `add_node()` for nodes with transient failures — not hand-rolled retry loops inside node bodies

```python
from langchain_core.runnables import RunnableWithFallbacks

# Good — resilient chain with retry and fallback
chain = (
    prompt
    | llm.with_retry(stop_after_attempt=3)
    | parser
).with_fallbacks([prompt | fallback_llm | parser])
```

### Naming Conventions

- Chain/graph variables: `snake_case` describing the workflow — `classify_chain`, `rag_pipeline`, `answer_graph`
- Node functions: `snake_case` action verbs — `classify_intent`, `retrieve_documents`, `generate_response`
- State classes: `PascalCase` with `State` suffix — `AgentState`, `RAGState`, `WorkflowState`
- Prompt constants: `UPPER_SNAKE_CASE` — `CLASSIFY_PROMPT`, `SYSTEM_TEMPLATE`, `RAG_PROMPT`
- Tool functions: `snake_case` action verbs — `search_documents`, `calculate_price`, `fetch_user_profile`
- Config keys in `configurable`: `snake_case` — `thread_id`, `max_retries`, `user_id`

---

## LangChain 0.3

Everything in the General section plus the following additions and clarifications specific to the 0.3 API surface.

### Use `init_chat_model` for Provider-Agnostic LLM Instantiation

`init_chat_model` (introduced in 0.2, stabilized in 0.3) replaces direct imports of provider-specific classes and makes provider switching trivial.

```python
from langchain.chat_models import init_chat_model

# Good — provider-agnostic, easy to switch
llm = init_chat_model("gpt-4o", temperature=0.0, max_tokens=1024)
llm_claude = init_chat_model("claude-sonnet-4-5-20250929", temperature=0.0)

# Less preferred — ties code to a specific provider import
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="gpt-4o")
```

### Use `add_messages` Reducer for Message Accumulation

The `add_messages` reducer from `langgraph.graph.message` correctly handles merging message lists, deduplication by ID, and update-by-ID semantics. Use it in preference to `operator.add` for message fields.

```python
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages

class State(TypedDict):
    messages: Annotated[list, add_messages]  # Use add_messages, not operator.add
```

---

## LangGraph 0.2+

### State Design

- Define state as `TypedDict` with `Annotated` fields for reducers — not raw dicts
- Use `add_messages` reducer for message fields; use `operator.add` for other accumulating lists with a custom reducer when needed
- Keep state minimal — store references (IDs, keys), not large objects (full documents, raw HTML)
- Never use mutable default values in state field definitions

```python
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
import operator

# Good — typed, reduced, minimal
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    current_step: str
    iteration_count: int

# Bad — raw dict, no types, no reducers
state = {"messages": [], "step": "start"}
```

### Graph Construction

- Define node functions as standalone module-level functions — not closures or methods on a class unless the class holds shared dependencies
- Name nodes descriptively — `"classify_intent"` not `"node_1"` or `"step_a"`
- Define conditional edge functions as standalone named functions — not inline lambdas
- Use `START` from `langgraph.graph` as the graph entry edge — not hardcoding the first node name
- Use `END` from `langgraph.graph` explicitly as the terminal node — never rely on a missing edge as implicit termination
- Use `interrupt_before` / `interrupt_after` on `compile()` for human-in-the-loop — not polling or `sleep` inside nodes
- Resume interrupted graphs with `Command(resume=...)` — not by re-invoking with a new initial state
- Limit individual graphs to ~10 nodes — use subgraphs for larger, compositionally distinct workflows

```python
from typing import Literal
from langgraph.graph import START, END, StateGraph

# Good — clear routing, named function, explicit terminals
def should_continue(state: AgentState) -> Literal["tools", "end"]:
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return "end"

workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)
workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
workflow.add_edge("tools", "agent")
app = workflow.compile()

# Bad — inline lambda, missing START/END, implicit termination
graph.add_conditional_edges("agent", lambda s: "tools" if s["messages"][-1].tool_calls else "end")
```

### Checkpointing

- Use `InMemorySaver` for development and testing only — it holds all state in process memory
- Use a persistent saver (PostgresSaver, RedisSaver, SqliteSaver) for production agents
- Always supply `{"configurable": {"thread_id": "<unique-id>"}}` in the invocation config when using a checkpointer
- Review what data ends up in checkpoints — avoid storing secrets or PII in graph state

```python
from langgraph.checkpoint.memory import InMemorySaver

# Testing
memory = InMemorySaver()
app = workflow.compile(checkpointer=memory)
result = app.invoke(inputs, config={"configurable": {"thread_id": "session-42"}})
```

### File Organization

```
src/
├── agents/
│   ├── graph.py             # StateGraph definition and compile()
│   ├── nodes.py             # Node functions
│   ├── state.py             # State TypedDict definitions
│   └── edges.py             # Conditional edge functions
├── chains/
│   ├── rag.py               # RAG chain composition
│   └── summarize.py         # Summarization chain
├── prompts/
│   ├── classify.py          # Classification prompts (UPPER_SNAKE_CASE constants)
│   └── generate.py          # Generation prompts
├── tools/
│   ├── search.py            # Search tool(s)
│   └── calculator.py        # Calculator tool
└── config.py                # LLM factory functions and model configuration
```

---

## Anti-Patterns

- `LLMChain` / `SequentialChain` / `SimpleSequentialChain` — all deprecated; use LCEL
- `AgentExecutor` with `initialize_agent()` — superseded by LangGraph; migrate to `StateGraph`
- `ConversationBufferMemory` / `ConversationSummaryMemory` from `langchain.memory` — superseded by LangGraph checkpointing with `add_messages` reducer
- Raw f-string interpolation of user input into system prompts — critical prompt injection risk
- `chain.run()` instead of `chain.invoke()` — `.run()` is deprecated in 0.2+
- LLM instantiation scattered across modules instead of a central factory function
- Inline lambda conditional edges — hard to test, hard to read, not traceable in LangSmith
- `PythonREPLTool` or `ShellTool` in any production code path — unrestricted code execution
- Storing full document content in LangGraph state — bloats checkpoints and serialization on every node
