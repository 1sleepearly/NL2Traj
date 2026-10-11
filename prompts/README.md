# NL2Traj Experimental Prompt

This directory publishes the fixed prompt text and assembly structure used by the formal NL2Traj experiment. Runtime values are represented by placeholders. Historical prompts, baseline prompts, ablation variants, the complete example set, and run-specific feedback are outside this release.

```text
prompts/
├── nl2traj_prompt.md
└── components/
    ├── spatial_database_knowledge.md
    ├── trajectory_knowledge.md
    ├── time_conventions.md
    ├── database_context.md
    ├── semantic_template_emphasis.md
    ├── example_context.md
    ├── feedback_context.md
    └── output_contract.md
```

The semantic emphasis block is extracted deterministically by experiment code; it is not produced by a separate LLM prompt. SQL refinement reuses the same NL2Traj prompt with typed feedback injected into the feedback block.

