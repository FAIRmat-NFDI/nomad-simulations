# Schema Development

This section contains published technical guidance for contributors who extend, populate, or implement the `nomad-simulations` schema in code.

Use this section for pages whose primary purpose is implementation: defining new schema classes, adding quantities or subsections, implementing normalization logic, and writing parser-side population patterns.

## Technical Development Pages

- [Populating `Simulation` and `Program`](simulation_entry_population.md): parser-side population pattern for the top-level simulation entry.
- [Bounded Data Types](data_types.md): defining bounded quantities and using bounded data types in schema extensions.
- [Normalization](normalize.md): implementing and reasoning about `normalize()` behavior in custom sections.
- [Model System Usage Guidelines](model_system_usage_guidelines.md): required rules for contributors populating and extending `ModelSystem`.

## Contribution Guides

For overarching contribution process and documentation workflow guidance, see:

- [Contribution Guides Overview](../contributor_guides/overview.md)
- [Schema Development Guide](../contributor_guides/schema_development_guide.md)
- [Documentation Writing Guide](../contributor_guides/documentation_writing_guide.md)
- [Documentation Automation Guide](../contributor_guides/documentation_automation_guide.md)
