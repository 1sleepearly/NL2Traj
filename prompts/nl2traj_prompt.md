# NL2Traj Prompt Assembly

The formal experiment assembles the NL2Traj prompt in the following order. Each placeholder is replaced at runtime with the corresponding component or case-specific context.

Initial generation uses `{{GENERATION_SYSTEM_PROMPT}}`. Targeted repair uses `{{REPAIR_SYSTEM_PROMPT}}`; both values are published in `components/system_prompts.md`.

```text
/* Static spatial knowledge used by NL2Traj */
{{SPATIAL_DATABASE_KNOWLEDGE}}

{{TRAJECTORY_KNOWLEDGE}}

{{TIME_CONVENTIONS}}

{{RETRIEVED_EXAMPLES}}

{{SEMANTIC_TEMPLATE_EMPHASIS}}

{{DATABASE_CONTEXT}}

{{TYPED_TRAJECTORY_FEEDBACK}}

{{SQL_OUTPUT_CONTRACT}}
```

For initial generation, `{{TYPED_TRAJECTORY_FEEDBACK}}` is empty. During targeted repair, the same prompt is rebuilt with typed execution or trajectory-semantic feedback in that position.
