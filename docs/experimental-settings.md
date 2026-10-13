# Experimental settings

This document records the main settings that affect the comparison of DAIL-SQL, SSpa, DIN-SQL, and Traj-P. Transport-level API retries are separate from algorithmic SQL refinement.

## Method comparison

| Setting | DAIL-SQL | SSpa | DIN-SQL | Traj-P |
| --- | --- | --- | --- | --- |
| Few-shot context | Top-2 dynamically retrieved examples | Top-2 dynamically retrieved examples | Fixed stage-level demonstrations; no dynamic Top-K retrieval | Top-2 dynamically retrieved examples |
| Example isolation | Retrieval is restricted to the example pool of the current SQL-skeleton-disjoint fold; target gold SQL is not included in the prompt | Same as DAIL-SQL | Not applicable; fixed cross-domain demonstrations are used | Exact questions, masked-equivalent questions, and examples with the same lexical gold-SQL skeleton are excluded; gold SQL is used only as an exclusion key |
| Fixed DIN-SQL demonstrations | Not applicable | Not applicable | Schema linking 10; classification/decomposition 10; generation EASY 14, NON-NESTED 7, NESTED 11; gentle correction 0 | Not applicable |
| Requested initial temperature | 0.1 | 0.0 | 0.0 | 1.0 |
| Requested correction temperature | Not applicable | 0.0 | 0.0 | 0.1 |
| Initial SQL candidates | One preliminary SQL for retrieval, then one final SQL | Five candidates per generation round | One generated SQL after schema linking and classification/decomposition | Generate two first; expand to five unless both pass semantic validation and have the same canonical execution result |
| Candidate selection | Use the final SQL directly | Majority vote over canonicalized execution results of executable candidates | Use the gently corrected SQL directly | Prioritize deterministic semantic validity, then combine semantic score and execution-result agreement |
| Correction feedback | None | Schema tips for missing relations, missing columns, and ambiguous column references | One prompt-only gentle-correction call using the question, database context, schema links, predicted difficulty, decomposition, and initial SQL | Typed execution-error and trajectory-semantic feedback |
| Maximum correction | 0 | Up to four feedback rounds after the initial round; at most five generation rounds in total | One fixed gentle-correction call | Up to two targeted repair calls |
| Output contract | One executable PostgreSQL `SELECT`/`WITH` query, without explanations or invented schema elements | Same as DAIL-SQL | Structured JSON for schema linking and classification/decomposition; one read-only PostgreSQL `SELECT`/`WITH` query for generation and correction | Same SQL-only contract as DAIL-SQL |

DIN-SQL uses four fixed stages—schema linking, classification/decomposition, category-conditioned SQL generation, and gentle correction. Its recorded matrix value of `K=2` does not change its fixed demonstrations.

## Shared controls

| Setting | Implementation |
| --- | --- |
| Random seed | Not set; the evaluated endpoints did not provide a verified seed-control path |
| SQL timeout | PostgreSQL `statement_timeout` is 30 seconds for every method |
| API failures | Network, rate-limit, and service retries are transport-level recovery and do not count as SQL correction rounds |

Temperatures in the comparison table are the values requested by each method in the DeepSeek experiments.

## Run protocol

Each model–method–dataset configuration in the standard experiment matrix is run once without an additional stochastic repeat. The leakage-controlled template-disjoint evaluation uses four folds; each model–method–fold configuration is run once and results are aggregated across folds.
