from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from dataclasses import asdict, dataclass
from statistics import mean, stdev
from typing import Any, Literal

import numpy as np
from nomad import files
from nomad.datamodel import EntryArchive, EntryMetadata
from nomad.datamodel.context import ServerContext
from nomad.datamodel.data import ArchiveSection, EntryData
from nomad.datamodel.hdf5 import HDF5Dataset
from nomad.metainfo import Quantity, SubSection

from nomad_simulations.schema_packages.properties.molecular_orbitals import (
    MolecularOrbitals,
)

BenchmarkKind = Literal['mo', 'density']
StorageKind = Literal['plain_array', 'hdf5_dataset']


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


class PlainChargeDensity(ArchiveSection):
    """
    Benchmark-only control case that mimics a bulky 3D charge-density grid.
    """

    n_x = Quantity(type=np.int32)
    n_y = Quantity(type=np.int32)
    n_z = Quantity(type=np.int32)

    value = Quantity(
        type=np.float64,
        shape=['n_x', 'n_y', 'n_z'],
    )


class HDF5ChargeDensity(ArchiveSection):
    """
    HDF5-backed 3D payload used to emulate charge-density storage.
    """

    n_x = Quantity(type=np.int32)
    n_y = Quantity(type=np.int32)
    n_z = Quantity(type=np.int32)

    value = Quantity(
        type=HDF5Dataset,
        shape=[],
    )


class PlainBenchmarkEntry(EntryData):
    payload = SubSection(sub_section=ArchiveSection.m_def)


class HDF5BenchmarkEntry(EntryData):
    payload = SubSection(sub_section=ArchiveSection.m_def)


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
    checksum_primary: float
    checksum_secondary: float | None


def _build_archive(
    section: ArchiveSection,
    upload_id: str,
    entry_id: str,
    upload_files: Any,
) -> EntryArchive:
    return EntryArchive(
        m_context=ServerContext(
            upload=BenchmarkUpload(upload_id=upload_id, upload_files=upload_files)
        ),
        metadata=EntryMetadata(upload_id=upload_id, entry_id=entry_id),
        data=PlainBenchmarkEntry(payload=section),
    )


def _make_section(
    benchmark_kind: BenchmarkKind,
    storage_kind: StorageKind,
    shape: tuple[int, ...],
) -> ArchiveSection:
    if benchmark_kind == 'mo':
        n_mo, n_ao = shape
        if storage_kind == 'plain_array':
            return PlainArrayMolecularOrbitals(n_mo=n_mo, n_ao=n_ao)
        return MolecularOrbitals(n_mo=n_mo, n_ao=n_ao)

    n_x, n_y, n_z = shape
    if storage_kind == 'plain_array':
        return PlainChargeDensity(n_x=n_x, n_y=n_y, n_z=n_z)
    return HDF5ChargeDensity(n_x=n_x, n_y=n_y, n_z=n_z)


def _assign_payload(
    section: ArchiveSection,
    benchmark_kind: BenchmarkKind,
    primary: np.ndarray,
    secondary: np.ndarray | None,
) -> None:
    if benchmark_kind == 'mo':
        section.mo_coefficients = primary
        if secondary is not None:
            section.mo_coefficients_im = secondary
        return

    section.value = primary


def _read_payload(
    section: ArchiveSection,
    benchmark_kind: BenchmarkKind,
    storage_kind: StorageKind,
    with_secondary: bool,
) -> tuple[float, float | None]:
    if benchmark_kind == 'mo':
        if storage_kind == 'plain_array':
            checksum_primary = float(np.asarray(section.mo_coefficients).sum())
            checksum_secondary = None
            if with_secondary:
                checksum_secondary = float(np.asarray(section.mo_coefficients_im).sum())
            return checksum_primary, checksum_secondary

        with section.mo_coefficients as dataset:
            checksum_primary = float(np.asarray(dataset[()]).sum())
        checksum_secondary = None
        if with_secondary:
            with section.mo_coefficients_im as dataset:
                checksum_secondary = float(np.asarray(dataset[()]).sum())
        return checksum_primary, checksum_secondary

    if storage_kind == 'plain_array':
        return float(np.asarray(section.value).sum()), None

    with section.value as dataset:
        return float(np.asarray(dataset[()]).sum()), None


def run_case(
    *,
    benchmark_kind: BenchmarkKind,
    storage_kind: StorageKind,
    shape: tuple[int, ...],
    primary: np.ndarray,
    secondary: np.ndarray | None,
) -> BenchmarkSample:
    upload_id = f'benchmark_{benchmark_kind}_{storage_kind}_{uuid.uuid4().hex}'
    entry_id = f'entry_{uuid.uuid4().hex}'
    upload_files = files.StagingUploadFiles(upload_id, create=True)

    try:
        section = _make_section(
            benchmark_kind=benchmark_kind,
            storage_kind=storage_kind,
            shape=shape,
        )
        archive = _build_archive(
            section=section,
            upload_id=upload_id,
            entry_id=entry_id,
            upload_files=upload_files,
        )

        start = time.perf_counter()
        _assign_payload(
            section=section,
            benchmark_kind=benchmark_kind,
            primary=primary,
            secondary=secondary,
        )
        assignment_seconds = time.perf_counter() - start

        start = time.perf_counter()
        serialized = archive.m_to_dict()
        serialize_seconds = time.perf_counter() - start

        json_payload_bytes = len(json.dumps(serialized).encode('utf-8'))
        hdf5_path = upload_files.archive_hdf5_location(entry_id)
        hdf5_bytes = os.path.getsize(hdf5_path) if os.path.exists(hdf5_path) else 0

        start = time.perf_counter()
        checksum_primary, checksum_secondary = _read_payload(
            section=section,
            benchmark_kind=benchmark_kind,
            storage_kind=storage_kind,
            with_secondary=secondary is not None,
        )
        readback_seconds = time.perf_counter() - start

        return BenchmarkSample(
            assignment_seconds=assignment_seconds,
            serialize_seconds=serialize_seconds,
            readback_seconds=readback_seconds,
            json_payload_bytes=json_payload_bytes,
            hdf5_bytes=hdf5_bytes,
            checksum_primary=checksum_primary,
            checksum_secondary=checksum_secondary,
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
        'checksum_primary': [sample.checksum_primary for sample in samples],
    }
    if samples[0].checksum_secondary is not None:
        metrics['checksum_secondary'] = [
            float(sample.checksum_secondary)
            for sample in samples
            if sample.checksum_secondary is not None
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


def _shape_label(shape: tuple[int, ...]) -> str:
    return ' x '.join(str(dim) for dim in shape)


def print_report(results: dict[str, Any]) -> None:
    print(
        f'Benchmark: {results["benchmark_kind"]} '
        f'(shape={_shape_label(tuple(results["shape"]))}, repeats={results["repeats"]})'
    )
    if results.get('complex_case') is not None:
        print(f'Complex payload: {results["complex_case"]}')
    print()

    for storage_kind in ('plain_array', 'hdf5_dataset'):
        case = results['cases'][storage_kind]
        print(storage_kind)
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
        checksum_line = f'primary={case["checksum_primary"]["mean"]:.6f}'
        if 'checksum_secondary' in case:
            checksum_line += f', secondary={case["checksum_secondary"]["mean"]:.6f}'
        print(f'  checksum  : {checksum_line}')
        print()


def benchmark_payload(
    *,
    benchmark_kind: BenchmarkKind,
    shape: tuple[int, ...],
    repeats: int,
    seed: int,
    complex_case: bool = False,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    primary = rng.random(shape, dtype=np.float64)
    secondary = None
    if benchmark_kind == 'mo' and complex_case:
        secondary = rng.random(shape, dtype=np.float64)

    results: dict[str, Any] = {
        'benchmark_kind': benchmark_kind,
        'shape': list(shape),
        'repeats': repeats,
        'seed': seed,
        'cases': {},
    }
    if benchmark_kind == 'mo':
        results['complex_case'] = complex_case

    for storage_kind in ('plain_array', 'hdf5_dataset'):
        samples = [
            run_case(
                benchmark_kind=benchmark_kind,
                storage_kind=storage_kind,
                shape=shape,
                primary=primary,
                secondary=secondary,
            )
            for _ in range(repeats)
        ]
        results['cases'][storage_kind] = summarize(samples)

    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            'Benchmark plain nested-array storage against HDF5-backed storage '
            'for bulky MO matrices and synthetic 3D charge-density grids.'
        )
    )
    parser.add_argument(
        '--benchmark',
        choices=('mo', 'density', 'both'),
        default='mo',
        help='Which benchmark payload to run.',
    )
    parser.add_argument(
        '--n-mo', type=int, default=2048, help='Number of molecular orbitals.'
    )
    parser.add_argument(
        '--n-ao', type=int, default=2048, help='Number of atomic orbitals.'
    )
    parser.add_argument(
        '--grid-shape',
        type=int,
        nargs=3,
        metavar=('NX', 'NY', 'NZ'),
        default=(200, 200, 200),
        help='3D grid shape for the charge-density-like benchmark.',
    )
    parser.add_argument(
        '--complex',
        action='store_true',
        dest='complex_case',
        help='Include an imaginary coefficient matrix in the MO benchmark.',
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

    benchmark_results: list[dict[str, Any]] = []
    if args.benchmark in ('mo', 'both'):
        benchmark_results.append(
            benchmark_payload(
                benchmark_kind='mo',
                shape=(args.n_mo, args.n_ao),
                repeats=args.repeats,
                seed=args.seed,
                complex_case=args.complex_case,
            )
        )
    if args.benchmark in ('density', 'both'):
        benchmark_results.append(
            benchmark_payload(
                benchmark_kind='density',
                shape=tuple(args.grid_shape),
                repeats=args.repeats,
                seed=args.seed,
            )
        )

    if len(benchmark_results) == 1:
        output: dict[str, Any] = benchmark_results[0]
    else:
        output = {'benchmarks': benchmark_results}

    for result in benchmark_results:
        print_report(result)

    if args.output_json:
        with open(args.output_json, 'w', encoding='utf-8') as handle:
            json.dump(output, handle, indent=2)
            handle.write('\n')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
