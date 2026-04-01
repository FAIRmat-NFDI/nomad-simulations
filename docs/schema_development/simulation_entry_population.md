# Populating `Simulation` and `Program`

This page gives implementation-oriented guidance for populating the top-level `Simulation` entry and its `Program` subsection in parser code.

For the conceptual meaning of these sections in archive data, see [Simulation Entry](../explanation/simulation_entry.md).

## Purpose

In parser implementations, `Program` is typically one of the first subsections populated under `Simulation`. It identifies the software that produced the data and provides a stable software context for the rest of the archive.

## Minimal Parser Pattern

A simple parser-side pattern is:

1. Extract program metadata from the source files.
2. Instantiate `Simulation`.
3. Populate `simulation.program` with the parsed software metadata.
4. Append the populated `Simulation` section to `archive.data`.

For example, imagine a file containing:

```txt
! * * * * * * *
! Welcome to SUPERCODE, version 7.0
...
```

The parser can extract the program name and version and store them in the archive:

```python
from nomad.parsing.file_parser import TextParser, Quantity
from nomad_simulations.schema_packages.general import Simulation, Program


class SUPERCODEParser:
    """
    Class responsible to populate the NOMAD `archive` from the files given by a
    SUPERCODE simulation.
    """

    def parse(self, filepath, archive, logger):
        output_parser = TextParser(
            quantities=[
                Quantity('program_version', r'version *([\d\.]+) *', repeats=False)
            ]
        )
        output_parser.mainfile = filepath

        simulation = Simulation()
        simulation.program = Program(
            name='SUPERCODE',
            version=output_parser.get('program_version'),
        )
        # append `Simulation` as an `archive.data` section
        archive.data.append(simulation)
```

## Notes

- Keep the conceptual meaning of `Simulation` and `Program` in the explanation docs.
- Keep parser-specific extraction patterns and archive-population examples in `Schema Development`.
- Follow the broader development workflow and contribution rules in [Contribution Guides Overview](../contributor_guides/overview.md).
