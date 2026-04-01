[![NOMAD](https://img.shields.io/badge/Open%20NOMAD-lightgray?logo=data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0idXRmLTgiPz4KPCEtLSBHZW5lcmF0b3I6IEFkb2JlIElsbHVzdHJhdG9yIDI3LjUuMCwgU1ZHIEV4cG9ydCBQbHVnLUluIC4gU1ZHIFZlcnNpb246IDYuMDAgQnVpbGQgMCkgIC0tPgo8c3ZnIHZlcnNpb249IjEuMSIgaWQ9IkxheWVyXzEiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIgeG1sbnM6eGxpbms9Imh0dHA6Ly93d3cudzMub3JnLzE5OTkveGxpbmsiIHg9IjBweCIgeT0iMHB4IgoJIHZpZXdCb3g9IjAgMCAxNTAwIDE1MDAiIHN0eWxlPSJlbmFibGUtYmFja2dyb3VuZDpuZXcgMCAwIDE1MDAgMTUwMDsiIHhtbDpzcGFjZT0icHJlc2VydmUiPgo8c3R5bGUgdHlwZT0idGV4dC9jc3MiPgoJLnN0MHtmaWxsOiMxOTJFODY7c3Ryb2tlOiMxOTJFODY7c3Ryb2tlLXdpZHRoOjE0MS4zMjI3O3N0cm9rZS1taXRlcmxpbWl0OjEwO30KCS5zdDF7ZmlsbDojMkE0Q0RGO3N0cm9rZTojMkE0Q0RGO3N0cm9rZS13aWR0aDoxNDEuMzIyNztzdHJva2UtbWl0ZXJsaW1pdDoxMDt9Cjwvc3R5bGU+CjxwYXRoIGNsYXNzPSJzdDAiIGQ9Ik0xMTM2LjQsNjM2LjVjMTUwLjgsMCwyNzMuMS0xMjEuOSwyNzMuMS0yNzIuMlMxMjg3LjIsOTIuMSwxMTM2LjQsOTIuMWMtMTUwLjgsMC0yNzMuMSwxMjEuOS0yNzMuMSwyNzIuMgoJUzk4NS42LDYzNi41LDExMzYuNCw2MzYuNXoiLz4KPHBhdGggY2xhc3M9InN0MSIgZD0iTTEzMjksOTQ2Yy0xMDYuNC0xMDYtMjc4LjgtMTA2LTM4Ni4xLDBjLTk5LjYsOTkuMy0yNTguNywxMDYtMzY1LjEsMTguMWMtNi43LTcuNi0xMy40LTE2LjItMjEuMS0yMy45CgljLTEwNi40LTEwNi0xMDYuNC0yNzgsMC0zODQuOWMxMDYuNC0xMDYsMTA2LjQtMjc4LDAtMzg0LjlzLTI3OC44LTEwNi0zODYuMSwwYy0xMDcuMywxMDYtMTA2LjQsMjc4LDAsMzg0LjkKCWMxMDYuNCwxMDYsMTA2LjQsMjc4LDAsMzg0LjljLTYzLjIsNjMtODkuMSwxNTAtNzYuNywyMzIuMWM3LjcsNTcuMywzMy41LDExMy43LDc3LjYsMTU3LjZjMTA2LjQsMTA2LDI3OC44LDEwNiwzODYuMSwwCgljMTA2LjQtMTA2LDI3OC44LTEwNiwzODYuMSwwYzEwNi40LDEwNiwyNzguOCwxMDYsMzg2LjEsMEMxNDM1LjQsMTIyNCwxNDM1LjQsMTA1MiwxMzI5LDk0NnoiLz4KPC9zdmc+Cg==)](https://nomad-lab.eu/prod/v1/staging/gui/)
![](https://coveralls.io/repos/github/fairmat-nfdi/nomad-simulations/badge.svg?branch=develop)
![](https://img.shields.io/pypi/v/nomad-simulations)
![](https://img.shields.io/pypi/pyversions/nomad-simulations)
[![DOI](https://zenodo.org/badge/744481756.svg)](https://zenodo.org/badge/latestdoi/744481756)

> ⚠️ **Repository migration notice**
>
> This repository was migrated from `nomad-coe/nomad-simulations` to `fairmat-nfdi/nomad-simulations` on **2025-01-02**.
> Existing GitHub links and clone URLs continue to work via redirects.
>
> If you encounter any broken links or unexpected issues related to the migration, please report them.

# `nomad-simulations`

`nomad-simulations` is an open-source Python package for managing materials-science simulation data. It follows the plugin architecture of [NOMAD](https://nomad-lab.eu). The package provides section definitions (Python classes) with quantities and methods that support extracting and organizing data from different simulation codes. These definitions can be used, modified, and extended at the level needed by the user, and external contributions are welcome.

Read more in the [official documentation](https://fairmat-nfdi.github.io/nomad-simulations/) page.


## Getting started

`nomad-simulations` can be installed as a PyPI package using `pip`:

```sh
pip install nomad-simulations
```


## Development

If you want to develop locally, clone the project and create a virtual environment with Python 3.10 or newer:
```sh
git clone https://github.com/fairmat-nfdi/nomad-simulations.git
cd nomad-simulations
python3.11 -m venv .pyenv
. .pyenv/bin/activate
```

Make sure to have `pip` upgraded:
```sh
pip install --upgrade pip
```

We recommend installing `uv` for fast pip installation of the packages:
```sh
pip install uv
```

Install the package with development dependencies:
```sh
uv pip install '.[dev]'
```

The plugin is still under development. If you would like to contribute, install the package in editable mode (with the added `-e` flag):
```sh
uv pip install -e '.[dev]'
```

### Run the tests

You can run the tests locally:
```sh
uv run pytest -sv tests
```

where the `-s` and `-v` options toggle the output verbosity.

Our CI/CD pipeline produces a more comprehensive test report using the `pytest-cov` package. You can generate a local coverage report:
```sh
uv run pytest --cov=src tests
```

You can also run the script to generate a local file `coverage.txt` with the same information:
```sh
./scripts/generate_coverage_txt.sh
```


### Run linting and auto-formatting

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting the code. Ruff auto-formatting is also a part of the GitHub workflow actions. You can run locally:
```sh
uv run ruff check .
uv run ruff format . --check
```


### Debugging

For interactive debugging of the tests, use `pytest` with the `--pdb` flag. We recommend using an IDE for debugging, e.g., _VSCode_. If that is the case, add the following snippet to your `.vscode/launch.json`:
```json
{
  "configurations": [
      {
        "name": "<descriptive tag>",
        "type": "debugpy",
        "request": "launch",
        "cwd": "${workspaceFolder}",
        "program": "${workspaceFolder}/.pyenv/bin/pytest",
        "justMyCode": true,
        "env": {
            "_PYTEST_RAISE": "1"
        },
        "args": [
            "-sv",
            "--pdb",
            "<path-to-plugin-tests>",
        ]
    }
  ]
}
```

where `<path-to-plugin-tests>` must be changed to the local path to the test module to be debugged.

The settings configuration file `.vscode/settings.json` automatically applies the linting and formatting upon saving the modified file.


### Launching the documentation locally

To view the documentation locally, run MkDocs with the extra docs dependencies:

```sh
uv run --extra docs mkdocs serve
```

Documentation conventions for maintainers are tracked in [docs/contributor_guides/documentation_writing_guide.md](docs/contributor_guides/documentation_writing_guide.md).

Note that part of the documentation is generated via repository scripts. For that workflow, see [docs/contributor_guides/documentation_automation_guide.md](docs/contributor_guides/documentation_automation_guide.md).


## Adding this plugin to NOMAD

If you are developing locally using the `nomad-distro-dev` environment, see [NOMAD distro-dev README: day-to-day development](https://github.com/FAIRmat-NFDI/nomad-distro-dev/tree/main?tab=readme-ov-file#day-to-day-development).

If you are adding this plugin to a NOMAD Oasis, see [NOMAD plugin installation docs](https://nomad-lab.eu/prod/v1/staging/docs/howto/oasis/plugins_install.html).

## How to cite this work
Pizarro, J.M., Boydas, E.B., Daelman, N., Ladines, A.N., Mohr, B. & Rudzinski, J.F., NOMAD Simulations [Computer software]. https://zenodo.org/doi/10.5281/zenodo.13838811

## Main contributors
| Name | E-mail     | Topics | Github profiles |
|------|------------|--------|-----------------|
| Dr. Nathan Daelman | [nathan.daelman@physik.hu-berlin.de](mailto:nathan.daelman@physik.hu-berlin.de) | DFT, Precision | [@ndaelman-hu](https://github.com/ndaelman-hu) |
| Dr. Bernadette Mohr | [mohrbern@physik.hu-berlin.de](mailto:mohrbern@physik.hu-berlin.de) | MD, FF | [@Bernadette-Mohr](https://github.com/Bernadette-Mohr) |
| Dr. José M. Pizarro | [jose.pizarro@physik.hu-berlin.de](mailto:jose.pizarro@physik.hu-berlin.de) | GW, DMFT, BSE | [@JosePizarro3](https://github.com/JosePizarro3) |
| Dr. Esma B. Boydas | [esma.boydas@physik.hu-berlin.de](mailto:esma.boydas@physik.hu-berlin.de) | Quantum Chemistry | [@EBB2675](https://github.com/EBB2675) |
| Dr. Joseph F. Rudzinski (**Coordinator**) | [joseph.rudzinski@physik.hu-berlin.de](mailto:joseph.rudzinski@physik.hu-berlin.de) | General | [@JFRudzinski](https://github.com/JFRudzinski) |
