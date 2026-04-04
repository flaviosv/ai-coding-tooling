---
name: tests-tdd
description: >
  Test-Driven Development methodology — behavioral principles for writing tests before
  implementation. Covers the red-green-refactor cycle, when to apply TDD, and when to skip it.
  Technology agnostic. Use when the user says "TDD", "test-driven", "red-green-refactor",
  "write test first", or "test-first". Do NOT use for writing tests without TDD intent — use
  the tests skill. Do NOT use for reviewing test quality — use the tests-code-review skill.
metadata:
  version: "1.0.0"
  triggers:
    - "TDD"
    - "test-driven"
    - "red-green-refactor"
    - "write test first"
    - "test-first"
---

# Test-Driven Development

Behavioral principles for test-first development. Apply regardless of language or framework.

## 1. Test First, Always

**Never write implementation before a failing test. The test defines what success looks like before a single line of production code exists.**

- Start every task by writing a test that describes the expected behavior.
- The test must fail for the right reason — not because of a syntax error or missing import.
- If you cannot write a test first, the requirement is not clear enough. Clarify before coding.
- A test written after the code is confirmation bias, not TDD.

## 2. Red-Green-Refactor

**The three-step cycle. Red: write a failing test. Green: write the minimum code to pass. Refactor: clean up while all tests stay green.**

- Red — one test, one behavior. Run it. Watch it fail. Read the failure message.
- Green — write the simplest code that makes the test pass. No cleverness, no extras.
- Refactor — improve structure, remove duplication, rename for clarity. Tests must stay green.
- Never skip refactor. The green phase produces ugly code on purpose — refactor is where design emerges.

## 3. Small Steps

**Each cycle adds one behavior. Write one test, make it pass, clean up, repeat.**

- If you write more than ~10 lines of production code to pass a test, the test covers too much. Split it.
- Resist the urge to "just finish this part" — that is where bugs hide.
- Commit after each green-refactor cycle. Small commits are cheap insurance.
- If a test requires complex setup to pass, that signals a design problem — address it now.

## 4. Discipline Over Speed

**TDD feels slower at first. The discipline is the point.**

- Skipping "just this once" leads to untested code piling up. Do not skip.
- The compound interest of test-first pays back in refactoring confidence and fewer regression bugs.
- If you feel the urge to write implementation first and "add tests later", stop. That is the moment TDD matters most.
- TDD is not about testing — it is about design. The tests force you to think about the interface before the implementation.

## When to Apply TDD

### Bug fixes
1. Write a failing test that reproduces the bug
2. Fix the bug — minimum code to make the test pass
3. Verify no regressions introduced

### New features
1. Write tests for expected behavior — they must fail
2. Implement the minimum code to make tests pass
3. Refactor if needed — tests must still pass

### Refactoring
1. Run existing tests — all must pass (establish baseline)
2. Refactor
3. Run tests again — behavior must be unchanged

## When NOT to Apply TDD

- **Spiking / prototyping** — exploring a new library or API to learn how it works. Throw the spike away and TDD the real implementation.
- **Trivial code** — getters, setters, simple data classes with no logic. Tests add noise without value.
- **UI exploration** — visual layout, styling, design iteration. TDD the behavior behind the UI, not the pixels.

## Tech-Specific Patterns

This skill is methodology-only. For language and framework-specific test patterns (fixtures, assertion styles, framework idioms), load matching reference files from the **tests** skill's `references/` directory following the naming convention `<language>-*` and `<framework>-*`.

## Example

User says: "Use TDD to implement the discount calculator."

1. Write test: `test_no_discount_for_order_below_threshold` — assert original price returned. Run — red.
2. Implement: return price unchanged. Run — green.
3. Write test: `test_10_percent_discount_above_100` — assert discounted price. Run — red.
4. Implement: add threshold check and discount logic. Run — green.
5. Refactor: extract discount percentage as a constant. Run — green.
6. Repeat until all behaviors are covered.

## References

- **tests** skill — test writing, coverage analysis, tech-specific patterns
- **tests-code-review** skill — reviewing test quality
