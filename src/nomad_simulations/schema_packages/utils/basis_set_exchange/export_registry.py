from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = ROOT / 'registry_min.json'


def _load_bse_names() -> tuple[str | None, list[dict[str, Any]]]:
    """
    Load the canonical basis-set names bundled with Basis Set Exchange.

    This function intentionally imports BSE lazily so the package remains an
    offline development-time source for the registry, not a runtime dependency.
    """
    try:
        import basis_set_exchange as bse
        from basis_set_exchange import misc
    except ImportError as exc:
        raise SystemExit(
            'basis_set_exchange is required only to regenerate this registry. '
            'Install the electronic-registry development dependencies, e.g. '
            '`uv run --extra dev-electronic python -m '
            'nomad_simulations.schema_packages.utils.basis_set_exchange.export_registry`.'
        ) from exc

    records = [
        {
            'key': misc.basis_name_to_filename(name),
            'canonical_name': name,
        }
        for name in bse.get_all_basis_names()
    ]
    records.sort(key=lambda rec: rec['key'])
    return getattr(bse, '__version__', None), records


def export_registry(output: Path = DEFAULT_OUTPUT, *, check: bool = False) -> int:
    bse_version, records = _load_bse_names()

    text = json.dumps(records, indent=2, ensure_ascii=False)
    text += '\n'

    if check:
        current = output.read_text(encoding='utf-8')
        if current != text:
            raise SystemExit(
                f'{output} is not up to date with Basis Set Exchange'
                + (f' {bse_version}' if bse_version else '')
            )
        return len(records)

    output.write_text(text, encoding='utf-8')
    return len(records)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            'Export the Basis Set Exchange canonical basis-set name list to '
            "NOMAD's lightweight runtime registry. No numerical basis data is "
            'exported.'
        )
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f'Path to write. Defaults to {DEFAULT_OUTPUT}.',
    )
    parser.add_argument(
        '--check',
        action='store_true',
        help='Fail if the output file is not already up to date.',
    )
    args = parser.parse_args()

    count = export_registry(args.output, check=args.check)
    action = 'checked' if args.check else 'wrote'
    print(f'{action} {count} Basis Set Exchange basis-set names: {args.output}')


if __name__ == '__main__':
    main()
