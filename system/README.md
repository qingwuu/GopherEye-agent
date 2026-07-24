# GopherEye System Docs

This folder contains implementation, model, data, provider, tool, schema, and
source-ingestion documentation.

Keep these separate from `wiki/`.

```text
wiki/
  Plant, grape leaf, disease-evidence, procedure, routine, and reviewed
  resource knowledge used as app-facing domain context.

system/
  How the app works: models, agents, providers, tools, schemas, source intake,
  data memory, evaluation, and workflow implementation.
```

## Sections

- [Single-Model Wiki Concept](concepts/single_model_wiki.md)
- [Current GopherEye Model](models/current_model.md)
- [Model Choice](models/model_choice.md)
- [Frontier Agent System](agents/frontier_agent_system.md)
- [Agent Context Reading Policy](agents/context_reading_policy.md)
- [Schema Layer](contracts/schema_layer.md)
- [Tool Layer](tools/tool_layer.md)
- [Dataset Memory Direction](data/dataset_memory.md)
- [Data Agent Workflow](data/data_agent_workflow.md)
- [Single-Model Workflow](workflows/single_model_workflow.md)
- [Wiki Update System](workflows/wiki_update_system.md)
- [Raw Source Intake Rules](source_requirements/raw_source_intake_rules.md)
- [Manual Source Backlog](source_requirements/manual_source_backlog.md)
