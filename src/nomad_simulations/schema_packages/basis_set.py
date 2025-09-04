import itertools
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, Optional

from scipy import constants as const

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

import numpy as np
import pint
from nomad import utils
from nomad.datamodel.data import ArchiveSection
from nomad.metainfo import MEnum, Quantity, SubSection
from nomad.units import ureg

from nomad_simulations.schema_packages.atoms_state import AtomsState
from nomad_simulations.schema_packages.general import (
    check_normalized,
    set_not_normalized,
)
from nomad_simulations.schema_packages.model_method import BaseModelMethod
from nomad_simulations.schema_packages.numerical_settings import (
    KMesh,
    Mesh,
    NumericalSettings,
)

logger = utils.get_logger(__name__)


class BasisSetComponent(ArchiveSection):
    """A type section denoting a basis set component of a simulation.
    Should be used as a base section for more specialized sections.
    Allows for denoting the basis set's _scope_, i.e. to which entity it applies,
    e.g. atoms species, orbital type, Hamiltonian term.

    Examples include:
    - mesh-based basis sets, e.g. (projector-)(augmented) plane-wave basis sets
    - atom-centered basis sets, e.g. Gaussian-type basis sets, Slater-type orbitals, muffin-tin orbitals
    """

    # TODO check implementation of `BasisSetComponent` for Wannier and Slater-Koster orbitals

    name = Quantity(
        type=str,
        description="""
        Name of the basis set component.
        """,
    )

    species_scope = Quantity(
        type=AtomsState,
        shape=['*'],
        description="""
        Reference to the section `AtomsState` specifying the localization of the basis set.
        """,
    )

    # TODO: add atom index-based instantiator for species if not present

    hamiltonian_scope = Quantity(
        type=BaseModelMethod,
        shape=['*'],
        description="""
        Reference to the section `BaseModelMethod` containing the information
        of the Hamiltonian term to which the basis set applies.
        """,
    )

    # ? band_scope or orbital_scope: valence vs core

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)
        self.name = self.m_def.name


class PlaneWaveBasisSet(BasisSetComponent, KMesh):
    """
    Basis set over a reciprocal mesh, where each point $k_n$ represents a planar-wave basis function $\frac{1}{\\sqrt{\\omega}} e^{i k_n r}$.
    Typically the grid itself is cartesian with only points within a designated sphere considered.
    The cutoff radius may be defined by a reciprocal length, or more commonly, the equivalent kinetic energy for a free particle.

    * D. J. Singh and L. Nordström, \"Why Planewaves\" in Planewaves, pseudopotentials, and the LAPW method, 2nd ed. New York, NY: Springer, 2006, pp. 24-26.
    """

    cutoff_energy = Quantity(
        type=np.float64,
        unit='joule',
        description="""
        Cutoff energy for the plane-wave basis set.
        The simulation uses plane waves with energies below this cutoff.
        """,
    )

    cutoff_radius = Quantity(
        type=np.float64,
        unit='1/meter',
        description="""
        Cutoff radius for the plane-wave basis set.
        Is the less frequently used dual to `cutoff_energy`.
        """,
    )

    def compute_cutoff_radius(
        self, cutoff_energy: pint.Quantity | None
    ) -> pint.Quantity | None:
        """
        Compute the cutoff radius for the plane-wave basis set, expressed in reciprocal coordinates.
        """
        if cutoff_energy is None:
            return None
        m_e = const.m_e * ureg(const.unit('electron mass'))
        h = const.h * ureg(const.unit('Planck constant'))
        return np.sqrt(2 * m_e * cutoff_energy) / h

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        self.label = 'g-mesh'

        if self.cutoff_radius is None:
            cutoff_radius = self.compute_cutoff_radius(self.cutoff_energy)
            if cutoff_radius is None:
                logger.warning(
                    'Could not calculate `PlaneWaveBasisSet.cutoff_radius`: missing `cutoff_energy`.'
                )
            else:
                self.cutoff_radius = cutoff_radius


class APWPlaneWaveBasisSet(PlaneWaveBasisSet):
    """
    A `PlaneWaveBasisSet` specialized to the APW use case.
    Its main descriptors are defined in terms of the `MuffinTin` regions.
    """

    cutoff_fractional = Quantity(
        type=np.float64,
        shape=[],
        description="""
        The spherical cutoff parameter for the interstitial plane waves in the APW family.
        This cutoff has no units, referring to the product of the smallest muffin-tin radius
        and the length of the cutoff reciprocal vector ($r_{MT} * |K_{cut}|$).
        """,
    )

    def compute_cutoff_fractional(
        self, cutoff_radius: pint.Quantity | None, mt_r_min: pint.Quantity | None
    ) -> pint.Quantity | None:
        """
        Compute the fractional cutoff parameter for the interstitial plane waves in the LAPW family.

        Args:
        - cutoff_radius (Optional[pint.Quantity]): The cutoff radius.
        - mt_r_min (Optional[pint.Quantity]): The smallest muffin-tin radius within the `BasisSetContainer`.
        """
        reference_unit = 'angstrom'
        if cutoff_radius is None or mt_r_min is None:
            return None
        return cutoff_radius.to(f'1 / {reference_unit}') * mt_r_min.to(reference_unit)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mt_r_min = None

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)  # 1st compute `cutoff_radius``
        if self.cutoff_fractional is None:
            logger.warning(
                'Expected `APWPlaneWaveBasisSet.cutoff_fractional` to be defined. Will attempt to calculate.'
            )
            cutoff_fractional = self.compute_cutoff_fractional(
                self.cutoff_radius, self.mt_r_min
            )
            if cutoff_fractional is None:
                logger.warning(
                    'Could not calculate `APWPlaneWaveBasisSet.cutoff_fractional`: missing `cutoff_radius` or `mt_r_min`.'
                )
            else:
                self.cutoff_fractional = cutoff_fractional


class AtomCenteredFunction(ArchiveSection):
    """
    Specifies a single contracted basis function in an atom-centered basis set.

    In many quantum-chemistry codes, an atom-centered basis set is composed of
    several "shells," each shell containing one or more basis functions of a certain
    angular momentum. For instance, a shell of p-type orbitals (L=1) typically
    consists of 3 degenerate functions (p_x, p_y, p_z) if `harmonic_type='cartesian'`
    or 3 spherical harmonics if `harmonic_type='spherical'`.

    A single "atom-centered function" can be a linear combination of multiple
    primitive Gaussians (or Slater-type orbitals, STOs).
    In practice, these contract together to form the final basis function used by
    the SCF or post-SCF method. Often, each contraction is labeled by its
    angular momentum (e.g., s, p, d, f) and a set of exponents and coefficients.

    This class also accepts *combined* shells ('sp', 'spd', 'spdf') as input.
    On normalize(), it **expands** them into multiple single-ℓ shells and
    replaces itself with those shells in the parent's `functional_compositions`.

    **References**:
      - T. Helgaker, P. Jørgensen, J. Olsen, *Molecular Electronic-Structure Theory*, Wiley (2000).
      - F. Jensen, *Introduction to Computational Chemistry*, 2nd ed., Wiley (2007).
      - J. B. Foresman, Æ. Frisch, *Exploring Chemistry with Electronic Structure Methods*, Gaussian Inc.
    """

    harmonic_type = Quantity(
        type=MEnum('spherical', 'cartesian'),
        default='spherical',
        description='Angular basis used when expanding this shell into AOs.',
    )

    function_type = Quantity(
        type=MEnum(
            's', 'p', 'd', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'sp', 'spd', 'spdf'
        ),
        description='Angular-momentum label; combined variants are expanded into single-ℓ shells.',
    )

    # explicit single-ℓ metadata
    angular_momentum = Quantity(
        type=np.int32,
        description='Angular momentum quantum number ℓ.',
    )
    r_power = Quantity(
        type=np.int32, description="Radial power n_s for this shell's analytic form."
    )

    # per-shell normalization (contracted)
    shell_normalization = Quantity(
        type=np.float64, description='Per-shell normalization factor.'
    )

    # primitives
    n_primitive = Quantity(
        type=np.int32, description='Number of primitives in this shell.'
    )
    exponents = Quantity(
        type=np.float32, shape=['n_primitive'], description='Primitive exponents.'
    )
    contraction_coefficients = Quantity(
        type=np.float32,
        shape=['*'],
        description=(
            'Contraction coefficients. Single-ℓ: length == n_primitive. '
            'Combined input: length == n_components * n_primitive in the order '
            '[all s | all p | all d | (all f)].'
        ),
    )
    primitive_factor = Quantity(
        type=np.float64,
        shape=['n_primitive'],
        description='Extra per-primitive multiplier (dimensionless).',
    )

    # optional convention hint (provenance)
    primitive_normalization = Quantity(
        type=MEnum('L2', 'none', 'contracted', 'custom'),
        default='L2',
        description='Normalization convention hint for parsers.',
    )

    # optional embedded point charge
    point_charge = Quantity(
        type=np.float32, description='Optional embedded point charge.'
    )

    # helper (internal)
    n_components = Quantity(
        type=np.int32, description='Number of components implied by function_type.'
    )

    _L_MAP = {
        's': 0,
        'p': 1,
        'd': 2,
        'f': 3,
        'g': 4,
        'h': 5,
        'i': 6,
        'j': 7,
        'k': 8,
        'l': 9,
    }
    _COMBINED_ORDER = {
        'sp': ['s', 'p'],
        'spd': ['s', 'p', 'd'],
        'spdf': ['s', 'p', 'd', 'f'],
    }

    def _is_combined(self) -> bool:
        return self.function_type in self._COMBINED_ORDER

    def _expand_combined_into_parent(self) -> None:
        """
        Expand a combined shell into multiple single-ℓ shells by rewriting this
        instance in place to the first component and appending the rest to the
        parent's functional_compositions. Quiet no-op if parent/data missing.
        """
        parent = getattr(self, 'm_parent', None)
        if parent is None or not hasattr(parent, 'functional_compositions'):
            return
        if (
            self.n_primitive is None
            or self.exponents is None
            or self.contraction_coefficients is None
        ):
            return

        letters = self._COMBINED_ORDER[self.function_type]
        step = int(self.n_primitive)
        flat = np.asarray(self.contraction_coefficients, dtype=np.float32).ravel()
        expected = step * len(letters)

        # quietly fit to expected length (pad zeros / truncate)
        if flat.size < expected:
            flat = np.concatenate(
                [flat, np.zeros(expected - flat.size, dtype=np.float32)]
            )
        elif flat.size > expected:
            flat = flat[:expected]

        # ---- rewrite THIS instance to the first component ----
        first = letters[0]
        first_slice = flat[0:step]
        self.function_type = first
        self.angular_momentum = self._L_MAP.get(first)
        # keep n_primitive, exponents, primitive_factor, normalizations as-is
        self.contraction_coefficients = np.array(first_slice, dtype=np.float32)
        # n_components should now be single-ℓ
        self.n_components = 1

        # ---- append the remaining components as brand-new shells ----
        for i, ltr in enumerate(letters[1:], start=1):
            coeff_slice = flat[i * step : (i + 1) * step]
            new_shell = AtomCenteredFunction(
                harmonic_type=self.harmonic_type,
                function_type=ltr,
                angular_momentum=self._L_MAP.get(ltr),
                r_power=self.r_power,
                shell_normalization=self.shell_normalization,
                n_primitive=self.n_primitive,
                exponents=np.array(self.exponents, copy=True),
                contraction_coefficients=np.array(coeff_slice, copy=True),
                primitive_factor=(
                    np.array(self.primitive_factor, copy=True)
                    if self.primitive_factor is not None
                    else None
                ),
                primitive_normalization=self.primitive_normalization,
                point_charge=self.point_charge,
            )
            parent.functional_compositions.append(new_shell)

    @check_normalized
    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        # components implied by function_type
        self.n_components = (
            len(self._COMBINED_ORDER[self.function_type]) if self._is_combined() else 1
        )

        # expand combined shells and exit
        if self._is_combined():
            self._expand_combined_into_parent()
            return

        # single-ℓ mapping: set angular_momentum from function_type if missing
        if self.function_type in self._L_MAP and self.angular_momentum is None:
            self.angular_momentum = self._L_MAP[self.function_type]

        # infer n_primitive
        if self.exponents is not None and self.n_primitive is None:
            self.n_primitive = len(self.exponents)

        # fit lengths quietly (truncate/pad)
        if self.exponents is not None and self.n_primitive is not None:
            exp = np.asarray(self.exponents, dtype=np.float32).ravel()
            if exp.size < self.n_primitive:
                if exp.size == 0:
                    exp = np.zeros(self.n_primitive, dtype=np.float32)
                else:
                    exp = np.pad(exp, (0, self.n_primitive - exp.size), mode='edge')
            elif exp.size > self.n_primitive:
                exp = exp[: self.n_primitive]
            self.exponents = exp

        if self.n_primitive is not None:
            if self.contraction_coefficients is None:
                self.contraction_coefficients = np.zeros(
                    self.n_primitive, dtype=np.float32
                )
            else:
                cc = np.asarray(self.contraction_coefficients, dtype=np.float32).ravel()
                if cc.size < self.n_primitive:
                    cc = np.pad(cc, (0, self.n_primitive - cc.size), mode='constant')
                elif cc.size > self.n_primitive:
                    cc = cc[: self.n_primitive]
                self.contraction_coefficients = cc

            if self.primitive_factor is None:
                self.primitive_factor = np.ones(self.n_primitive, dtype=np.float64)
            else:
                pf = np.asarray(self.primitive_factor, dtype=np.float64).ravel()
                if pf.size < self.n_primitive:
                    pf = np.pad(
                        pf,
                        (0, self.n_primitive - pf.size),
                        mode='constant',
                        constant_values=1.0,
                    )
                elif pf.size > self.n_primitive:
                    pf = pf[: self.n_primitive]
                self.primitive_factor = pf

    @set_not_normalized
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class EffectiveCorePotential(BasisSetComponent):
    """
    TREXIO-style ECP storage:
      - Per-nucleus arrays: z_core[nucleus], max_ang_mom_plus_1[nucleus]
      - Flat list of projector items: size ecp_num with nucleus_index, ang_mom, exponent, coefficient, power
    """

    # Optional human label
    ecp_name = Quantity(type=str, description='ECP identifier or source label.')

    # --- Per-nucleus metadata (length should match number of nuclei addressed by this ECP set) ---
    z_core = Quantity(
        type=np.int32,
        shape=['*'],
        description='Core electrons replaced per nucleus (TREXIO: ecp.z_core[nucleus]).',
    )
    max_ang_mom_plus_1 = Quantity(
        type=np.int32,
        shape=['*'],
        description='ℓ_max + 1 per nucleus (TREXIO: ecp.max_ang_mom_plus_1[nucleus]).',
    )

    # --- Flat list of ECP projector items ---
    ecp_num = Quantity(
        type=np.int32,
        description='Number of ECP projector items (TREXIO: ecp.num).',
    )
    nucleus_index = Quantity(
        type=np.int32,
        shape=['ecp_num'],
        description='For each item: nucleus index it belongs to (TREXIO: ecp.nucleus_index[item]).',
    )
    ang_mom = Quantity(
        type=np.int32,
        shape=['ecp_num'],
        description='Angular momentum ℓ of each item (TREXIO: ecp.ang_mom[item]).',
    )
    exponent = Quantity(
        type=np.float64,
        shape=['ecp_num'],
        description='Gaussian exponent α per item (TREXIO: ecp.exponent[item], a.u.; convert on I/O).',
    )
    coefficient = Quantity(
        type=np.float64,
        shape=['ecp_num'],
        description='Coefficient c per item (TREXIO: ecp.coefficient[item], a.u.).',
    )
    power = Quantity(
        type=np.int32,
        shape=['ecp_num'],
        description='Radial power n per item (TREXIO: ecp.power[item]).',
    )

    @check_normalized
    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        # --- basic consistency for per-nucleus arrays ---
        if self.z_core is not None and self.max_ang_mom_plus_1 is not None:
            if len(self.z_core) != len(self.max_ang_mom_plus_1):
                logger.error(
                    'ECP per-nucleus arrays must have equal length: len(z_core) != len(max_ang_mom_plus_1).'
                )

        # --- ecp_num-driven arrays must match lengths ---
        if self.ecp_num is not None:
            for name in (
                'nucleus_index',
                'ang_mom',
                'exponent',
                'coefficient',
                'power',
            ):
                arr = getattr(self, name)
                if arr is None:
                    logger.error('ECP array is missing while ecp_num is set.')
                else:
                    if len(arr) != self.ecp_num:
                        logger.error(
                            "Length of ECP array '%s' (%d) must equal ecp_num (%d).",
                            name,
                            len(arr),
                            self.ecp_num,
                        )

        # --- optional human-readable name from species_scope, if present ---
        if self.species_scope:
            try:
                symbol = self.species_scope[0].chemical_symbol
                if not getattr(self, 'name', None):
                    self.name = f'ECP-{symbol}'
            except Exception:
                pass

    @set_not_normalized
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class AtomicOrbitals(ArchiveSection):
    """
    Expanded **atomic orbital (AO) layer** associated with a specific
    `AtomCenteredBasisSet`.

    While `AtomCenteredFunction` defines the *contracted shells* (basis
    functions before expansion), this section describes the actual AO
    functions that the code constructs from them. It captures the
    one-to-one mapping between the mathematical basis definition and the
    internal AO list used in SCF/post-SCF methods.

    Typical use cases:
      - Recording whether the code expanded shells in **Cartesian** or
        **spherical harmonic** form.
      - Tracking the **per-AO normalization factors** (to reconcile
        conventions across codes).
      - Providing an explicit **AO→shell mapping** for downstream
        population analysis, MO coefficients, or density matrices.
    """

    num = Quantity(type=np.int32, description='Total number of AOs (contracted).')
    cartesian = Quantity(type=bool, description='True=Cartesian, False=Spherical.')
    shell_index = Quantity(
        type=np.int32,
        shape=['num'],
        description="For each AO: index of AtomCenteredFunction (the 'shell') it belongs to.",
    )
    normalization = Quantity(
        type=np.float64,
        shape=['num'],
        description='Per-AO factor to reconcile code conventions.',
    )


class AtomCenteredBasisSet(BasisSetComponent):
    """
    Defines an **atom-centered basis set** for quantum chemistry calculations.
    Unlike plane-wave methods, these expansions are typically built around each atom's
    position, using either:
      - Slater-type orbitals (STO)
      - Gaussian-type orbitals (GTO)
      - Numerical atomic orbitals (NAO)
      - Effective-core potentials or point-charges (PC, cECP, etc.)

    This section references multiple `AtomCenteredFunction` objects, each describing
    a single contracted function or shell. Additionally, one can label the overall
    basis set name (e.g., "cc-pVTZ", "def2-SVP", "6-31G**") and specify the high-level
    role of the basis set in the calculation.

    **Common examples**:
      - **Pople basis** (3-21G, 6-31G(d), 6-311++G(2df,2pd), etc.)
      - **Dunning correlation-consistent** (cc-pVDZ, cc-pVTZ, aug-cc-pVTZ, etc.)
      - **Slater basis** used in ADF, for instance
      - **ECP** (Effective Core Potential) expansions like LANL2DZ or SDD for transition metals

    **References**:
      - F. Jensen, *Introduction to Computational Chemistry*, 2nd ed., Wiley (2007).
      - A. Szabo, N. S. Ostlund, *Modern Quantum Chemistry*, McGraw-Hill (1989).
      - T. H. Dunning Jr., J. Chem. Phys. 90, 1007 (1989) for correlation-consistent basis sets.
    """

    basis_set = Quantity(
        type=str,
        description="""
        **Name** or label of the basis set as recognized by the code or standard 
        library. Examples: "6-31G*", "cc-pVTZ", "def2-SVP", "STO-3G", "LANL2DZ" (ECP).
        """,
    )

    type = Quantity(
        type=MEnum(
            'STO',  # Slater-type orbitals
            'GTO',  # Gaussian-type orbitals
            'NAO',  # Numerical atomic orbitals
            'PC',  # Point charges
        ),
        description="""
        The **functional form** of the basis set:
          - 'STO': Slater-type orbitals
          - 'GTO': Gaussian-type orbitals
          - 'NAO': Numerical atomic orbitals
          - 'PC': Point charges (or ghost basis centers)

        If a code uses a mixture (e.g., GTO + ECP), store them as separate `AtomCenteredBasisSet` sections, 
        while referring to the relevant AtomsState.
        """,
    )

    role = Quantity(
        type=MEnum(
            'orbital',
            'auxiliary_scf',
            'auxiliary_post_hf',
            'cabs',
        ),
        description="""
        The role of this basis set in the calculation:
          - 'orbital': main orbital basis for the SCF
          - 'auxiliary_scf': used for RI-J or density fitting in SCF
          - 'auxiliary_post_hf': used in MP2, CC, etc. 
          - 'cabs': complementary auxiliary basis for explicitly correlated (F12) methods.
        """,
    )

    ao_ordering_convention = Quantity(
        type=MEnum(
            # the most frequently encountered conventions
            'Gaussian',  # (px, py, pz)  5D,7F,9G… as in Gaussian FChk
            'Molden',  # (pz, px, py)  and separate order for spherical
            'QChem',  # same as Gaussian for Cartesian; spherical ≠
            'TREXIO',  # explicit via ao.cartesian + see trexio docs
            'CP2K',  # CP2K/QuickStep (pz, px, py) by default
            'PySCF',  # follows libcint (px, py, pz) Cartesian
            'Custom',  # user‑defined; see `ao_custom_order`
        ),
        default='Gaussian',
        description="""
        **Ordering convention for the magnetic sub-functions** (Cartesian
        polynomials or spherical harmonics) within each angular-momentum shell.

        Examples for a *p* shell:

        | Convention | Cartesian order | Spherical order (m=0,+1,-1) |
        |------------|-----------------|------------------------------|
        | Gaussian   | (px, py, pz)    | (p₀, p₊₁, p₋₁)              |
        | Molden     | (pz, px, py)    | (p₀, p₊₁, p₋₁)              |
        | CP2K       | (pz, px, py)    | (p₀, p₊₁, p₋₁)              |

        If you select `'Custom'`, specify the explicit order for each ℓ ≥ 1
        in the optional field `ao_custom_order` below.  Otherwise parsers and
        writers will assume the canonical order embedded in the named
        convention.
        """,
    )

    ao_custom_order = Quantity(
        type=str,  # mapping: int ℓ  -> list[str] names
        description="""
        JSON-encoded mapping *ℓ → list-of-labels* that defines a user-specific
        AO ordering.  Only used when `ao_ordering_convention == "Custom"`.

        Example value::

            {"1": ["pz", "px", "py"],
            "2": ["d0", "d+1", "d-1", "d+2", "d-2"]}

        Parsers/writers should `json.loads(...)` this string.
        """,
    )

    total_number_of_basis_functions = Quantity(
        type=np.int32,
        description="""
        The **total** number of contracted basis functions in this entire set. 
        This is typically the sum of all `(2l+1)` or cartesian expansions across
        all shells on all relevant atoms (within the scope of this section).
        """,
    )

    functional_compositions = SubSection(
        sub_section=AtomCenteredFunction.m_def, repeats=True
    )

    atomic_orbitals = SubSection(
        sub_section=AtomicOrbitals.m_def,
        repeats=False,
        description='AO layer (cartesian flag, AO→shell map, per-AO normalization).',
    )

    ecps = SubSection(
        sub_section=EffectiveCorePotential.m_def,
        repeats=True,
        description='Zero or more ECP definitions replacing core electrons.',
    )

    @check_normalized
    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        # Set AO count from AO view if present
        if self.atomic_orbitals is not None and self.atomic_orbitals.num is not None:
            self.total_number_of_basis_functions = self.atomic_orbitals.num

            # Lightweight sanity checks (kept minimal to avoid verbosity)
            si = getattr(self.atomic_orbitals, 'shell_index', None)
            if si is not None and len(si) != self.atomic_orbitals.num:
                # leave silent; upstream parsers can correct/override
                pass
            norm = getattr(self.atomic_orbitals, 'normalization', None)
            if norm is not None and len(norm) != self.atomic_orbitals.num:
                pass
            if (
                self.functional_compositions is not None
                and si is not None
                and len(self.functional_compositions) > 0
            ):
                try:
                    max_idx = int(np.max(si)) if len(si) > 0 else -1
                    if max_idx >= len(self.functional_compositions):
                        pass
                except Exception:
                    pass

    @set_not_normalized
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class APWBaseOrbital(ArchiveSection):
    """
    Abstract base section for (S)(L)APW and local orbital component wavefunctions.
    It helps defining the interface with `APWLChannel`.
    """

    n_terms = Quantity(
        type=np.int32,
        description="""
        Number of terms in the local orbital.
        """,
    )

    energy_parameter = Quantity(
        type=np.float64,
        shape=['n_terms'],
        unit='joule',
        description="""
        Reference energy parameter for the augmented plane wave (APW) basis set.
        Is used to set the energy parameter for each state.
        """,
    )  # TODO: add approximation formula from energy parameter n

    energy_parameter_n = Quantity(
        type=np.int32,
        shape=['n_terms'],
        description="""
        Reference number of radial nodes for the augmented plane wave (APW) basis set.
        This is used to derive the `energy_parameter`.
        """,
    )

    energy_status = Quantity(
        type=MEnum('fixed', 'pre-optimization', 'post-optimization'),
        default='post-optimization',
        description="""
        Allow the code to optimize the initial energy parameter.
        """,
    )

    differential_order = Quantity(
        type=np.int32,
        shape=['n_terms'],
        description="""
        Derivative order of the radial wavefunction term.
        """,
    )  # TODO: add check non-negative # ? to remove

    def _get_open_quantities(self) -> set[str]:
        """Extract the open quantities of the `APWBaseOrbital`."""
        return {
            k for k, v in self.m_def.all_quantities.items() if self.m_get(v) is not None
        }

    def _get_lengths(self, quantities: set[str]) -> list[int]:
        """Extract the lengths of the `quantities` contained in the set."""
        present_quantities = set(quantities) & self._get_open_quantities()
        return [len(getattr(self, quant)) for quant in present_quantities]

    def _of_equal_length(self, lengths: list[int]) -> bool:
        """Check if all elements in the list are of equal length."""
        if len(lengths) == 0:
            return True
        else:
            ref_length = lengths[0]
            return all(length == ref_length for length in lengths)

    def get_n_terms(
        self,
        representative_quantities: set[str] = {
            'energy_parameter',
            'energy_parameter_n',
            'differential_order',
        },
    ) -> int | None:
        """Determine the value of `n_terms` based on the lengths of the representative quantities."""
        lengths = self._get_lengths(representative_quantities)
        if not self._of_equal_length(lengths) or len(lengths) == 0:
            return None
        else:
            return lengths[0]

    def _check_non_negative(self, quantity_names: set[str]) -> bool:
        """Check if all elements in the set are non-negative."""
        for quantity_name in quantity_names:
            if isinstance(quant := self.get(quantity_name), Iterable):
                if np.any(np.array(quant) <= 0):
                    return False
        return True

    @check_normalized
    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        # enforce quantity length (will be used for type assignment)
        new_n_terms = self.get_n_terms()
        if self.n_terms is None:
            self.n_terms = new_n_terms
        elif self.n_terms != new_n_terms:
            logger.error(
                f'Inconsistent lengths of `APWBaseOrbital` quantities: {self.m_def.quantities}. Setting back to `None`.'
            )
            self.n_terms = None

        # enforce differential order constraints
        for quantity_name in ('differential_order', 'energy_parameter_n'):
            if self._check_non_negative({quantity_name}):
                self.m_set(self.m_def.all_quantities[quantity_name], None)
                logger.error(
                    f'`{self.m_def}.{quantity_name}` must be completely non-negative. Resetting to `None`.'
                )

        # use the differential order as naming convention
        self.name = (
            'APW-like'
            if self.differential_order is None or len(self.differential_order) == 0
            else f'{sorted(self.differential_order)}'
        )

    @set_not_normalized
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # it's hard to enforce commutative diagrams between `_determine_apw` and `normalize`
        # instead, make all `_determine_apw` soft-coupled and dependent on the normalized state
        # leverage normalize ∘ normalize = normalize


class APWOrbital(APWBaseOrbital):
    """
    Implementation of `APWWavefunction` capturing the foundational (S)(L)APW basis sets, all of the form $\\sum_{lm} \\left[ \\sum_o c_{lmo} \frac{\\partial}{\\partial r}u_l(r, \\epsilon_l) \right] Y_lm$.
    The energy parameter $\\epsilon_l$ is always considered fixed during diagonalization, opposed to the original APW formulation.
    This representation then has to match the plane-wave $k_n$ points within the muffin-tin sphere.

    Its `name` is showcased as `(s)(l)apw: <differential order>`.

    * D. J. Singh and L. Nordström, \"INTRODUCTION TO THE LAPW METHOD,\" in Planewaves, pseudopotentials, and the LAPW method, 2nd ed. New York, NY: Springer, 2006, pp. 43-52.
    """

    type = Quantity(
        type=MEnum('apw', 'lapw', 'slapw'),  # ? add 'spherical_dirac'
        description=r"""
        Type of augmentation contribution. Abbreviations stand for:
        | name | description | radial product |
        |------|-------------|----------------|
        | APW  | augmented plane wave with parametrized energy levels | $A_{lm, k_n} u_l (r, E_l)$ |
        | LAPW | linearized augmented plane wave with an optimized energy parameter | $A_{lm, k_n} u_l (r, E_l) + B_{lm, k_n} \dot{u}_{lm} (r, E_l^')$ |
        | SLAPW | super linearized augmented plane wave | -- |

        * http://susi.theochem.tuwien.ac.at/lapw/
        """,
    )

    def do_to_type(self, do: list[int] | None) -> str | None:
        """
        Set the type of the APW orbital based on the differential order.
        """
        if do is None or len(do) == 0:
            return None

        do = sorted(do)
        if do == [0]:
            return 'apw'
        elif do == [0, 1]:
            return 'lapw'
        elif max(do) > 1:  # exciting definition
            return 'slapw'
        else:
            return None

    @check_normalized
    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)
        # assign a APW orbital type
        # this snippet works of the previous normalization
        new_type = self.do_to_type(self.differential_order)
        if self.type is None:
            self.type = new_type
        elif self.type != new_type:
            logger.error(
                f'Inconsistent `APWOrbital` type: {self.type}. Setting back to `None`.'
            )
            self.type = None

        self.name = (
            f'{self.type.upper()}: {self.name}'
            if self.type and len(self.differential_order) > 0
            else self.name
        )


class APWLocalOrbital(APWBaseOrbital):
    """
    Implementation of `APWWavefunction` capturing a local orbital extending a foundational APW basis set.
    Local orbitals allow for flexible additions to an `APWOrbital` specification.
    They may be included to describe semi-core states, virtual states, ghost bands, or improve overall convergence.

    * D. J. Singh and L. Nordström, \"Role of the Linearization Energies,\" in Planewaves, pseudopotentials, and the LAPW method, 2nd ed. New York, NY: Springer, 2006, pp. 49-52.
    """

    # there's no community consensus on `type`

    @check_normalized
    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)
        self.name = (
            f'LO: {sorted(self.differential_order)}'
            if self.differential_order
            else 'LO'
        )


class APWLChannel(BasisSetComponent):
    """
    Collection of all (S)(L)APW and local orbital components that contribute
    to a single $l$-channel. $l$ here stands for the angular momentum parameter
    in the Laplace spherical harmonics $Y_{l, m}$.
    """

    name = Quantity(
        type=np.int32,
        description="""
        Angular momentum quantum number of the local orbital.
        """,
    )

    n_orbitals = Quantity(
        type=np.int32,
        description="""
        Number of wavefunctions in the l-channel, i.e. $(2l + 1) n_orbitals$.
        """,
    )

    orbitals = SubSection(sub_section=APWBaseOrbital.m_def, repeats=True)

    def _determine_apw(self) -> dict[str, int]:
        """
        Produce a count of the APW components in the l-channel.
        Invokes `normalize` on `orbitals` to ensure the existence of `type`.
        """
        for orb in self.orbitals:
            orb.normalize(None, logger)

        type_count = {'apw': 0, 'lapw': 0, 'slapw': 0, 'lo': 0, 'other': 0}
        for orb in self.orbitals:
            if orb.type is None:
                type_count['other'] += 1
            elif isinstance(orb, APWOrbital) and orb.type.lower() in type_count.keys():
                type_count[orb.type] += 1
            elif isinstance(orb, APWLocalOrbital):
                type_count['lo'] += 1
            else:
                type_count['other'] += 1  # other de facto operates as a catch-all
        return type_count

    @set_not_normalized
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @check_normalized
    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        # call order: parent of `BasisSetComponent``, then `self`
        super(BasisSetComponent, self).normalize(archive, logger)
        self.n_orbitals = len(self.orbitals)


class MuffinTinRegion(BasisSetComponent, Mesh):
    """
    Muffin-tin region around atoms, containing the augmented part of the APW basis set.
    The latter is structured by l-channel. Each channel contains a base (S)(L)APW definition,
    which may be extended via local orbitals.
    """

    # there are 2 main ways of structuring the APW basis set
    # either as APW and lo in the MT region
    # or by l-channel in the MT region

    radius = Quantity(
        type=np.float64,
        unit='meter',
        description="""
        The radius descriptor of the `MuffinTin` is spherical shape.
        """,
    )

    l_max = Quantity(
        type=np.int32,
        description="""
        Maximum angular momentum quantum number that is sampled.
        Starts at 0.
        """,
    )

    l_channels = SubSection(sub_section=APWLChannel.m_def, repeats=True)

    def _determine_apw(self) -> dict[str, int]:
        """
        Aggregate the APW component count in the muffin-tin region.
        Invokes `normalize` on `l_channels`.
        """
        for l_channel in self.l_channels:
            l_channel.normalize(None, logger)

        type_count: dict[str, int] = {}
        if len(self.l_channels) > 0:
            # dynamically determine `type_count` structure
            for l_channel in self.l_channels:
                type_count.update(l_channel._determine_apw())
        return type_count

    @set_not_normalized
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mt_r_min = None

    @check_normalized
    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)
        # TODO: add spherical specification, once supported in `Grid`


class BasisSetContainer(NumericalSettings):
    """
    A section defining the full basis set used for representing the electronic structure
    during the diagonalization of a Hamiltonian (component), as defined in `ModelMethod`.
    This section may contain multiple basis set specifications under the basis_set_components,
    each with their own parameters.
    """

    native_tier = Quantity(
        type=str,  # to be overwritten by a parser `MEnum`
        description="""
        Code-specific tag indicating the overall precision based on the basis set parameters.
        The naming conventions of the same code are used. See the parser implementation for the possible values.
        The number of tiers varies, but a typical example would be `low`, `medium`, `high`.
        """,
    )  # TODO: rename to `code_specific_tier`

    # TODO: add reference to `electronic_structure`,
    # specifying to which electronic structure representation the basis set is applied
    # e.g. wavefunction, density, grids for subroutines, etc.

    basis_set_components = SubSection(sub_section=BasisSetComponent.m_def, repeats=True)

    def _determine_apw(self) -> str | None:
        """
        Derive the basis set name for a (S)(L)APW case, including local orbitals.
        Invokes `normalize` on `basis_set_components`.
        """
        has_plane_wave = (
            True
            if any(
                isinstance(comp, PlaneWaveBasisSet)
                for comp in self.basis_set_components
            )
            else False
        )

        type_sums: dict[str, int] = {}
        for comp in self.basis_set_components:
            if isinstance(comp, MuffinTinRegion):
                type_count = comp._determine_apw()
                for key in type_count.keys():
                    type_sums[key] = type_sums.get(key, 0) + type_count[key]

        type_str = 'APW-like'
        for key in ('slapw', 'lapw', 'apw'):
            try:
                if type_sums[key] > 0:
                    type_str = key.upper()
                    if type_sums['lo'] > 0:
                        type_str += '+lo'
                    break
            except KeyError:
                pass

        return type_str if has_plane_wave else None

    def _find_mt_r_min(self) -> pint.Quantity | None:
        """
        Scan the container for the smallest muffin-tin region.
        """
        mt_r_min = None
        for comp in self.basis_set_components:
            if isinstance(comp, MuffinTinRegion):
                if mt_r_min is None or comp.radius < mt_r_min:
                    mt_r_min = comp.radius
        return mt_r_min

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        mt_r_min = self._find_mt_r_min()
        plane_waves: list[APWPlaneWaveBasisSet] = []
        for component in self.basis_set_components:
            if isinstance(component, PlaneWaveBasisSet):
                plane_waves.append(component)
            elif isinstance(component, MuffinTinRegion):
                component.mt_r_min = mt_r_min
                component.normalize(archive, logger)
            elif isinstance(component, AtomCenteredBasisSet):
                component.normalize(archive, logger)
            elif isinstance(component, EffectiveCorePotential):
                component.normalize(archive, logger)

        if len(plane_waves) == 0:
            logger.error('Expected a `APWPlaneWaveBasisSet` instance, but found none.')
        elif len(plane_waves) > 1:
            logger.warning('Multiple plane-wave basis sets found were found.')
        self.name = self._determine_apw()


def generate_apw(
    species: dict[str, dict[str, Any]],
    cutoff: float | None = None,
) -> BasisSetContainer:  # TODO: extend to cover all parsing use cases (maybe split up?)
    """
    Generate a mock APW basis set with the following structure:
    .
    ├── 1 x plane-wave basis set
    └── n x muffin-tin regions
        └── l_max x l-channels
            ├── orbitals
            └── local orbitals

    from a dictionary
    {
    <species_name>: {
            'r': <muffin-tin radius>,
            'l_max': <maximum angular momentum>,
            'orb_do': [[int]],
            'orb_param': [<APWOrbital.energy_parameter>],
            'lo_do': [[int]],
            'lo_param': [<APWOrbital.energy_parameter>],
        }
    }
    """

    basis_set_components: list[BasisSetComponent] = []
    if cutoff is not None:
        pw = APWPlaneWaveBasisSet(cutoff_energy=cutoff)
        basis_set_components.append(pw)

    for sp_ref, sp in species.items():
        sp['r'] = sp.get('r', None)
        sp['l_max'] = sp.get('l_max', 0)
        sp['orb_d_o'] = sp.get('orb_d_o', [])
        sp['orb_param'] = sp.get('orb_param', [])
        sp['lo_d_o'] = sp.get('lo_d_o', [])
        sp['lo_param'] = sp.get('lo_param', [])

        basis_set_components.extend(
            [
                MuffinTinRegion(
                    species_scope=[sp_ref],
                    radius=sp['r'],
                    l_max=sp['l_max'],
                    l_channels=[
                        APWLChannel(
                            name=l_channel,
                            orbitals=list(
                                itertools.chain(
                                    (
                                        APWOrbital(
                                            energy_parameter=param,  # TODO: add energy_parameter_n
                                            differential_order=d_o,
                                        )
                                        for param, d_o in zip(
                                            sp['orb_param'], sp['orb_d_o']
                                        )
                                    ),
                                    (
                                        APWLocalOrbital(
                                            energy_parameter=param,  # TODO: add energy_parameter_n
                                            differential_order=d_o,
                                        )
                                        for param, d_o in zip(
                                            sp['lo_param'], sp['lo_d_o']
                                        )
                                    ),
                                )
                            ),
                        )
                        for l_channel in range(sp['l_max'] + 1)
                    ],
                )
            ]
        )

    return BasisSetContainer(basis_set_components=basis_set_components)
