# Model-Facing Examples

Files in this folder are safe to turn into model training or evaluation inputs.

```text
visual_intake_sft.example.jsonl
  image pixels + compact task context -> visual_intake JSON

diagnosis_sft.example.jsonl
  visual intake + memory + selected wiki refs + user question -> diagnosis JSON

chat_memory_sft.example.jsonl
  recent transcript + memory + optional image order references -> assistant
  message + memory update

behavior_eval_inputs.example.jsonl
  input-only regression prompts. Expected answers and pass criteria are stored
  separately in system_records/eval_oracles.example.jsonl.
```

For supervised fine-tuning, `target` is the label. During inference, the model
should only receive the prompt built from `model_input`, attached image pixels,
and selected wiki text.
