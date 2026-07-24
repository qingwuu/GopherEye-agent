# Evaluation

This folder stores behavior tests for the GopherEye wiki app.

The purpose is to compare:

```text
strong cloud model behavior
local model behavior
single-model wiki behavior
frontier provider behavior
```

## Files

```text
diagnosis_behavior_cases.jsonl
  Tests for image diagnosis and evidence sufficiency behavior.

wiki_qa_questions.jsonl
  Tests for wiki-grounded answers and page selection.
```

## Evaluation Criteria

```text
selected correct wiki page
answered from wiki instead of unsupported knowledge
requested missing abaxial image when needed
did not over-diagnose from weak evidence
returned valid JSON when schema was required
kept follow-up chat in scope
```

