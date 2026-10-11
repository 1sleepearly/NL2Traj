# Structure-aware examples

Examples are kept separate from prompt instructions and knowledge. NL2Traj masks entity names, temporal expressions, coordinates, and numeric constants before similarity retrieval so selection emphasizes logical query structure.

The public examples in this directory are illustrative, not the full experimental example repository. Retrieval code, embeddings, and top-k selection are implementation concerns rather than prompt text.

Each example records the original question, a logic-masked representation, trajectory semantics, and a SQL reference.

