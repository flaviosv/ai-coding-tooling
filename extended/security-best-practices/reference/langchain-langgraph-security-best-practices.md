# LangChain / LangGraph Security Spec

Supplements the general Python security guidelines for projects using LangChain and LangGraph.

---

## 0) Scope

This document covers security patterns specific to LLM-powered applications built with LangChain
and LangGraph. General Python security rules still apply.

---

## 1) Prompt Injection Prevention

### LC-SEC-001: Never interpolate raw user input into system prompts

Severity: Critical

User input must go through designated `("human", "{variable}")` placeholders in
`ChatPromptTemplate` — never concatenated into system message strings.

Required:

- MUST use `ChatPromptTemplate.from_messages()` with separate system and human message tuples.
- MUST NOT use f-strings, `.format()`, or `%` formatting to inject user input into system prompts.

Insecure patterns:

```python
# Bad — user can override system instructions
prompt = f"You are a helpful assistant. User says: {user_input}"
```

Secure pattern:

```python
# Good — user input isolated in human message
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant."),
    ("human", "{user_input}"),
])
```

### LC-SEC-002: Validate and constrain structured LLM output

Severity: High

LLM-generated structured output (JSON, tool calls) must be validated before use in application
logic.

Required:

- MUST use `with_structured_output()` with a Pydantic model — not manual JSON parsing.
- MUST validate parsed output against expected schemas before using in downstream logic.
- SHOULD use `OutputFixingParser` or `RetryWithErrorOutputParser` for graceful recovery.

---

## 2) Tool Security

### LC-SEC-003: Never expose unrestricted shell or code execution tools

Severity: Critical

`PythonREPLTool`, `ShellTool`, and `BashProcess` must never be used in production or
user-facing applications.

Required:

- MUST NOT use `PythonREPLTool` or `ShellTool` in production.
- MUST build purpose-specific tools with explicit input validation.
- SHOULD use `args_schema` (Pydantic model) on all tools to constrain inputs.

### LC-SEC-004: Validate tool inputs independently of LLM output

Severity: High

Tool functions must validate their own inputs — never trust that the LLM will provide safe values.

Required:

- MUST validate all tool inputs at the tool boundary (path traversal, SQL injection, etc.).
- MUST NOT trust LLM-generated file paths, URLs, or database queries without validation.
- SHOULD use allowlists for constrained operations (e.g. allowed API endpoints, table names).

```python
@tool(args_schema=FileReadInput)
def read_file(path: str) -> str:
    """Read a file from the allowed directory."""
    resolved = Path(path).resolve()
    if not resolved.is_relative_to(ALLOWED_DIR):
        raise ValueError("Access denied: path outside allowed directory")
    return resolved.read_text()
```

### LC-SEC-005: Limit tool permissions to minimum necessary scope

Severity: Medium

Tools should operate with least-privilege access.

Required:

- Database tools SHOULD use read-only connections unless writes are explicitly required.
- API tools SHOULD use scoped tokens — not admin/root credentials.
- File tools MUST restrict access to a sandboxed directory.

---

## 3) Data Exposure

### LC-SEC-006: Do not store secrets or PII in graph state

Severity: High

Graph state is checkpointed and may be serialized to persistent storage. Sensitive data in state
can leak through checkpoints, traces, or logs.

Required:

- MUST NOT store API keys, tokens, or credentials in graph state.
- SHOULD NOT store raw PII in state — use references (user IDs) and fetch from secure storage.
- MUST review checkpoint storage security (encryption at rest, access controls).

### LC-SEC-007: Sanitize data before sending to LLM providers

Severity: High

Data sent to LLM APIs is transmitted to third-party infrastructure.

Required:

- MUST NOT include credentials, secrets, or internal system details in prompts or messages.
- SHOULD redact PII before including in LLM context (or use a data masking layer).
- MUST review what metadata is attached to LangSmith traces (traces may contain full prompts and responses).

---

## 4) Tracing and Observability

### LC-SEC-008: Secure LangSmith tracing configuration

Severity: Medium

LangSmith traces contain full prompt/response content and may include sensitive data.

Required:

- MUST use a dedicated LangSmith project for production — not shared with development.
- SHOULD configure `LANGCHAIN_HIDE_INPUTS` and `LANGCHAIN_HIDE_OUTPUTS` for sensitive workflows.
- MUST NOT log LangSmith API keys in application logs or error reports.
- SHOULD review trace retention policies for compliance with data regulations.

---

## 5) Retrieval Security

### LC-SEC-009: Enforce access control on retrieved documents

Severity: High

RAG applications must respect document-level permissions — the vector store does not enforce
authorization by default.

Required:

- MUST filter retrieval results by user permissions — use metadata filtering, not post-retrieval filtering.
- MUST NOT rely on the LLM to enforce access control ("only show documents the user can see" in the prompt is not a security control).
- SHOULD tag documents with access control metadata at ingestion time.

```python
# Good — filter at the vector store level
results = vectorstore.similarity_search(
    query,
    filter={"tenant_id": current_user.tenant_id},
)

# Bad — filter after retrieval (data already exposed to the retrieval pipeline)
results = vectorstore.similarity_search(query, k=100)
results = [r for r in results if r.metadata["tenant_id"] == current_user.tenant_id]
```

### LC-SEC-010: Sanitize document content before ingestion

Severity: Medium

Documents ingested into vector stores may contain malicious content (e.g. prompt injection payloads
embedded in PDFs or web pages).

Required:

- SHOULD scan ingested documents for known prompt injection patterns.
- MUST NOT blindly trust content from user-uploaded documents.
- SHOULD use content-type validation before processing (reject unexpected file types).

---

## 6) Dependency Security

### LC-SEC-011: Pin LangChain dependencies and audit community packages

Severity: Medium

The LangChain ecosystem has many community-maintained packages with varying security postures.

Required:

- MUST pin `langchain-core`, `langchain`, and `langgraph` to specific versions.
- SHOULD prefer `langchain-<provider>` official partner packages over `langchain-community` equivalents.
- MUST review `langchain-community` package code before using in production — community packages have less rigorous review.
- SHOULD run `pip audit` or equivalent in CI to catch known vulnerabilities.
