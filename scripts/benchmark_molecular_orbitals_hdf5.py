from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from dataclasses import asdict, dataclass
from statistics import mean, stdev
from typing import Any

import numpy as np
from nomad import files
from nomad.datamodel import EntryArchive, EntryMetadata
from nomad.datamodel.context import ServerContext
from nomad.datamodel.data import ArchiveSection, EntryData
from nomad.metainfo import Quantity, SubSection

from nomad_simulations.schema_packages.properties.molecular_orbitals import (
    MolecularOrbitals,
)


class PlainArrayMolecularOrbitals(ArchiveSection):
    """
    Benchmark-only control case that mimics the pre-HDF5 MO coefficient storage.
    """

    n_mo = Quantity(type=np.int32)
    n_ao = Quantity(type=np.int32)

    mo_coefficients = Quantity(
        type=np.float64,
        shape=['n_mo', 'n_ao'],
    )

    mo_coefficients_im = Quantity(
        type=np.float64,
        shape=['n_mo', 'n_ao'],
    )


class PlainBenchmarkEntry(EntryData):
    molecular_orbitals = SubSection(sub_section=PlainArrayMolecularOrbitals.m_def)


class HDF5BenchmarkEntry(EntryData):
    molecular_orbitals = SubSection(sub_section=MolecularOrbitals.m_def)


@dataclass
class BenchmarkUpload:
    upload_id: str
    upload_files: Any


@dataclass
class BenchmarkSample:
    assignment_seconds: float
    serialize_seconds: float
    readback_seconds: float
    json_payload_bytes: int
    hdf5_bytes: int
    checksum_real: float
    checksum_imag: float | None


def _build_archive(
    section: ArchiveSection,
    upload_id: str,
    entry_id: str,
    upload_files: Any,
) -> EntryArchive:
    entry_cls = (
        HDF5BenchmarkEntry
        if isinstance(section, MolecularOrbitals)
        else PlainBenchmarkEntry
    )
    return EntryArchive(
        m_context=ServerContext(
            upload=BenchmarkUpload(upload_id=upload_id, upload_files=upload_files)
        ),
        metadata=EntryMetadata(upload_id=upload_id, entry_id=entry_id),
        data=entry_cls(molecular_orbitals=section),
    )


def _read_plain(
    section: PlainArrayMolecularOrbitals, complex_case: bool
) -> tuple[float, float | None]:
    checksum_real = float(np.asarray(section.mo_coefficients).sum())
    checksum_imag = None
    if complex_case:
        checksum_imag = float(np.asarray(section.mo_coefficients_im).sum())
    return checksum_real, checksum_imag


def _read_hdf5(
    section: MolecularOrbitals, complex_case: bool
) -> tuple[float, float | None]:
    with section.mo_coefficients as dataset:
        checksum_real = float(np.asarray(dataset[()]).sum())

    checksum_imag = None
    if complex_case:
        with section.mo_coefficients_im as dataset:
            checksum_imag = float(np.asarray(dataset[()]).sum())

    return checksum_real, checksum_imag


def run_case(
    *,
    label: str,
    n_mo: int,
    n_ao: int,
    complex_case: bool,
    coeff_real: np.ndarray,
    coeff_imag: np.ndarray | None,
) -> BenchmarkSample:
    upload_id = f'benchmark_mo_{label}_{uuid.uuid4().hex}'
    entry_id = f'entry_{uuid.uuid4().hex}'
    upload_files = files.StagingUploadFiles(upload_id, create=True)

    try:
        if label == 'plain_array':
            section = PlainArrayMolecularOrbitals(n_mo=n_mo, n_ao=n_ao)
        elif label == 'hdf5_dataset':
            section = MolecularOrbitals(n_mo=n_mo, n_ao=n_ao)
        else:
            raise ValueError(f'Unknown benchmark label: {label}')

        archive = _build_archive(
            section=section,
            upload_id=upload_id,
            entry_id=entry_id,
            upload_files=upload_files,
        )

        start = time.perf_counter()
        section.mo_coefficients = coeff_real
        if complex_case and coeff_imag is not None:
            section.mo_coefficients_im = coeff_imag
        assignment_seconds = time.perf_counter() - start

        start = time.perf_counter()
        serialized = archive.m_to_dict()
        serialize_seconds = time.perf_counter() - start

        json_payload_bytes = len(json.dumps(serialized).encode('utf-8'))
        hdf5_path = upload_files.archive_hdf5_location(entry_id)
        hdf5_bytes = os.path.getsize(hdf5_path) if os.path.exists(hdf5_path) else 0

        start = time.perf_counter()
        if label == 'plain_array':
            checksum_real, checksum_imag = _read_plain(section, complex_case)
        else:
            checksum_real, checksum_imag = _read_hdf5(section, complex_case)
        readback_seconds = time.perf_counter() - start

        return BenchmarkSample(
            assignment_seconds=assignment_seconds,
            serialize_seconds=serialize_seconds,
            readback_seconds=readback_seconds,
            json_payload_bytes=json_payload_bytes,
            hdf5_bytes=hdf5_bytes,
            checksum_real=checksum_real,
            checksum_imag=checksum_imag,
        )
    finally:
        upload_files.delete()


def summarize(samples: list[BenchmarkSample]) -> dict[str, Any]:
    metrics: dict[str, list[float]] = {
        'assignment_seconds': [sample.assignment_seconds for sample in samples],
        'serialize_seconds': [sample.serialize_seconds for sample in samples],
        'readback_seconds': [sample.readback_seconds for sample in samples],
        'json_payload_bytes': [float(sample.json_payload_bytes) for sample in samples],
        'hdf5_bytes': [float(sample.hdf5_bytes) for sample in samples],
        'checksum_real': [sample.checksum_real for sample in samples],
    }
    if samples[0].checksum_imag is not None:
        metrics['checksum_imag'] = [
            float(sample.checksum_imag)
            for sample in samples
            if sample.checksum_imag is not None
        ]

    summary: dict[str, Any] = {'samples': [asdict(sample) for sample in samples]}
    for metric_name, values in metrics.items():
        summary[metric_name] = {
            'mean': mean(values),
            'min': min(values),
            'max': max(values),
            'stdev': stdev(values) if len(values) > 1 else 0.0,
        }
    return summary


def format_bytes(num_bytes: float) -> str:
    units = ['B', 'KiB', 'MiB', 'GiB', 'TiB']
    value = float(num_bytes)
    for unit in units:
        if value < 1024.0 or unit == units[-1]:
            return f'{value:.2f} {unit}'
        value /= 1024.0
    return f'{value:.2f} TiB'


def print_report(results: dict[str, Any]) -> None:
    print(
        'Benchmark shape: '
        f'n_mo={results["n_mo"]}, n_ao={results["n_ao"]}, '
        f'complex={results["complex_case"]}, repeats={results["repeats"]}'
    )
    print()

    for label in ('plain_array', 'hdf5_dataset'):
        case = results['cases'][label]
        print(label)
        print(
            '  assignment: '
            f'{case["assignment_seconds"]["mean"]:.6f}s '
            f'(min {case["assignment_seconds"]["min"]:.6f}s, '
            f'max {case["assignment_seconds"]["max"]:.6f}s)'
        )
        print(
            '  serialize : '
            f'{case["serialize_seconds"]["mean"]:.6f}s '
            f'(min {case["serialize_seconds"]["min"]:.6f}s, '
            f'max {case["serialize_seconds"]["max"]:.6f}s)'
        )
        print(
            '  readback  : '
            f'{case["readback_seconds"]["mean"]:.6f}s '
            f'(min {case["readback_seconds"]["min"]:.6f}s, '
            f'max {case["readback_seconds"]["max"]:.6f}s)'
        )
        print(f'  json size : {format_bytes(case["json_payload_bytes"]["mean"])}')
        print(f'  hdf5 size : {format_bytes(case["hdf5_bytes"]["mean"])}')
        print(
            '  checksum  : '
            f'real={case["checksum_real"]["mean"]:.6f}'
            + (
                f', imag={case["checksum_imag"]["mean"]:.6f}'
                if 'checksum_imag' in case
                else ''
            )
        )
        print()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            'Benchmark plain nested-array MO coefficient storage against the '
            'HDF5-backed MolecularOrbitals implementation.'
        )
    )
    parser.add_argument(
        '--n-mo', type=int, default=2048, help='Number of molecular orbitals.'
    )
    parser.add_argument(
        '--n-ao', type=int, default=2048, help='Number of atomic orbitals.'
    )
    parser.add_argument(
        '--complex',
        action='store_true',
        dest='complex_case',
        help='Include an imaginary coefficient matrix in addition to the real part.',
    )
    parser.add_argument(
        '--repeats', type=int, default=3, help='Number of repetitions per case.'
    )
    parser.add_argument(
        '--seed',
        type=int,
        default=13,
        help='Random seed used to create deterministic input data.',
    )
    parser.add_argument(
        '--output-json',
        type=str,
        default=None,
        help='Optional path for writing the full benchmark results as JSON.',
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rng = np.random.default_rng(args.seed)
    coeff_real = rng.random((args.n_mo, args.n_ao), dtype=np.float64)
    coeff_imag = (
        rng.random((args.n_mo, args.n_ao), dtype=np.float64)
        if args.complex_case
        else None
    )

    results = {
        'n_mo': args.n_mo,
        'n_ao': args.n_ao,
        'complex_case': args.complex_case,
        'repeats': args.repeats,
        'seed': args.seed,
        'cases': {},
    }

    for label in ('plain_array', 'hdf5_dataset'):
        samples = [
            run_case(
                label=label,
                n_mo=args.n_mo,
                n_ao=args.n_ao,
                complex_case=args.complex_case,
                coeff_real=coeff_real,
                coeff_imag=coeff_imag,
            )
            for _ in range(args.repeats)
        ]
        results['cases'][label] = summarize(samples)

    print_report(results)

    if args.output_json:
        with open(args.output_json, 'w', encoding='utf-8') as handle:
            json.dump(results, handle, indent=2)
            handle.write('\n')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
