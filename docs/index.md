
<!-- This is the force-directed graph using Cytoscape
    <div id="cy"></div>
-->

**Welcome to the NOMAD documentation for the Schema developed for Computational Materials Scientists**, where you can find information about how to use the NOMAD schema definition to store the data output by your simulations.
This project contains all the information about the main base sections and their `SubSections` and `Quantities` relevant for simulations. We propose here a general schema which could then be used as a basis to build more specific schemas.

The documentation is split into two complementary sections:

- `Schema Navigation` (auto-generated): canonical source for section trees, quantities, inheritance, and relationship diagrams.
- `Schema Explanation` (hand-written): design rationale, modeling decisions, migration notes, and parser usage guidance.

Start here:

- [Schema Navigation: Overview](schema/index.md)
- [Schema Explanation: Overview](explanation/overview.md)
- [Schema Explanation Old: Overview](explanation_old/index.md) (development-time comparison snapshot)

NOMAD is a free open-source data management platform for Materials Science which follows the F.A.I.R. (Findable, Accessible, Interoperable, and Reusable) principles. This documentation page is a part of the more [general NOMAD documentation](https://nomad-lab.eu/prod/v1/staging/docs/), as well as on the usage of [NOMAD base sections](https://nomad-lab.eu/prod/v1/staging/docs/howto/customization/base_sections.html).

When designing the sections, we follow [SOLID principles](https://www.geeksforgeeks.org/solid-principle-in-programming-understand-with-real-life-examples/) for object-oriented programming. And throughout this documentation, we will use [UML diagrams](https://en.wikipedia.org/wiki/Class_diagram), both in a simplified and in a detailed manner, to draw the schemas relationships.
