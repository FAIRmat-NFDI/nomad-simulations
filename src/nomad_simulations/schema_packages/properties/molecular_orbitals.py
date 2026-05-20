import itertools
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

import numpy as np
from nomad.datamodel.data import ArchiveSection
from nomad.datamodel.datamodel import JSON
from nomad.datamodel.hdf5 import HDF5Dataset, match_hdf5_reference
from nomad.datamodel.metainfo.basesections.v2 import Entity
from nomad.metainfo import URL, MEnum, Quantity, Reference, SectionProxy, SubSection
from nomad.units import ureg

from nomad_simulations.schema_packages.properties import ElectronicEigenvalues
from nomad_simulations.schema_packages.properties.orbital_volume import OrbitalVolume


class MolecularOrbitals(ElectronicEigenvalues):
    """
    Molecular-orbital eigenstates expressed in an atom-centred AO basis.

    Every quantity is either directly mappable to the TREXIO *mo* group or
    provides auxiliary metadata needed by NOMAD tooling.

    The TREXIO format:
    Posenitsky et al., J. Chem. Phys. 158, 174801 (2023).
    """

    # References
    basis_set_ref = Quantity(
        type=Reference(
            SectionProxy(
                'nomad_simulations.schema_packages.basis_set.AtomCenteredBasisSet'
            )
        ),
        description="""
        Reference to the atom-centered basis set in which these molecular
        orbitals are expanded.
        """,
    )

    # Dimension-defining scalars
    n_mo = Quantity(
        type=np.int32,
        description='Number of molecular orbitals stored.',
    )

    n_ao = Quantity(
        type=np.int32,
        description='Number of atomic orbitals (size of AO basis).',
    )

    # Per-orbital mandatory metadata
    mo_spin = Quantity(
        type=np.int32,
        shape=['n_mo'],
        description="""
        Spin index of each molecular orbital: 0 for α-spin, 1 for β-spin.
        """,
    )

    mo_energies = Quantity(
        type=np.float64,
        unit='electron_volt',
        shape=['n_mo'],
        description="""
        Orbital energies for each MO. In a canonical SCF these are the eigenvalues 
        of the (Fock) Hamiltonian; in correlated frameworks they may be natural-orbital
        energies or any other chosen set.
        """,
    )

    mo_occupations = Quantity(
        type=np.float64,
        shape=['n_mo'],
        description="""
        Occupation numbers for each MO. Closed-shell codes will typically give 2.0 
        for occupied and 0.0 for virtual orbitals; unrestricted codes use two channels.
        """,
    )

    # TODO: check via normalization
    mo_class = Quantity(
        type=MEnum('core', 'inactive', 'active', 'virtual', 'deleted'),
        shape=['n_mo'],
        description="""
        Role of each MO within a correlated calculation or active-space
        protocol:

        * core     : energy-frozen doubly-occupied  
        * inactive : doubly-occupied but variationally optimised  
        * active   : part of the active space  
        * virtual  : unoccupied (correlated) orbital  
        * deleted  : pruned for technical reasons
        """,
    )

    mo_symmetry = Quantity(
        type=str,
        shape=['n_mo'],
        description="""
        Symmetry label of each MO in the molecule's point group
        (e.g. *a₁*, *b₂u*, *pi_g*). Leave empty for systems with
        no detected symmetry.
        """,
    )

    # AO → MO coefficient matrices
    mo_coefficients = Quantity(
        type=HDF5Dataset,
        shape=[],
        description="""
        The AO→MO coefficient matrix **C**, such that 
        ψ_i(r) = ∑_μ C[i,μ] φ_μ(r). 
        Row index i runs over MOs, column index μ runs over AOs in `basis_set_ref`.
        """,
    )

    mo_coefficients_im = Quantity(
        type=HDF5Dataset,
        shape=[],
        description="""
        Imaginary component of the AO→MO coefficient matrix **C**. 
        Combine it with `mo_coefficients` to obtain the full complex matrix:
            C_complex = mo_coefficients + 1j * mo_coefficients_im  
        Leave this quantity unset (or an empty array) when the wave-function
        is strictly real, as is typical in non-relativistic calculations without complex basis functions.
        """,
    )

    # Whole-set classification
    mo_type = Quantity(
        type=MEnum('canonical', 'natural', 'localized', 'hybrid'),
        # default='canonical',
        description="""
        Classification of these orbitals:
          - canonical  : standard SCF eigenfunctions
          - natural    : eigenfunctions of the 1-RDM
          - localized  : after a localization transform (Boys, Pipek-Mezey, …)
          - hybrid     : e.g. post-HF (CASSCF) orbitals, etc.
        """,
    )

    orbital_volumes = SubSection(sub_section=OrbitalVolume.m_def, repeats=True)

    orbital_shape_viewer = Quantity(
        type=JSON,
        description="""
        Derived GUI payload for rendering real-space orbital volumes together with
        the corresponding structure.
        """,
    )

    def _infer_n_mo_from_hdf5(self) -> int | None:
        if isinstance(self.mo_coefficients, str):
            match = match_hdf5_reference(self.mo_coefficients)
            if match and 'shape' in match['path']:
                return None
        if (
            isinstance(self.mo_coefficients, np.ndarray)
            and self.mo_coefficients.ndim > 0
        ):
            return int(self.mo_coefficients.shape[0])
        return None

    @staticmethod
    def _to_float(value, unit=None):
        if value is None:
            return None
        if hasattr(value, 'to'):
            if unit is not None:
                value = value.to(unit)
            return float(value.magnitude)
        return float(value)

    @staticmethod
    def _to_vector_list(value, unit=None):
        if value is None:
            return None
        if hasattr(value, 'to'):
            if unit is not None:
                value = value.to(unit)
            value = value.magnitude
        return np.asarray(value, dtype=float).tolist()

    @staticmethod
    def _resolve_species(model_system):
        species = []
        for particle_state in model_system.particle_states or []:
            atomic_number = getattr(particle_state, 'atomic_number', None)
            if atomic_number is not None:
                species.append(int(atomic_number))
                continue
            chemical_symbol = getattr(particle_state, 'chemical_symbol', None)
            if chemical_symbol:
                try:
                    species.append(int(ureg.Quantity(chemical_symbol).magnitude))
                except Exception:
                    return None
                continue
            return None
        return species or None

    def _build_structure_payload(self, model_system):
        if model_system is None or model_system.positions is None:
            return None

        lattice_vectors = self._to_vector_list(
            getattr(model_system, 'lattice_vectors', None), unit=ureg.angstrom
        )
        periodic = getattr(model_system, 'periodic_boundary_conditions', None)
        if periodic is not None:
            periodic = [bool(value) for value in periodic]

        return {
            'systemId': model_system.m_path(),
            'positions': self._to_vector_list(
                model_system.positions, unit=ureg.angstrom
            ),
            'species': self._resolve_species(model_system),
            'latticeVectors': lattice_vectors,
            'periodic': periodic,
        }

    def _build_viewer_payload(self, archive: 'EntryArchive'):
        volumes = list(self.orbital_volumes or [])
        if not volumes:
            return None

        model_system = None
        if volumes[0].model_system_ref is not None:
            model_system = volumes[0].model_system_ref
        elif getattr(self.m_parent, 'model_system_ref', None) is not None:
            model_system = self.m_parent.model_system_ref

        structure = self._build_structure_payload(model_system)
        orbitals = []
        upload_id = getattr(getattr(archive, 'metadata', None), 'upload_id', None)
        entry_id = getattr(getattr(archive, 'metadata', None), 'entry_id', None)

        for index, volume in enumerate(volumes):
            if not isinstance(volume.field, str):
                continue
            match = match_hdf5_reference(volume.field)
            if not match:
                continue

            label = volume.label or volume.source_file or f'Orbital {index + 1}'
            orbitals.append(
                {
                    'id': volume.source_file or f'orbital-{index + 1}',
                    'orbitalIndex': int(volume.orbital_index)
                    if volume.orbital_index is not None
                    else None,
                    'label': label,
                    'energy': self._to_float(volume.energy, unit=ureg.electron_volt),
                    'occupation': self._to_float(volume.occupation),
                    'spin': volume.spin,
                    'symmetry': volume.symmetry,
                    'sourceFile': volume.source_file,
                    'gridOrigin': self._to_vector_list(
                        volume.grid_origin, unit=ureg.angstrom
                    ),
                    'gridVectors': self._to_vector_list(
                        volume.grid_vectors, unit=ureg.angstrom
                    ),
                    'gridShape': self._to_vector_list(volume.grid_shape),
                    'defaultIsovalue': self._to_float(volume.default_isovalue),
                    'volume': {
                        'uploadId': match.get('upload_id') or upload_id,
                        'file': match['file_id'] or entry_id,
                        'path': match['path'],
                    },
                }
            )

        orbitals.sort(
            key=lambda item: (
                item['orbitalIndex'] is None,
                item['orbitalIndex']
                if item['orbitalIndex'] is not None
                else item['id'],
                item['id'],
            )
        )

        if not orbitals:
            return None

        return {
            'orbitals': orbitals,
            'structure': structure,
            'structureContext': {
                'entryId': entry_id,
                'modelSystemPath': model_system.m_path() if model_system else None,
            },
            'displayOptions': {
                'showStructure': structure is not None,
                'showIsovalueSlider': True,
            },
        }

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        Infer `n_mo` / `n_ao` from supplied arrays when absent.
        """
        super().normalize(archive, logger)

        # ---------- infer n_mo ----------
        if self.n_mo is None:
            if isinstance(self.mo_coefficients, np.ndarray):
                self.n_mo = int(self.mo_coefficients.shape[0])
            elif self.orbital_volumes:
                self.n_mo = len(self.orbital_volumes)
            elif self.mo_spin is not None:
                self.n_mo = len(self.mo_spin)
            elif self.mo_energies is not None:
                self.n_mo = len(self.mo_energies)

        # ---------- infer n_ao ----------
        if self.n_ao is None and isinstance(self.mo_coefficients, np.ndarray):
            self.n_ao = int(self.mo_coefficients.shape[1])

        for orbital_volume in self.orbital_volumes or []:
            if orbital_volume.molecular_orbitals_ref is None:
                orbital_volume.molecular_orbitals_ref = self

        self.orbital_shape_viewer = self._build_viewer_payload(archive)
