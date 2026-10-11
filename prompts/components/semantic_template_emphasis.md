# Deterministic Semantic-Template Emphasis

This block is produced by the deterministic [`LightTemplate` extractor](../support/light_template.py) used in the experiment. Only fields whose values are not false, null, zero, or empty are included.

```text
/* Deterministically extracted semantic emphasis:
- time_role: {{TIME_ROLE}}
- origin: {{ORIGIN}}
- destination: {{DESTINATION}}
- passing: {{PASSING}}
- output_id: {{OUTPUT_ID}}
- output_position: {{OUTPUT_POSITION}}
- output_speed: {{OUTPUT_SPEED}}
- output_distance: {{OUTPUT_DISTANCE}}
- output_date: {{OUTPUT_DATE}}
- grouped_average_speed: {{GROUPED_AVERAGE_SPEED}}
- ratio_fraction: {{RATIO_FRACTION}}
- ordered_passing: {{ORDERED_PASSING}}
- forbidden_invented_date: {{FORBIDDEN_INVENTED_DATE}}
- deterministic_single: {{DETERMINISTIC_SINGLE}}
- endpoint_ratio_population: {{ENDPOINT_RATIO_POPULATION}}
- requested_precision: {{REQUESTED_PRECISION}}
*/
```

This is runtime context, not a separate LLM template-extraction prompt.
