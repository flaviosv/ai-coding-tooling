# LangChain / LangGraph Security Reference

Supplements the general Python security guidelines for projects using LangChain and LangGraph.

Applies to: LangChain 0.3+ / langchain-core 0.3+, LangGraph 0.2+

---

## 0) Scope

This document covers security patterns specific to LLM-powered applications built with LangChain
and LangGraph. It focuses on AI-specific threats: prompt injection, LLM output validation,
credential handling for LLM APIs, and sensitive data leakage through prompts and traces.
General Python security rules still apply and are not repeated here.

---

## 1) Prompt Injection Prevention

### LC-SEC-001: Never interpolate raw user input into system prompts

Severity: Critical

User input that reaches the system message can override assistant behavior, bypass guardrails,
exfiltrate context, or redirect tool calls. This is the primary prompt injection vector.

Required:

- MUST use `ChatPromptTemplate.from_messages()` with separate `("system", ...)` and `("human", "{variable}")` tuples.
- MUST NOT use f-strings, `.format()`, `%` formatting, or string concatenation to inject user-controlled values into the system message.

Insecure pattern:

```python
# Bad — user controls the system message; can override instructions
system_msg = f"You are a helpful assistant. Answer: {user_input}"
response = llm.invoke(system_msg)
```

Secure pattern:

```python
from langchain_core.prompts import ChatPromptTemplate

# Good — user input isolated in the human message slot
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant. Answer only questions about {domain}."),
    ("human", "{user_input}"),
])
chain = prompt | llm
response = chain.invoke({"domain": "finance", "user_input": user_input})
```

### LC-SEC-002: Do not embed user-supplied content in tool definitions or agent instructions

Severity: High

Tool descriptions and system prompts that include dynamic content from user input extend the
injection surface beyond the initial human message.

Required:

- MUST NOT construct tool docstrings or `name` fields from user-supplied data.
- MUST NOT include user-controlled variables in system prompts that define agent persona, capabilities, or restrictions.
- SHOULD treat any content retrieved from external sources (web scraping, user-uploaded files, database content) as untrusted and capable of carrying injection payloads.

---

## 2) LLM Output Validation

### LC-SEC-003: Validate and constrain structured LLM output before use

Severity: High

LLM-generated structured output (JSON, tool call arguments, routing decisions) must be
validated before being used in application logic. The LLM may produce malformed, out-of-range,
or malicious values — especially when inputs are attacker-controlled.

Required:

- MUST use `with_structured_output()` with a Pydantic model — not manual JSON parsing or `json.loads()` on raw LLM output.
- MUST validate parsed output against expected schemas before passing to downstream logic.
- SHOULD use `OutputFixingParser` or `RetryWithErrorOutputParser` for graceful recovery on parse failure.
- MUST NOT use `eval()` or `exec()` on any LLM-generated content.

Insecure pattern:

```python
# Bad — raw eval on LLM output
code = llm.invoke("Write a Python expression for the sum of a list.")
result = eval(code.content)  # arbitrary code execution
```

Secure pattern:

```python
from pydantic import BaseModel
from langchain.chat_models import init_chat_model

class SumResult(BaseModel):
    result: float

llm = init_chat_model("gpt-4o", max_tokens=64)
structured_llm = llm.with_structured_output(SumResult)
output = structured_llm.invoke("What is the sum of [1, 2, 3]?")
# output.result is a validated float — no eval
```

### LC-SEC-004: Validate LLM-generated routing decisions

Severity: High

Conditional edge functions that route graph execution must validate LLM output — they should
never pass arbitrary LLM-generated strings directly as routing keys.

Required:

- MUST define an explicit allowlist of valid routing destinations and validate against it.
- MUST return a safe default (e.g. `"end"`) when the LLM output does not match any valid destination.

```python
from typing import Literal

VALID_ROUTES: set[str] = {"tools", "human_review", "end"}

def should_continue(state: AgentState) -> Literal["tools", "human_review", "end"]:
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    # No LLM-generated string is trusted as a routing key
    return "end"
```

---

## 3) Tool Security

### LC-SEC-005: Never expose unrestricted shell or code execution tools

Severity: Critical

`PythonREPLTool`, `ShellTool`, and `BashProcess` execute arbitrary code in the server process.
They must not appear in any production or user-facing code path.

Required:

- MUST NOT use `PythonREPLTool`, `ShellTool`, or `BashProcess` in production.
- MUST build purpose-specific tools with explicit, constrained inputs.
- MUST define `args_schema` (Pydantic model) on all tools to enforce input types and ranges.

### LC-SEC-006: Validate tool inputs independently of LLM output

Severity: High

Tool functions must validate their own inputs at the function boundary. The LLM may supply
out-of-range values, path traversal strings, SQL injection payloads, or SSRF-enabling URLs.

Required:

- MUST validate all tool inputs at the tool boundary — never assume the LLM supplies safe values.
- MUST NOT trust LLM-generated file paths, URLs, or database query fragments without validation.
- SHOULD use allowlists for constrained operations (allowed endpoints, table names, directories).

```python
from pathlib import Path
from langchain_core.tools import tool
from pydantic import BaseModel, Field

ALLOWED_DIR = Path("/data/reports").resolve()

class FileReadInput(BaseModel):
    path: str = Field(description="Relative path within the reports directory")

@tool(args_schema=FileReadInput)
def read_report(path: str) -> str:
    """Read a report file from the allowed reports directory."""
    resolved = (ALLOWED_DIR / path).resolve()
    if not resolved.is_relative_to(ALLOWED_DIR):
        raise ValueError("Access denied: path outside allowed directory")
    if not resolved.is_file():
        raise ValueError("File not found")
    return resolved.read_text(encoding="utf-8")
```

### LC-SEC-007: Apply least-privilege access to tools

Severity: Medium

Tools should operate with the minimum permissions required for their task.

Required:

- Database tools MUST use read-only connections unless writes are explicitly required.
- API tools MUST use scoped tokens — not admin or root credentials.
- File tools MUST restrict access to a sandboxed directory.
- HTTP tools MUST validate URLs against an allowlist of approved domains to prevent SSRF.

---

## 4) Credential and Secret Handling

### LC-SEC-008: Load all LLM API keys from environment variables

Severity: Critical

LLM provider credentials (`$OPENAI_API_KEY`, `$ANTHROPIC_API_KEY`, `$LANGCHAIN_API_KEY`, etc.)
must never appear in source code, configuration files committed to version control, or
LangGraph state.

Required:

- MUST load API keys exclusively from environment variables — never hardcoded, never in `.env` files committed to the repository.
- MUST NOT log, print, or include API keys in error messages, tracebacks, or test output.
- SHOULD use a secrets manager (AWS Secrets Manager, HashiCorp Vault) for production deployments.

```python
import os

# Good — loaded from environment at runtime
llm = init_chat_model(
    os.environ["LLM_MODEL"],   # e.g. "gpt-4o"
    # Provider SDK picks up OPENAI_API_KEY / ANTHROPIC_API_KEY automatically from env
)

# Bad — credential in source
llm = ChatOpenAI(api_key="sk-...")  # Never do this
```

### LC-SEC-009: Do not store secrets or PII in LangGraph state

Severity: High

LangGraph state is checkpointed and may be serialized to persistent storage (database, Redis).
Secrets and PII in state leak through checkpoints, trace logs, and error reports.

Required:

- MUST NOT store API keys, tokens, or credentials in graph state fields.
- SHOULD NOT store raw PII in state — use opaque references (user IDs, session tokens) and fetch from secure storage within nodes.
- MUST review checkpoint storage security: encryption at rest, access control, and retention policy.

---

## 5) Data Leakage Through Prompts and Traces

### LC-SEC-010: Sanitize data before sending to LLM provider APIs

Severity: High

All data included in prompts is transmitted to third-party LLM provider infrastructure. This
includes system messages, retrieved documents, tool outputs, and conversation history.

Required:

- MUST NOT include credentials, secrets, internal system architecture details, or database schemas in prompts or messages.
- SHOULD redact or pseudonymize PII before including it in LLM context — use a data masking layer if the use case involves sensitive personal data.
- MUST audit what data flows into the `messages` list before it reaches the LLM API call.

### LC-SEC-011: Control what LangSmith traces capture

Severity: Medium

LangSmith traces contain full prompt/response content, tool inputs/outputs, and intermediate
state values. By default, all of this is sent to LangSmith's cloud service.

Required:

- MUST use a dedicated LangSmith project for production — not shared with development or staging.
- SHOULD configure `LANGCHAIN_HIDE_INPUTS=true` and `LANGCHAIN_HIDE_OUTPUTS=true` for any workflow that processes sensitive personal data.
- MUST NOT commit `LANGCHAIN_API_KEY` to version control or include it in application logs.
- SHOULD review trace retention policies for compliance with applicable data regulations (GDPR, HIPAA, SOC 2).

---

## 6) Retrieval and RAG Security

### LC-SEC-012: Enforce access control on retrieved documents at the vector store level

Severity: High

RAG applications must respect document-level permissions. The vector store does not enforce
authorization by default — every document in the index is retrievable unless filtered explicitly.

Required:

- MUST filter retrieval results by user/tenant permissions using vector store metadata filters — not post-retrieval Python filtering.
- MUST NOT rely on the LLM to enforce access control. Instructions like "only show documents the user can see" in a prompt are not a security control — they are bypassable.
- SHOULD tag documents with access control metadata (tenant ID, permission level) at ingestion time.

```python
# Good — filter at the vector store level; unauthorized documents never enter the context
results = vectorstore.similarity_search(
    query,
    filter={"tenant_id": current_user.tenant_id, "classification": "public"},
)

# Bad — all documents retrieved, then filtered in Python (data already in memory)
results = vectorstore.similarity_search(query, k=100)
filtered = [r for r in results if r.metadata["tenant_id"] == current_user.tenant_id]
```

### LC-SEC-013: Treat ingested document content as untrusted

Severity: Medium

Documents ingested into vector stores (PDFs, web pages, user uploads) may contain embedded
prompt injection payloads. Injected instructions in retrieved documents can hijack agent behavior.

Required:

- SHOULD scan ingested documents for known prompt injection patterns before adding to the index.
- MUST NOT blindly trust content from user-uploaded documents — treat it as attacker-controlled.
- MUST validate content-type and file extension before processing uploads.
- SHOULD use a dedicated document processing pipeline that strips executable content (macros, scripts) before text extraction.

---

## 7) Dependency Security

### LC-SEC-014: Pin LangChain dependencies and audit community packages

Severity: Medium

The LangChain ecosystem includes many community-maintained packages (`langchain-community`)
with varying security review standards.

Required:

- MUST pin `langchain-core`, `langchain`, and `langgraph` to specific versions in production.
- SHOULD prefer official provider partner packages (`langchain-openai`, `langchain-anthropic`) over `langchain-community` equivalents when both exist.
- MUST review `langchain-community` package code before introducing it in production — community packages receive less rigorous security review than core packages.
- SHOULD run `pip audit` or `safety check` in CI to catch known CVEs in transitive dependencies.

```bash
# Good — run in CI pipeline
pip audit
# or
safety check -r requirements.txt
```
