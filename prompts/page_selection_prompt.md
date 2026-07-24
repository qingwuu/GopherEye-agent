# Page Selection Prompt

Use this prompt when the same model must choose relevant wiki pages.

```text
You are selecting GopherEye wiki pages for a task.

Return only JSON:
{
  "selected_page_ids": ["..."],
  "reason": "short reason"
}

Rules:
- Select only pages listed in the catalog.
- Prefer disease pages, workflow pages, and schema pages directly relevant to
  the question.
- For image diagnosis questions, include grape leaf foundation pages when leaf
  anatomy, leaf side, normal variation, or image quality is relevant.
- Do not select pages only because they share generic words.
- Select at most {max_selected_pages} pages.

User question:
{question}

Wiki catalog:
{catalog}
```
