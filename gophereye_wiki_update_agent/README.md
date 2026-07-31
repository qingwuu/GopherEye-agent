# GopherEye Wiki Update Agent

Independent CLI-first agent for source-backed wiki updates.

It is intentionally separate from:

```text
Frontier_model/              chat and diagnosis agent
gophereye_data_agent/        dataset automation agent
```

The update flow is:

```text
priority-source web search
-> broad web search
-> compact merged research JSON
-> build/read wiki catalog
-> model selects candidate pages
-> model reads selected current wiki pages
-> minimal append-only wiki operations
-> rebuild catalog automatically
-> save run artifacts
```

Install runtime dependencies if needed:

```bash
pip install -r gophereye_wiki_update_agent/requirements.txt
```

## Priority Sources

Manual priority sites live in:

```text
gophereye_wiki_update_agent/priority_sources.json
```

Those sources are searched first. They are not an exclusive allowlist; the agent
then runs a broad web search and can use other reliable sources.

Source shape:

```json
{
  "name": "UC IPM Grape",
  "url": "https://ipm.ucanr.edu/agriculture/grape/",
  "domains": ["ipm.ucanr.edu"],
  "topics": ["grape disease diagnosis", "treatment boundaries"]
}
```

Use another priority file for a run:

```bash
python -m gophereye_wiki_update_agent update "powdery mildew source update" \
  --priority-sources path/to/priority_sources.json
```

## Run

OpenAI:

```bash
python -m gophereye_wiki_update_agent update "latest extension guidance for grape powdery mildew visual diagnosis" \
  --profile openai_wiki_update
```

Claude:

```bash
python -m gophereye_wiki_update_agent update "new source-backed facts about grape downy mildew symptoms" \
  --profile anthropic_wiki_update
```

Dry run:

```bash
python -m gophereye_wiki_update_agent update "check current grape leaf anatomy references" \
  --profile openai_wiki_update \
  --dry-run \
  --json
```

Smoke test without API keys:

```bash
python -m gophereye_wiki_update_agent update "powdery mildew source update" \
  --profile echo \
  --dry-run \
  --json
```

Run artifacts are written under:

```text
wiki_update_agent_workspace/runs/
```

The catalog is rebuilt at:

```text
catalog/wiki/
```
