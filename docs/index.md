
<!-- This is the force-directed graph using Cytoscape
    <div id="cy"></div>
-->

Welcome to the NOMAD documentation for `nomad-simulations`, a schema for computational materials science data.

## Where to Start

The documentation is split into three complementary sections:

- [Schema Navigation > Overview](schema/index.md): auto-generated reference for section trees, quantities, inheritance, and relationship diagrams.
- [Schema Explanation > Overview](explanation/overview.md): hand-written guidance for design rationale, modeling conventions, and usage patterns.
- [Dev Docs > Overview](dev_docs/overview.md): contributor-focused references, development process guidance, and historical design context.

## Context

NOMAD is a free, open-source data management platform for materials science aligned with FAIR principles (Findable, Accessible, Interoperable, Reusable). For broader platform documentation, see the [NOMAD docs](https://nomad-lab.eu/prod/v1/staging/docs/) and [NOMAD base sections guide](https://nomad-lab.eu/prod/v1/staging/docs/howto/customization/base_sections.html).

The `nomad-simulations` schema provides reusable core sections that can be extended for code-specific and domain-specific schemas while preserving consistent structure, interoperability, and discoverability.

When designing sections, we follow established object-oriented design
principles and patterns (for example, [SOLID](https://en.wikipedia.org/wiki/SOLID)
and [Design Patterns by Gamma et al.](https://en.wikipedia.org/wiki/Design_Patterns)).

Throughout this documentation, we use UML class diagrams to represent schema
relationships. UML is specified by the
[Object Management Group (OMG)](https://www.omg.org/spec/UML/).

## Contributing

If you want to contribute schema or documentation updates:

1. Fork the repository and create a focused branch.
2. Check [Dev Docs > Overview](dev_docs/overview.md) before changing established patterns.
3. Implement your extension following the [Schema Development Guide](dev_docs/schema_development_guide.md).
4. Update docs according to the [Documentation Writing Guide](dev_docs/documentation_writing_guide.md).
5. Open a pull request against upstream with a clear scope and test evidence.
