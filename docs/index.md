
<!-- This is the force-directed graph using Cytoscape
    <div id="cy"></div>
-->

Welcome to the NOMAD documentation for `nomad-simulations`, a schema for computational materials science data.

## Where to Start

The documentation is split into three complementary sections:

- [Schema Navigation: Overview](schema/index.md): auto-generated reference for section trees, quantities, inheritance, and relationship diagrams.
- [Schema Explanation: Overview](explanation/overview.md): hand-written guidance for design rationale, modeling conventions, and usage patterns.
- [Dev Docs: Overview](dev_docs/overview.md): contributor-focused references, development process guidance, and historical design context.

## Context

NOMAD is a free, open-source data management platform for materials science aligned with FAIR principles (Findable, Accessible, Interoperable, Reusable). For broader platform documentation, see the [NOMAD docs](https://nomad-lab.eu/prod/v1/staging/docs/) and [NOMAD base sections guide](https://nomad-lab.eu/prod/v1/staging/docs/howto/customization/base_sections.html).

The `nomad-simulations` schema provides reusable core sections that can be extended for code-specific and domain-specific schemas while preserving consistent structure, interoperability, and discoverability.

When designing the sections, we follow [SOLID principles](https://www.geeksforgeeks.org/solid-principle-in-programming-understand-with-real-life-examples/) for object-oriented programming wherever possible.

Throughout this documentation, we use [UML diagrams](https://en.wikipedia.org/wiki/Class_diagram) to represent schema relationships.

## Contributing

If you want to contribute schema or documentation updates:

1. Fork the repository and create a focused branch.
2. Check [Dev Docs: Overview](dev_docs/overview.md) before changing established patterns.
3. Implement your extension following the [Schema Development Guide](software-development-guide.md).
4. Update docs according to the [Documentation Authoring Guide](explanation/doc_guidelines.md).
5. Open a pull request against upstream with a clear scope and test evidence.
