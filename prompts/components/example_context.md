# Retrieved Example Context

When structure-aware retrieval selects examples, the experiment inserts them using this wrapper:

```text
/* Similar natural-language/SQL examples */
{{RETRIEVED_EXAMPLES}}
```

The complete experimental example repository is not included in this prompt release.

Each selected example is formatted exactly as follows:

```text
/* Few-shot Examples (K={{K}}, Masked Question Similarity):
Q1: {{EXAMPLE_QUESTION_1}}
Hint1: {{EXAMPLE_EVIDENCE_1}}
A1: {{EXAMPLE_SQL_1}}

Q2: {{EXAMPLE_QUESTION_2}}
Hint2: {{EXAMPLE_EVIDENCE_2}}
A2: {{EXAMPLE_SQL_2}}

*/
```

`HintN` is omitted when the selected record has no evidence field. The formal experiments use `K=2`. Selection ranks eligible examples by deterministic template similarity, trajectory-semantic tag overlap, and masked-question lexical similarity. Strict benchmark runs exclude exact questions, masked-equal questions, and examples whose SQL skeleton equals the target gold SQL skeleton before any example is inserted into the prompt.
