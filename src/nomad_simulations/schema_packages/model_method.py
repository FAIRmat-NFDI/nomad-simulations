import re
from typing import TYPE_CHECKING

import numpy as np
from nomad.datamodel.data import ArchiveSection
from nomad.metainfo import URL, MEnum, Quantity, Section, SubSection

if TYPE_CHECKING:
    from nomad.datamodel.context import Context
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.atoms_state import CoreHole, ElectronicState
from nomad_simulations.schema_packages.data_types import unit_float
from nomad_simulations.schema_packages.model_system import ModelSystem
from nomad_simulations.schema_packages.numerical_settings import NumericalSettings
from nomad_simulations.schema_packages.utils.libxc.build import (
    spec_from_label,
)
from nomad_simulations.schema_packages.utils.libxc.expand import (
    expand_to_libxc_labels,
)


class BaseModelMethod(ArchiveSection):
    """
    A base section used to define the abstract class of a Hamiltonian section. This section is an
    abstraction of the `ModelMethod` section, which contains the settings and parameters used in
    the mathematical model solved in a simulation. This abstraction is needed in order to allow
    `ModelMethod` to be divided into specific `terms`, so that the total Hamiltonian is specified in
    `ModelMethod`, while its contributions are defined in `ModelMethod.terms`.

    Example: a custom model Hamiltonian containing two terms:
        $H = H_{V_{1}(r)}+H_{V_{2}(r)}$
    where $H_{V_{1}(r)}$ and $H_{V_{2}(r)}$ are the contributions of two different potentials written in
    real space coordinates $r$. These potentials could be defined in terms of a combination of parameters
    $(a_{1}, b_{1}, c_{1}...)$ for $V_{1}(r)$ and $(a_{2}, b_{2}, c_{2}...)$ for $V_{2}(r)$. If we name the
    total Hamiltonian as `'FF1'`:
        `ModelMethod.name = 'FF1'`
        `ModelMethod.contributions = [BaseModelMethod(name='V1', parameters=[a1, b1, c1]), BaseModelMethod(name='V2', parameters=[a2, b2, c2])]`

    Note: quantities such as `name`, `type`, `external_reference` should be descriptive enough so that the
    total Hamiltonian model or each of the terms or contributions can be identified.
    """

    normalizer_level = 1

    name = Quantity(
        type=str,
        description="""
        Name of the mathematical model. This is typically used to identify the model Hamiltonian used in the
        simulation. Typical standard names: 'DFT', 'TB', 'GW', 'BSE', 'DMFT', 'NMR', 'kMC'.
        """,
    )

    type = Quantity(
        type=str,
        description="""
        Identifier used to further specify the kind or sub-type of model Hamiltonian. Example: a TB
        model can be 'Wannier', 'DFTB', 'xTB' or 'Slater-Koster'. This quantity should be
        rewritten to a MEnum when inheriting from this class.
        """,
    )

    external_reference = Quantity(
        type=URL,
        description="""
        External reference to the model e.g. DOI, URL.
        """,
    )

    numerical_settings = SubSection(sub_section=NumericalSettings.m_def, repeats=True)


class ModelMethod(BaseModelMethod):
    """
    A base section containing the mathematical model parameters. These are both the parameters of
    the model and the settings used in the simulation. Optionally, this section can be decomposed
    in a series of contributions by storing them under the `contributions` quantity.
    """

    contributions = SubSection(
        sub_section=BaseModelMethod.m_def,
        repeats=True,
        description="""
        Contribution or sub-term of the total model Hamiltonian.
        """,
    )


class ImplicitSolvationModel(BaseModelMethod):
    """Implicit-solvent or polarizable continuum treatments.

    Examples include PCM and its variants (IEF-PCM, CPCM), COSMO, COSMO-RS,
    SMD, GBSA, and Poisson-Boltzmann (PB) models.  The essential parameters
    are the dielectric constant **ε** of the solvent, a description of how
    the cavity is constructed, and optional surface-charge or
    dispersion terms used by the model.

    References
    ----------
    •  J. Tomasi, B. Mennucci, R. Cammi, *Chem. Rev.* **105**, 2999 (2005) — PCM overview
    •  A. Klamt, *J. Phys. Chem.* **99**, 2224 (1995) — COSMO
    •  A. V. Marenich *et al.*, *J. Chem. Phys. B* **113**, 6378 (2009) — SMD
    """

    model = Quantity(
        type=MEnum(
            # Quantum-chemistry continuum
            'PCM',
            'IEF-PCM',
            'CPCM',
            'DCOSMO',
            'COSMO',
            'COSMO-RS',
            'SMD',  # SMx family represented by SMD here
            # Electrostatics continuum
            'PB',
            'GB',
            'GBSA',
            # Solid-state / modern continua
            'SCCS',
        ),
        description="""
        The implicit-solvent flavour employed.

        | Abbrev. | Full name                              |
        |---------|----------------------------------------|
        | PCM     | Polarizable Continuum Model            |
        | IEF-PCM | Integral Equation Formalism PCM        |
        | CPCM    | Conductor-like PCM                     |
        | SMD     | Solvation Model based on Density       |
        | COSMO   | COnductor-like Screening MOdel         |
        | COSMO-RS| COSMO for Real Solvents                |
        | GBSA    | Generalised Born Surface Area          |
        | PB      | Poisson-Boltzmann                      |
        """,
    )

    solvent = Quantity(
        type=str,
        description="""
        Common name or formula of the solvent (e.g. water, acetonitrile).
        """,
    )

    dielectric_constant = Quantity(
        type=np.float64,
        description="""
        Static relative permittivity (ε) of the bulk solvent. (ε at ω=0)
        Required for PCM/COSMO/GBSA; may be implicit in SMD parameter sets.
        """,
    )

    dielectric_constant_optical = Quantity(
        type=np.float64,
        description="""
        Optical-frequency (high-frequency) dielectric ε_∞ of the solvent.
        Used in TDDFT/non-equilibrium PCM. Often derived from n via ε_∞ ≈ n².
        """,
    )

    is_mixture = Quantity(
        type=bool,
        description='True if a solvent mixture was modeled (COSMO-RS/JDFT contexts).',
    )

    refractive_index = Quantity(
        type=np.float64,
        description="""
        Optical-frequency refractive index *n* of the solvent.  Needed when a
        frequency-dependent dielectric is used (e.g. in TDDFT PCM).
        If provided and `dielectric_constant_optical` is missing, normalization sets
        dielectric_constant_optical = n**2.
        """,
    )

    cavity_construction = Quantity(
        type=MEnum('UFF', 'VdW', 'ISOSURFACE', 'SAS', 'FIXED_RADIUS', 'other'),
        description="""
        How the solute cavity surface is defined.
          • *UFF* / *VdW* : scaled van-der-Waals radii (default for PCM)
          • *ISOSURFACE*  : electron-density isosurface (IEFPCM/SMD)
          • *SAS*         : solvent-accessible surface
          • *FIXED_RADIUS*: single-sphere (GBSA)
        """,
    )

    # TODO: revisit here after the final Mesh implementation
    surface_tessellation = Quantity(
        type=np.int32,
        shape=['*'],
        description="""
        Number of Lebedev/Geodesic points per atom used in the cavity
        discretisation (relevant for surface-integral PCM codes).

        Semantics:
        • Single value → global default applied to all atoms.
        • Length == n_species → per-species values (ordered like the model's species list).
        • Length == n_atoms → per-atom values (in atomic order).

        Many codes expose a global setting but internally vary with element; this
        shape allows parsers to emit either a single global value or an explicit
        vector when the input/output is species- or atom-resolved.
        """,
    )

    #  minimal PB/GB knobs for classical comparability
    epsilon_interior = Quantity(
        type=np.float64,
        description='Interior (solute) dielectric ε_in; GB/PB often use ε_in > 1. Default is 1.0 if missing.',
    )

    ionic_strength = Quantity(
        type=np.float64,
        unit='mole / liter',
        description='Bulk ionic strength (salt) for PB; optional for GB parameterizations.',
    )

    # GB/GBSA per-atom Born radii
    born_radii_system_ref = Quantity(
        type=ModelSystem,
        description="""
        ModelSystem whose particle ordering the Born radii refer to. If omitted,
        normalization should default to the last representative ModelSystem.
        """,
    )

    # Local count specifically for this array (avoids clashing with ModelSystem.n_particles)
    n_born = Quantity(
        type=np.int32,
        description='Number of Born radii provided (length of effective_born_radii).',
    )

    effective_born_radii = Quantity(
        type=np.float64,
        unit='meter',
        shape=['n_born'],
        description="""
        Per-particle effective Born radii R_i^Born used by GB/GBSA electrostatics.
        Units match the code's length unit; ordering defined by born_radii_system_ref
        plus optional born_radii_particle_indices.
        """,
    )

    born_radii_particle_indices = Quantity(
        type=np.int32,
        shape=['n_born'],
        description="""
        Optional indices into born_radii_system_ref's particle list. If omitted, a 1:1
        mapping to that system's particle ordering is assumed.
        """,
    )

    def normalize(self, archive, logger):
        super().normalize(archive, logger)

        # --- derive ε∞ from n (when needed) ---
        if (
            self.dielectric_constant_optical is None
            and self.refractive_index is not None
        ):
            try:
                self.dielectric_constant_optical = float(self.refractive_index) ** 2
            except Exception:
                logger.warning(
                    'Failed to derive dielectric_constant_optical from refractive_index.'
                )

        # --- light validation by model type ---
        if (
            self.model in ['PCM', 'IEF-PCM', 'CPCM', 'DCOSMO', 'COSMO', 'GB', 'GBSA']
            and self.dielectric_constant is None
        ):
            logger.warning(
                'ImplicitSolvationModel.model requires static dielectric_constant (ε_s), but it is missing.'
            )


class ExplicitDispersionModel(BaseModelMethod):
    """Explicit dispersion / vdW treatment used together with an ab-initio method.

    Covers pairwise-additive (D2/D3/D3(BJ)/D4), density-dependent (TS/TS-SCS),
    many-body dispersion (MBD, e.g. MBD@rsSCS), and non-local correlation
    functionals (VV10, rVV10, vdW-DF family, XDM). Records key numerical knobs
    (s6/s8/s9, BJ a1/a2, VV10 b, MBD beta, TS sR).

    References
    ----------
    •  S. Grimme, *J. Comp. Chem.* **27**, 1787 (2006) — DFT-D2
    •  S. Grimme *et al.*, *J. Chem. Phys.* **132**, 154104 (2010) — DFT-D3
    •  S. Grimme *et al.*, *J. Chem. Phys.* **136**, 154105 (2012) — DFT-D3(BJ)
    •  C. Steinmann, *WIREs Comput. Mol. Sci.* **10**, e1438 (2020) — overview
    """

    model = Quantity(
        type=MEnum(
            # Pairwise / density-dependent
            'D2',
            'D3',
            'D3BJ',
            'D4',
            'OBS',
            'JCHS',
            'TS',
            'TS-SCS',
            # Many-body
            'MBD',
            'MBD@rsSCS',
            # Exchange-hole based
            'XDM',
            # Non-local correlation functionals
            'VV10',
            'rVV10',
            'vdW-DF',
            'vdW-DF2',
            'optB88-vdW',
            'optB86b-vdW',
            'SCAN+rVV10',
            'BEEF-vdW',
        ),
        description='Dispersion/vdW scheme.',
    )

    # application context
    is_embedded_in_xc = Quantity(
        type=bool,
        description='True if dispersion is part of the XC functional (e.g. SCAN+rVV10).',
    )

    # Damping form
    damping_function = Quantity(
        type=MEnum('zero', 'BJ', 'fermi', 'rational'),
        description='Short-range damping: D3{zero,BJ}, TS{fermi}, XDM{rational}.',
    )

    # TODO @ EBB: link this to XCComponent(s) when available
    xc_partner = Quantity(
        type=str,
        description="Base XC functional used/tuned for (e.g. 'PBE', 'SCAN', 'B3LYP').",
    )

    # Core scalar knobs (only some are relevant for each model)
    s6 = Quantity(type=np.float64, description='Global s6 scaling for C6/R6.')
    s8 = Quantity(type=np.float64, description='Global s8 scaling for C8/R8 (D3/D4).')
    s9 = Quantity(
        type=np.float64, description='Global s9 for 3-body ATM term (if enabled).'
    )
    a1 = Quantity(type=np.float64, description='BJ damping a1 (D3BJ/D4).')
    a2 = Quantity(type=np.float64, description='BJ damping a2 (D3BJ/D4).')
    sR = Quantity(type=np.float64, description='Range/damping length for TS/TS-SCS.')
    b = Quantity(type=np.float64, description='VV10/rVV10 kernel parameter b.')
    beta = Quantity(
        type=np.float64, description='MBD range-separation / screening parameter.'
    )

    # Method-specific switches
    include_three_body_atm = Quantity(
        type=bool,
        description='If a 3-body Axilrod-Teller-Muto term is included (D3/D4).',
    )
    include_c8 = Quantity(
        type=bool, description='If C8 term is included in the pairwise sum.'
    )
    include_c10 = Quantity(type=bool, description='If C10 term is included (e.g. XDM).')
    max_dispersion_order = Quantity(
        type=np.int32, description='Highest n in Cn/R^n used (e.g., 6, 8, 10).'
    )

    # Environment/charges for density-dependent schemes
    partition_scheme = Quantity(
        type=MEnum('Hirshfeld', 'Hirshfeld-I', 'MBIS'),
        description='Density partition for TS/MBD polarizabilities.',
    )
    charge_model = Quantity(
        type=MEnum('EEQ', 'CM5', 'NPA'),
        description='Atomic charge model used by D4 (e.g., EEQ).',
    )

    # Kernel flavor (vdW-DF family)
    nonlocal_kernel = Quantity(
        type=MEnum('DRSLL', 'LMKLL', 'VV10', 'rVV10'),
        description='Nonlocal correlation kernel flavor (when applicable).',
    )

    # Density source for TS/MBD
    density_source = Quantity(
        type=MEnum('all-electron', 'PAW-reconstructed', 'valence-only'),
        description='Source of electron density used for Hirshfeld/MBIS partitioning.',
    )

    # Practical cutoffs
    cutoff_radius = Quantity(
        type=np.float64,
        unit='meter',
        description='Pairwise/MBD real-space cutoff (if any).',
    )


class RelativityModel(BaseModelMethod):
    """
    Relativistic treatment of the valence Hamiltonian.
    This does not describe core-electron approximations (PP/ECP).

    Typical options
    --------------
    * Four-component Dirac-Coulomb (DC)
    * Two-component X2C / DKH / ZORA
    * Spin-orbit mean-field (SOMF) for post-HF/BSE
    """

    level = Quantity(
        type=MEnum(
            'non-relativistic',
            'scalar',
            'two-component',
            'four-component',
        ),
        default='non-relativistic',
        description="""
        Non-relativistic (Schrödinger), scalar (spin-free),
        two-component (spin-orbit couple removed variationally, e.g. X2C),
        or four-component Dirac treatment.
        """,
    )

    approximation = Quantity(
        type=MEnum(
            'DKH',
            'ZORA',
            'FORA',
            'IORA',
            'X2C',
            'BSS',
            'NESC',
            'Pauli',
            'SOMF',
        ),
        description="""
        Specific approximation or decoupling scheme.
          • DKH  : Douglas-Kroll-Hess (all orders)
          • ZORA : Zeroth-order regular approximation      
          • FORA  : First-order regular approximation
          • IORA  : Improved regular approximation
          • X2C  : Exact two-component
          • BSS  : Barysz-Sadlej-Snijders
          • NESC: Normalized elimination of the small component (Dyall)
          • Pauli: Pauli spin-orbit correction
          • SOMF : Spin-orbit mean-field added after SCF
        """,
    )

    dkh_order = Quantity(
        type=np.int32,
        description='Order used for DKH (e.g., 2, 4, ...).',
    )


class OrbitalLocalization(BaseModelMethod):
    """Transforming canonical MOs into a localized representation.

    Localized orbitals are used by local correlation methods such as
    LMP2, DLPNO-CCSD(T), fragment charge analyses, and qualitative bonding pictures.
    The transformation is (near) unitary and does not change the total energy by itself,
    it merely changes the representation.

    References:
        - S. F. Boys, "Construction of Some Molecular Orbitals to Be Approximately Invariant for Changes from One Molecule to Another," Rev. Mod. Phys. 32, 296 (1960). https://doi.org/10.1103/RevModPhys.32.296
        - J. Pipek and P. G. Mezey, "A fast intrinsic localization procedure applicable for ab initio and semiempirical linear combination of atomic orbital wave functions," J. Chem. Phys. 90, 4916 (1989). https://doi.org/10.1063/1.456588
        - C. Edmiston and K. Ruedenberg, "Localized Atomic and Molecular Orbitals," Rev. Mod. Phys. 35, 457 (1963). https://doi.org/10.1103/RevModPhys.35.457
        - G. Knizia, "Intrinsic Atomic Orbitals: An Unbiased Bridge between Quantum Theory and Chemical Concepts," J. Chem. Theory Comput. 9, 4834 (2013). https://doi.org/10.1021/ct400687b
        - F. Weinhold, C. R. Landis, "Natural bond orbitals and extensions of localized bonding concepts," Chem. Educ. Res. Pract. 2, 91 (2001). https://doi.org/10.1039/B1RP90011K

    """

    method = Quantity(
        type=MEnum(
            'Foster-Boys',
            'Pipek-Mezey',
            'Edmiston-Ruedenberg',
            'IBO',
            'NBO',
            'AIOPM-NBO',
        ),
        description="""Localization criterion / algorithm.""",
    )

    n_localized_orbitals = Quantity(
        type=np.int32,
        description='Number of orbitals actually subjected to the localization (can differ from the full occupied space).',
    )


class ModelMethodElectronic(ModelMethod):
    """
    A base section used to define the parameters of a model Hamiltonian used in electronic structure
    calculations (TB, DFT, GW, BSE, DMFT, etc).
    """

    # ? Is this necessary or will it be defined in another way?
    # TODO @ndaelman-hu & EBB2675, we need to assess how to reconcile is_spin_polarized and determinant
    is_spin_polarized = Quantity(
        type=bool,
        description="""
        If the simulation is done considering the spin degrees of freedom (then there are two spin
        channels, 'down' and 'up') or not.
        """,
    )
    # TODO : this part should be revisited once Spin is handled.
    # TODO : this part should be revisited in general.
    determinant = Quantity(
        type=MEnum('unrestricted', 'restricted', 'restricted-open-shell'),
        description="""
        The spin-coupling form of the determinant used for the
        self-consistent field (SCF) calculation.

        - **restricted**  (RHF/RKS): α and β electrons share the same spatial orbitals  
        - **unrestricted** (UHF/UKS): α and β orbitals are optimized independently  
        - **restricted-open-shell** (ROHF/ROKS): closed-shell core with spin-unpaired electrons
        sharing spatial orbitals in the open-shell manifold
        """,
    )


class XCComponent(ArchiveSection):
    """
    One exchange-correlation functional component using LibXC nomenclature for standardization.

    Note: LibXC IDs and labels are used to provide a unified taxonomy across different codes,
    but do not necessarily indicate that the LibXC library was used in the calculation.
    Check `XCFunctional.uses_libxc` to determine the actual implementation source.

    All taxonomy data are extracted from the LibXC registry; hybrid parameters (α/ω) are
    set by parsers when present in inputs/outputs.

    LibXC project page: https://libxc.gitlab.io/
    """

    # Identity (from LibXC registry)
    libxc_id = Quantity(type=np.int64, description='LibXC ID (e.g., 101).')
    canonical_label = Quantity(
        type=str, description="LibXC label, e.g. 'XC_GGA_X_PBE'."
    )
    display_name = Quantity(type=str, description='Human-readable name, e.g. B3LYP.')

    # Taxonomy
    family = Quantity(
        type=MEnum('LDA', 'GGA', 'meta-GGA', 'hybrid-GGA', 'hybrid-meta-GGA'),
        description="Jacob's ladder family.",
    )
    kind = Quantity(
        type=MEnum('exchange', 'correlation', 'xc', 'k'), description='Component kind.'
    )

    # Hybrid / range-separated parameters — PARSERS fill these if known
    # TODO: normalize with defaults if not provided
    fraction_exact_exchange = Quantity(type=np.float64, description='HF mixing α.')

    range_part = Quantity(
        type=MEnum('global', 'short-range', 'long-range'),
        description="""
        Range domain this component applies to:
        'global' (no split), 'short-range', or 'long-range'.
        """,
    )

    range_separation_parameter = Quantity(
        type=np.float64, unit='1/m', description='Range separation ω.'
    )

    range_separation_function = Quantity(
        type=MEnum('erf', 'erfc', 'Yukawa', 'exp', 'Gaussian', 'Slater'),
        description="""
        Functional form of the range-separation kernel used to partition the Coulomb operator.

        Common choices:
        • erf     — error function (used in LC-ωPBE, CAM-B3LYP)
        • erfc    — complementary error function (equivalent to erf split)
        • Yukawa  — exponential screening, e.g. HSE-style
        • exp     — simple exponential decay
        • Gaussian — Gaussian screening form
        • Slater  — Slater-type exponential

        Needed to interpret the range-separation parameter ω correctly.
        """,
    )

    weight = Quantity(
        type=unit_float(),
        description="""
            Fractional contribution in the density functional result.
            Only applies when the functional is part of a larger, composed functional, that is not included in the LibXC.
            All components' fractions should sum up to one.
         """,
    )


class XCFunctional(ArchiveSection):
    """
    Normalized XC information for a calculation (possibly multi-component).

    The `components` subsection uses LibXC nomenclature to provide standardized
    taxonomy and metadata across different simulation codes. This standardization
    does not imply that the LibXC library was actually used in the calculation.

    To determine whether the simulation code used its internal XC implementation
    or explicitly called the LibXC library, check the `uses_libxc` quantity.
    """

    components = SubSection(sub_section=XCComponent.m_def, repeats=True)

    functional_key = Quantity(
        type=str,
        description="""
        Canonical functional alias representing one XC functional as a whole.
        Used for filtering and display (e.g. 'PBE', 'PBE0', 'B3LYP', 'SCAN+rVV10').
        Typically corresponds to the original name reported in the code,
        """,
    )

    # moved & renamed from DFT.exact_exchange_mixing_factor
    global_exact_exchange = Quantity(
        type=np.float64,
        description='Global HF mixing α (if any); derived from XC components.',
    )

    uses_libxc = Quantity(
        type=bool,
        default=False,
        description="""
        `True` if the calculation explicitly used the LibXC library for XC functional evaluation.
        Has to be set by the parser. `False` indicates the code used its own internal implementation.
        """,
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        try:
            if not self.components and self.functional_key:
                labels = expand_to_libxc_labels(self.functional_key)
                if labels:
                    # de-duplicate while preserving order
                    seen = set()
                    for lbl in labels:
                        if lbl in seen:
                            continue
                        seen.add(lbl)

                        spec = spec_from_label(lbl, weight=1.0)
                        if spec is not None:
                            comp = XCComponent(**spec)
                            self.m_add_sub_section(type(self).components, comp)
                else:
                    logger.debug(
                        'LibXC expansion produced no labels.',
                        raw=self.functional_key,
                    )
        except Exception:
            logger.warning('LibXC expansion failed.')

        if self.global_exact_exchange is None:
            alphas = [
                c.fraction_exact_exchange
                for c in (self.components or [])
                if c.fraction_exact_exchange is not None
            ]
            if len(alphas) == 1 or (len(alphas) > 1 and len(set(alphas)) == 1):
                self.global_exact_exchange = alphas[0]


class DFT(ModelMethodElectronic):
    """
    A base section used to define the parameters used in a density functional theory (DFT) calculation.
    """

    # TODO : improve and rename this classification
    jacobs_ladder = Quantity(
        type=MEnum(
            'LDA', 'GGA', 'meta-GGA', 'hybrid-GGA', 'hybrid-meta-GGA', 'unavailable'
        ),
        description="""
        Highest Jacob's ladder rung present among XC components.
        See:
            - https://doi.org/10.1063/1.1390175 (original paper)
            - https://doi.org/10.1103/PhysRevLett.91.146401 (meta-GGA)
            - https://doi.org/10.1063/1.1904565 (hyper-GGA)
        """,
    )

    xc = SubSection(sub_section=XCFunctional.m_def, repeats=False)

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        if self.xc is None:
            self.xc = XCFunctional()

        # XC-specific normalization now handled by XCFunctional
        self.xc.normalize(archive, logger)

        # Derive Jacob’s ladder from components (highest rung wins)
        rank = {
            'LDA': 0,
            'GGA': 1,
            'meta-GGA': 2,
            'hybrid-GGA': 3,
            'hybrid-meta-GGA': 4,
        }
        families = [c.family for c in (self.xc.components or []) if c.family]
        if families:
            self.jacobs_ladder = max(families, key=lambda f: rank.get(f, -1))
        else:
            self.jacobs_ladder = self.jacobs_ladder or 'unavailable'


class TB(ModelMethodElectronic):
    """
    A base section containing the parameters pertaining to a tight-binding (TB) model calculation.
    The type of tight-binding model is specified in the `type` quantity.
    """

    type = Quantity(
        type=MEnum('DFTB', 'xTB', 'Wannier', 'SlaterKoster', 'unavailable'),
        default='unavailable',
        description="""
        Tight-binding model Hamiltonian type. The default is set to `'unavailable'` in case none of the
        standard types can be recognized. These can be:

        | Value | Reference |
        | --------- | ----------------------- |
        | `'DFTB'` | https://en.wikipedia.org/wiki/DFTB |
        | `'xTB'` | https://xtb-docs.readthedocs.io/en/latest/ |
        | `'Wannier'` | https://www.wanniertools.org/theory/tight-binding-model/ |
        | `'SlaterKoster'` | https://journals.aps.org/pr/abstract/10.1103/PhysRev.94.1498 |
        | `'unavailable'` | - |
        """,
    )

    # ? these 4 quantities will change when `BasisSet` is defined
    n_orbitals_per_atom = Quantity(
        type=np.int32,
        description="""
        Number of orbitals per atom in the unit cell used as a basis to obtain the `TB` model. This
        quantity is resolved from `orbitals_ref` via normalization.
        """,
    )

    n_atoms_per_unit_cell = Quantity(
        type=np.int32,
        description="""
        Number of atoms per unit cell relevant for the `TB` model. This quantity is resolved from
        `n_total_orbitals` and `n_orbitals_per_atom` via normalization.
        """,
    )

    n_total_orbitals = Quantity(
        type=np.int32,
        description="""
        Total number of orbitals used as a basis to obtain the `TB` model. This quantity is parsed by
        the specific parsing code. This is related with `n_orbitals_per_atom` and `n_atoms_per_unit_cell` as:
            `n_total_orbitals` = `n_orbitals_per_atom` * `n_atoms_per_unit_cell`
        """,
    )

    orbitals_ref = Quantity(
        type=ElectronicState,
        shape=['n_orbitals_per_atom'],
        description="""
        References to the `ElectronicState` that contain system's the orbitals (with a mapping to each atom) relevant for the `TB` model. This quantity is resolved from normalization when the active atoms sub-systems `model_system.model_system[*]`
        are populated.

        The relevant orbitals for the TB model are the `'pz'` ones for each `'C'` atom. Then, we define:

            `orbitals_ref= [ElectronicState('pz'), ElectronicState('pz')]`

        The relevant atoms information can be accessed from the parent AtomsState sections:

            ```
                atom_state = orbitals_ref[i].m_parent
                index = orbitals_ref[i].m_parent_index
                atom_position = orbitals_ref[i].m_parent.m_parent.positions[index]
            ```
        """,
    )

    def resolve_type(self) -> str | None:
        """
        Resolves the `type` of the `TB` section if it is not already defined, and from the
        `m_def.name` of the section.

        Returns:
            str | None: The resolved `type` of the `TB` section.
        """
        return (
            self.m_def.name
            if self.m_def.name in ['DFTB', 'xTB', 'Wannier', 'SlaterKoster']
            else None
        )

    def resolve_orbital_references(
        self,
        model_systems: list[ModelSystem],
        logger: 'BoundLogger',
        model_index: int = -1,
    ) -> list[ElectronicState] | None:
        """
        Resolves references to the `ElectronicState` sections from the top-level `ModelSystem`
        that has child system(s) typed 'active_atom'. This uses the new design:

        - The parent ModelSystem stores per-atom data in `particle_states`.
        - The child system(s) typed 'active_atom' list indices in `particle_indices`.
        - We gather `ElectronicState` from each relevant particle_states entry.

        Args:
            model_systems (list[ModelSystem]): The list of `ModelSystem` sections.
            logger (BoundLogger): The logger to log messages.
            model_index (int, optional): The ModelSystem index to use. Defaults to -1 (the last).

        Returns:
            `list[ElectronicState] | None`: The resolved references to the `ElectronicState` sections.
        """
        # Check that the requested ModelSystem exists
        try:
            model_system = model_systems[model_index]
        except IndexError:
            logger.warning('No ModelSystem at index %s.', model_index)
            return None

        # If the system is not representative, bail out of normalization
        if not model_system.is_representative:
            return None

        # If no child ModelSystem sections exist, bail out of normalization
        if not model_system.sub_systems:
            logger.warning(
                'No child ModelSystem found; cannot find active_atom references.'
            )
            return None

        #  If no particle_states are present at the top level, we have no orbitals
        if not model_system.particle_states:
            logger.warning('No particle_states in the parent ModelSystem.')
            return None

        orbitals_ref: list[ElectronicState] = []

        # For each child in sub_systems, if type='active_atom', gather orbitals
        for child_sys in model_system.sub_systems:
            if child_sys.type != 'active_atom':
                continue
            # if no particle_indices => skip
            # Note: Use 'is None' and len check to avoid numpy array boolean evaluation issues
            # (numpy array [0] evaluates to False in boolean context)
            if (
                child_sys.particle_indices is None
                or len(child_sys.particle_indices) == 0
            ):
                logger.warning('Child system is active_atom but no particle_indices.')
                continue

            # For each index in child_sys.particle_indices => fetch from parent’s particle_states
            for idx in child_sys.particle_indices:
                if idx < 0 or idx >= len(model_system.particle_states):
                    logger.warning(
                        'Particle index %s out of range for particle_states.', idx
                    )
                    continue
                active_atom_state = model_system.particle_states[idx]

                # If no orbitals_state => skip
                if not active_atom_state.electronic_state:
                    logger.warning(
                        'No electronic_state found in particle_states[%s].', idx
                    )
                    continue

                orbitals_ref.append(active_atom_state.electronic_state)

        # Return the collected orbitals
        return orbitals_ref

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        # Set `name` to "TB"
        self.name = 'TB'

        # Resolve `type` to be defined by the lower level class (Wannier, DFTB, xTB or SlaterKoster) if it is not already defined
        self.type = self.resolve_type()

        # Resolve `orbitals_ref` from the info in the child `ModelSystem` section and the `ElectronicState` sections
        model_systems = self.m_xpath('m_parent.model_system', dict=False)
        if model_systems is None:
            logger.warning(
                'Could not find the `ModelSystem` sections. References to `ElectronicState` will not be resolved.'
            )
            return
        # This normalization only considers the last `ModelSystem` (default `model_index` argument set to -1)
        orbitals_ref = self.resolve_orbital_references(
            model_systems=model_systems, logger=logger
        )
        if orbitals_ref is not None and len(orbitals_ref) > 0 and not self.orbitals_ref:
            self.n_orbitals_per_atom = len(orbitals_ref)
            self.orbitals_ref = orbitals_ref

        # Resolve `n_atoms_per_unit_cell` from `n_total_orbitals` and `n_orbitals_per_atom`
        if self.n_orbitals_per_atom is not None and self.n_total_orbitals is not None:
            self.n_atoms_per_unit_cell = (
                self.n_total_orbitals // self.n_orbitals_per_atom
            )


class Wannier(TB):
    """
    A base section used to define the parameters used in a Wannier tight-binding fitting.
    """

    is_maximally_localized = Quantity(
        type=bool,
        description="""
        If the projected orbitals are maximally localized or just a single-shot projection.
        """,
    )

    localization_type = Quantity(
        type=MEnum('single_shot', 'maximally_localized'),
        description="""
        Localization type of the Wannier orbitals.
        """,
    )

    n_bloch_bands = Quantity(
        type=np.int32,
        description="""
        Number of input Bloch bands to calculate the projection matrix.
        """,
    )

    energy_window_outer = Quantity(
        type=np.float64,
        unit='electron_volt',
        shape=[2],
        description="""
        Bottom and top of the outer energy window used for the projection.
        """,
    )

    energy_window_inner = Quantity(
        type=np.float64,
        unit='electron_volt',
        shape=[2],
        description="""
        Bottom and top of the inner energy window used for the projection.
        """,
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        # Resolve `localization_type` from `is_maximally_localized`
        if self.localization_type is None:
            if self.is_maximally_localized is not None:
                if self.is_maximally_localized:
                    self.localization_type = 'maximally_localized'
                else:
                    self.localization_type = 'single_shot'


class SlaterKosterBond(ArchiveSection):
    """
    A base section used to define the Slater-Koster bond information betwee two orbitals.
    """

    orbital_1 = Quantity(
        type=ElectronicState,
        description="""
        Reference to the first `ElectronicState` section.
        """,
    )

    orbital_2 = Quantity(
        type=ElectronicState,
        description="""
        Reference to the second `ElectronicState` section.
        """,
    )

    # ? is this the best naming
    bravais_vector = Quantity(
        type=np.int32,
        default=[0, 0, 0],
        shape=[3],
        description="""
        The Bravais vector of the cell in 3 dimensional. This is defined as the vector that connects the
        two atoms that define the Slater-Koster bond. A bond can be defined between orbitals in the
        same unit cell (bravais_vector = [0, 0, 0]) or in neighboring cells (bravais_vector = [m, n, p] with m, n, p are integers).
        Default is [0, 0, 0].
        """,
    )

    # TODO add more names and in the table
    name = Quantity(
        type=MEnum('sss', 'sps', 'sds'),
        description="""
        The name of the Slater-Koster bond. The name is composed by the `l_quantum_symbol` of the orbitals
        and the cell index. Table of possible values:

        | Value   | `orbital_1.l_quantum_symbol` | `orbital_2.l_quantum_symbol` | `bravais_vector` |
        | ------- | ---------------------------- | ---------------------------- | ------------ |
        | `'sss'` | 's' | 's' | [0, 0, 0] |
        | `'sps'` | 's' | 'p' | [0, 0, 0] |
        | `'sds'` | 's' | 'd' | [0, 0, 0] |
        """,
    )

    # ? units
    integral_value = Quantity(
        type=np.float64,
        description="""
        The Slater-Koster bond integral value.
        """,
    )

    def __init__(self, m_def: 'Section' = None, m_context: 'Context' = None, **kwargs):
        super().__init__(m_def, m_context, **kwargs)
        # TODO extend this to cover all bond names
        self._bond_name_map = {
            'sss': ['s', 's', (0, 0, 0)],
            'sps': ['s', 'p', (0, 0, 0)],
            'sds': ['s', 'd', (0, 0, 0)],
        }

    def resolve_bond_name_from_references(
        self,
        orbital_1: ElectronicState | None,
        orbital_2: ElectronicState | None,
        bravais_vector: tuple | None,
        logger: 'BoundLogger',
    ) -> str | None:
        """
        Resolves the `name` of the `SlaterKosterBond` from the references to the `ElectronicState` sections.

        Args:
            orbital_1 (`ElectronicState | None`): The first `ElectronicState` section.
            orbital_2 (`ElectronicState | None`): The second `ElectronicState` section.
            bravais_vector (`tuple | None`): The bravais vector of the cell.
            logger (`BoundLogger`): The logger to log messages.

        Returns:
            `[str] | None`: The resolved `name` of the `SlaterKosterBond`.
        """
        # Initial check
        if orbital_1 is None or orbital_2 is None:
            logger.warning('The `ElectronicState` sections are not defined.')
            return None
        if bravais_vector is None:
            logger.warning('The `bravais_vector` is not defined.')
            return None

        # Check for `l_quantum_symbol` in `ElectronicState` sections
        orbital_1_l_symbol = (
            getattr(orbital_1.spin_orbit_state, 'l_quantum_symbol', None)
            if orbital_1.spin_orbit_state
            else None
        )
        orbital_2_l_symbol = (
            getattr(orbital_2.spin_orbit_state, 'l_quantum_symbol', None)
            if orbital_2.spin_orbit_state
            else None
        )

        if orbital_1_l_symbol is None or orbital_2_l_symbol is None:
            logger.warning(
                'The `l_quantum_symbol` of the `ElectronicState` bonds are not defined.'
            )
            return None

        bond_name = None
        value = [orbital_1_l_symbol, orbital_2_l_symbol, bravais_vector]
        # Check if `value` is found in the `self._bond_name_map` and return the key
        for key, val in self._bond_name_map.items():
            if val == value:
                bond_name = key
                break
        return bond_name

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        # Resolve the SK bond `name` from the `ElectronicState` references and the `bravais_vector`
        if self.orbital_1 and self.orbital_2 and self.bravais_vector is not None:
            if self.bravais_vector is not None:
                bravais_vector = tuple(self.bravais_vector)  # transformed for comparing
            self.name = self.resolve_bond_name_from_references(
                orbital_1=self.orbital_1,
                orbital_2=self.orbital_2,
                bravais_vector=bravais_vector,
                logger=logger,
            )


class SlaterKoster(TB):
    """
    A base section used to define the parameters used in a Slater-Koster tight-binding fitting.
    """

    bonds = SubSection(sub_section=SlaterKosterBond.m_def, repeats=True)

    overlaps = SubSection(sub_section=SlaterKosterBond.m_def, repeats=True)

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)


class xTB(TB):
    """
    A base section used to define the parameters used in an extended tight-binding (xTB) calculation.
    """

    # ? Deprecate this

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)


class Photon(ArchiveSection):
    """
    A base section used to define parameters of a photon, typically used for optical responses.
    """

    # TODO check other options and add specific refs
    multipole_type = Quantity(
        type=MEnum('dipolar', 'quadrupolar', 'NRIXS', 'Raman'),
        description="""
        Type used for the multipolar expansion: dipole, quadrupole, NRIXS, Raman, etc.
        """,
    )

    polarization = Quantity(
        type=np.float64,
        shape=[3],
        description="""
        Direction of the photon polarization in cartesian coordinates.
        """,
    )

    energy = Quantity(
        type=np.float64,
        unit='joule',
        description="""
        Photon energy.
        """,
    )

    momentum_transfer = Quantity(
        type=np.float64,
        shape=[3],
        description="""
        Momentum transfer to the lattice. This quanitity is important for inelastic scatterings, like
        the ones happening in quadrupolar, Raman, or NRIXS processes.
        """,
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        # Add warning in case `multipole_type` and `momentum_transfer` are not consistent
        if (
            self.multipole_type in ['quadrupolar', 'NRIXS', 'Raman']
            and self.momentum_transfer is None
        ):
            logger.warning(
                'The `Photon.momentum_transfer` is not defined but the `Photon.multipole_type` describes inelastic scattering processes.'
            )


class ExcitedStateMethodology(ModelMethodElectronic):
    """
    A base section used to define the parameters typical of excited-state calculations. "ExcitedStateMethodology"
    mainly refers to methodologies which consider many-body effects as a perturbation of the original
    DFT Hamiltonian. These are: GW, TDDFT, BSE.
    """  # Note: we don't really talk about Hamiltonians in DFT: their physics is accommodated in the functional itself

    n_states = Quantity(
        type=np.int32,
        description="""
        Number of states used to calculate the excitations.
        """,
    )

    n_empty_states = Quantity(
        type=np.int32,
        description="""
        Number of empty states used to calculate the excitations. This quantity is complementary to `n_states`.
        """,
    )

    broadening = Quantity(
        type=np.float64,
        unit='joule',
        description="""
        Lifetime broadening applied to the spectra in full-width at half maximum for excited-state calculations.
        """,
    )


class Screening(ExcitedStateMethodology):
    """
    A base section used to define the parameters that define the calculation of screening. This is usually done in
    RPA and linear response.
    """

    dielectric_infinity = Quantity(
        type=np.int32,
        description="""
        Value of the static dielectric constant at infinite q. For metals, this is infinite
        (or a very large value), while for insulators is finite.
        """,
    )


class GW(ExcitedStateMethodology):
    """
    A base section used to define the parameters of a GW calculation.
    """

    type = Quantity(
        type=MEnum(
            'G0W0',
            'scGW',
            'scGW0',
            'scG0W',
            'ev-scGW0',
            'ev-scGW',
            'qp-scGW0',
            'qp-scGW',
        ),
        description="""
        GW Hedin's self-consistency cycle:

        | Name      | Description                      | Reference             |
        | --------- | -------------------------------- | --------------------- |
        | `'G0W0'`  | single-shot                      | https://journals.aps.org/prb/abstract/10.1103/PhysRevB.74.035101 |
        | `'scGW'`  | self-consistent G and W               | https://journals.aps.org/prb/abstract/10.1103/PhysRevB.75.235102 |
        | `'scGW0'` | self-consistent G with fixed W0  | https://journals.aps.org/prb/abstract/10.1103/PhysRevB.54.8411 |
        | `'scG0W'` | self-consistent W with fixed G0  | -                     |
        | `'ev-scGW0'`  | eigenvalues self-consistent G with fixed W0   | https://journals.aps.org/prb/abstract/10.1103/PhysRevB.34.5390 |
        | `'ev-scGW'`  | eigenvalues self-consistent G and W   | https://journals.aps.org/prb/abstract/10.1103/PhysRevB.74.045102 |
        | `'qp-scGW0'`  | quasiparticle self-consistent G with fixed W0 | https://journals.aps.org/prb/abstract/10.1103/PhysRevB.76.115109 |
        | `'qp-scGW'`  | quasiparticle self-consistent G and W | https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.96.226402 |
        """,
    )

    analytical_continuation = Quantity(
        type=MEnum(
            'pade',
            'contour_deformation',
            'ppm_GodbyNeeds',
            'ppm_HybertsenLouie',
            'ppm_vonderLindenHorsh',
            'ppm_FaridEngel',
            'multi_pole',
        ),
        description="""
        Analytical continuation approximations of the GW self-energy:

        | Name           | Description         | Reference                        |
        | -------------- | ------------------- | -------------------------------- |
        | `'pade'` | Pade's approximant  | https://link.springer.com/article/10.1007/BF00655090 |
        | `'contour_deformation'` | Contour deformation | https://journals.aps.org/prb/abstract/10.1103/PhysRevB.67.155208 |
        | `'ppm_GodbyNeeds'` | Godby-Needs plasmon-pole model | https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.62.1169 |
        | `'ppm_HybertsenLouie'` | Hybertsen and Louie plasmon-pole model | https://journals.aps.org/prb/abstract/10.1103/PhysRevB.34.5390 |
        | `'ppm_vonderLindenHorsh'` | von der Linden and P. Horsh plasmon-pole model | https://journals.aps.org/prb/abstract/10.1103/PhysRevB.37.8351 |
        | `'ppm_FaridEngel'` | Farid and Engel plasmon-pole model  | https://journals.aps.org/prb/abstract/10.1103/PhysRevB.47.15931 |
        | `'multi_pole'` | Multi-pole fitting  | https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.74.1827 |
        """,
    )

    # TODO improve description
    interval_qp_corrections = Quantity(
        type=np.int32,
        shape=[2],
        description="""
        Band indices (in an interval) for which the GW quasiparticle corrections are calculated.
        """,
    )

    screening_ref = Quantity(
        type=Screening,
        description="""
        Reference to the `Screening` section that the GW calculation used to obtain the screened Coulomb interactions.
        """,
    )


class BSE(ExcitedStateMethodology):
    """
    A base section used to define the parameters of a BSE calculation.
    """

    # ? does RPA relates with `screening_ref`?
    type = Quantity(
        type=MEnum('Singlet', 'Triplet', 'IP', 'RPA'),
        description="""
        Type of the BSE Hamiltonian solved:

            H_BSE = H_diagonal + 2 * gx * Hx - gc * Hc

        Online resources for the theory:
        - http://exciting.wikidot.com/carbon-excited-states-from-bse#toc1
        - https://www.vasp.at/wiki/index.php/Bethe-Salpeter-equations_calculations
        - https://docs.abinit.org/theory/bse/
        - https://www.yambo-code.eu/wiki/index.php/Bethe-Salpeter_kernel

        | Name | Description |
        | --------- | ----------------------- |
        | `'Singlet'` | gx = 1, gc = 1 |
        | `'Triplet'` | gx = 0, gc = 1 |
        | `'IP'` | Independent-particle approach |
        | `'RPA'` | Random Phase Approximation |
        """,
    )

    solver = Quantity(
        type=MEnum('Full-diagonalization', 'Lanczos-Haydock', 'GMRES', 'SLEPc', 'TDA'),
        description="""
        Solver algotithm used to diagonalize the BSE Hamiltonian.

        | Name | Description | Reference |
        | --------- | ----------------------- | ----------- |
        | `'Full-diagonalization'` | Full diagonalization of the BSE Hamiltonian | - |
        | `'Lanczos-Haydock'` | Subspace iterative Lanczos-Haydock algorithm | https://doi.org/10.1103/PhysRevB.59.5441 |
        | `'GMRES'` | Generalized minimal residual method | https://doi.org/10.1137/0907058 |
        | `'SLEPc'` | Scalable Library for Eigenvalue Problem Computations | https://slepc.upv.es/ |
        | `'TDA'` | Tamm-Dancoff approximation | https://doi.org/10.1016/S0009-2614(99)01149-5 |
        """,
    )

    screening_ref = Quantity(
        type=Screening,
        description="""
        Reference to the `Screening` section that the BSE calculation used to obtain the screened Coulomb interactions.
        """,
    )


class TDDFT(ExcitedStateMethodology):
    """
    Time-dependent density functional theory settings. Captures both linear-response
    and real-time propagation flavours.

    References
    ----------
    • E. Runge, E. K. U. Gross, Phys. Rev. Lett. 52, 997 (1984)  (TDDFT formalism)
    • M. A. L. Marques et al. (eds.), *Fundamentals of Time-Dependent Density Functional Theory*,
      Springer (2012)
    • A. Castro et al., Phys. Status Solidi B 243, 2465 (2006)  (Real-time TDDFT overview)
    """

    type = Quantity(
        type=MEnum('linear_response', 'real_time'),
        default='linear_response',
        description="""
        TDDFT flavour (linear-response or real-time propagation).
          • linear_response — frequency-domain (Casida, Sternheimer, Liouville-Lanczos)
          • real_time       — explicit time propagation under a perturbation.
        """,
    )

    kernel = Quantity(
        type=MEnum(
            'ALDA',
            'AGGA',
            'hybrid',
            'range_separated',
            'frequency_dependent',
            'bootstrap',
            'long_range_corrected',
        ),
        description="""
        This field describes the effective XC response behaviour assumed in the TDDFT calculation, 
        whether implemented explicitly (linear-response) or implicitly via the XC potential (real-time).
          • ALDA / AGGA     : adiabatic local or semi-local
          • hybrid          : hybrid adiabatic kernel
          • range_separated : long/short-range split hybrids
          • frequency_dependent : non-adiabatic kernel
          • bootstrap / long_range_corrected : common nano/solid-state kernels
        """,
    )

    is_tamm_dancoff = Quantity(
        type=bool,
        description='If True, Tamm-Dancoff approximation (TDA) is used (linear-response only).',
    )

    solver = Quantity(
        type=MEnum(
            'Casida', 'Sternheimer', 'Liouville-Lanczos', 'propagation', 'unavailable'
        ),
        description="""
        Numerical driver:
          • Casida             : eigenvalue problem in particle-hole space
          • Sternheimer        : frequency-domain Sternheimer
          • Liouville-Lanczos  : iterative Liouville-Lanczos
          • propagation        : explicit time evolution (real-time)
          • unavailable        : code-chosen / unspecified
        """,
    )

    xc_kernel_ref = Quantity(
        type=XCFunctional,
        description="""
        Reference to an `XCFunctional` describing the TDDFT kernel.
        Typically points to the ground-state DFT XC section if the adiabatic
        kernel matches, or to a separate XCFunctional created for the TD kernel
        when it differs (e.g., LRC/hybrid kernel on top of semi-local ground state).
        """,
    )

    field_polarization_ref = Quantity(
        type=Photon,
        description='External field / polarization used to drive the response or propagation.',
    )

    target_property = Quantity(
        type=MEnum('absorption', 'emission', 'EELS', 'Raman', 'nonlinear'),
        description='Intended spectral/response target of the TDDFT input.',
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        self.name = 'TDDFT'

        # Soft warnings to help parsers spot missing essentials
        if self.type == 'real_time' and (
            self.time_step is None or self.n_steps is None
        ):
            logger.warning(
                'TDDFT real_time mode without time_step or n_steps may be incomplete.'
            )
        if self.type == 'linear_response' and self.is_tamm_dancoff is None:
            logger.warning(
                'TDDFT linear_response set but is_tamm_dancoff not specified.'
            )


# ? Is this class really necessary or should go in outputs.py?
class CoreHoleSpectra(ModelMethodElectronic):
    """
    A base section used to define the parameters used in a core-hole spectra calculation. This
    also contains reference to the specific methodological section (DFT, BSE) used to obtain the core-hole spectra.
    """

    m_def = Section(a_eln={'hide': ['type']})

    # # TODO add examples
    # solver = Quantity(
    #     type=str,
    #     description="""
    #     Solver algorithm used for the core-hole spectra.
    #     """,
    # )

    type = Quantity(
        type=MEnum('absorption', 'emission'),
        description="""
        Type of the CoreHole excitation spectra calculated, either "absorption" or "emission".
        """,
    )

    edge = Quantity(
        type=MEnum(
            'K',
            'L1',
            'L2',
            'L3',
            'L23',
            'M1',
            'M2',
            'M3',
            'M23',
            'M4',
            'M5',
            'M45',
            'N1',
            'N2',
            'N3',
            'N23',
            'N4',
            'N5',
            'N45',
        ),
        description="""
        Edge label of the excited core-hole. This is obtained by normalization by using `core_hole_ref`.
        """,
    )

    core_hole_ref = Quantity(
        type=CoreHole,
        description="""
        Reference to the `CoreHole` section that contains the information of the edge of the excited core-hole.
        """,
    )

    excited_state_method_ref = Quantity(
        type=ModelMethodElectronic,
        description="""
        Reference to the `ModelMethodElectronic` section (e.g., `DFT` or `BSE`) that was used to obtain the core-hole spectra.
        """,
    )

    # TODO add normalization to obtain `edge`


class DMFT(ModelMethodElectronic):
    """
    A base section used to define the parameters of a DMFT calculation.
    """

    m_def = Section(a_eln={'hide': ['type']})

    impurity_solver = Quantity(
        type=MEnum(
            'CT-INT',
            'CT-HYB',
            'CT-AUX',
            'ED',
            'NRG',
            'MPS',
            'IPT',
            'NCA',
            'OCA',
            'slave_bosons',
            'hubbard_I',
        ),
        description="""
        Impurity solver method used in the DMFT loop:

        | Name              | Reference                            |
        | ----------------- | ------------------------------------ |
        | `'CT-INT'`        | https://link.springer.com/article/10.1134/1.1800216 |
        | `'CT-HYB'`        | https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.97.076405 |
        | `'CT-AUX'`        | https://iopscience.iop.org/article/10.1209/0295-5075/82/57003 |
        | `'ED'`            | https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.72.1545 |
        | `'NRG'`           | https://journals.aps.org/rmp/abstract/10.1103/RevModPhys.80.395 |
        | `'MPS'`           | https://journals.aps.org/prb/abstract/10.1103/PhysRevB.90.045144 |
        | `'IPT'`           | https://journals.aps.org/prb/abstract/10.1103/PhysRevB.45.6479 |
        | `'NCA'`           | https://journals.aps.org/prb/abstract/10.1103/PhysRevB.47.3553 |
        | `'OCA'`           | https://journals.aps.org/prb/abstract/10.1103/PhysRevB.47.3553 |
        | `'slave_bosons'`  | https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.57.1362 |
        | `'hubbard_I'`     | https://iopscience.iop.org/article/10.1088/0953-8984/24/7/075604 |
        """,
    )

    n_impurities = Quantity(
        type=np.int32,
        description="""
        Number of impurities mapped from the correlated atoms in the unit cell. This defines whether
        the DMFT calculation is done in a single-impurity or multi-impurity run.
        """,
    )

    n_orbitals = Quantity(
        type=np.int32,
        shape=['n_impurities'],
        description="""
        Number of correlated orbitals per impurity.
        """,
    )

    orbitals_ref = Quantity(
        type=ElectronicState,
        shape=['n_orbitals'],
        description="""
        References to the `ElectronicState` sections that contain the orbitals information which are
        relevant for the `DMFT` calculation.

        Example: hydrogenated graphene with 3 atoms in the unit cell. The full list of `AtomsState` would
        be
            [
                AtomsState(chemical_symbol='C', electronic_state=ElectronicState(basis_orbitals=[SphericalSymmetryState('s'), SphericalSymmetryState('px'), SphericalSymmetryState('py'), SphericalSymmetryState('pz')])),
                AtomsState(chemical_symbol='C', electronic_state=ElectronicState(basis_orbitals=[SphericalSymmetryState('s'), SphericalSymmetryState('px'), SphericalSymmetryState('py'), SphericalSymmetryState('pz')])),
                AtomsState(chemical_symbol='H', electronic_state=ElectronicState(basis_orbitals=[SphericalSymmetryState('s')])),
            ]

        The relevant orbitals for the TB model are the `'pz'` ones for each `'C'` atom. Then, we define:

            orbitals_ref = [ElectronicState('pz'), ElectronicState('pz')]

        The relevant impurities information can be accesed from the parent AtomsState sections:
            impurity_state = orbitals_ref[i].m_parent
            index = orbitals_ref[i].m_parent_index
            impurity_position = orbitals_ref[i].m_parent.m_parent.positions[index]
        """,
    )

    # ? Improve this with `orbitals_ref.occupation` and possibly a function?
    n_electrons = Quantity(
        type=np.float64,
        shape=['n_impurities'],
        description="""
        Initial number of valence electrons per impurity.
        """,
    )

    inverse_temperature = Quantity(
        type=np.float64,
        unit='1/joule',
        description="""
        Inverse temperature = 1/(kB*T).
        """,
    )

    # ? Check this once magnetic states are better covered in the schema. This will be probably under `ModelSystem`
    # ? by checking the spins in `AtomsState` for the `AtomicCell`
    # ! Check solid_dmft example by using magmom (atomic magnetic moments), and improve on AtomsState to include such moments
    magnetic_state = Quantity(
        type=MEnum('paramagnetic', 'ferromagnetic', 'antiferromagnetic'),
        description="""
        Magnetic state in which the DMFT calculation is done. This quantity can be obtained from
        `orbitals_ref` and their spin state.
        """,
    )


class HartreeFock(ModelMethodElectronic):
    """
    Defines a Hartree-Fock (HF) calculation.

    In HF theory:
      - RHF  = Restricted Hartree-Fock, for closed-shell systems.
      - UHF  = Unrestricted Hartree-Fock, allows different orbitals for alpha/beta spin.
      - ROHF = Restricted Open-Shell Hartree-Fock, a partially restricted approach for
               open-shell systems.

    **References**:
      - Roothaan, C. C. J. (1951). "New Developments in Molecular Orbital Theory."
        Rev. Mod. Phys. 23, 69.
      - Szabo, A., & Ostlund, N. S. (1989). *Modern Quantum Chemistry*. McGraw-Hill.
      - Jensen, F. (2007). *Introduction to Computational Chemistry*. 2nd ed., Wiley.
    """

    type = Quantity(
        type=MEnum('RHF', 'UHF', 'ROHF'),
        description="""
        The type of HF determinant.
        """,
    )


class PerturbationMethod(ModelMethodElectronic):
    type = Quantity(
        type=MEnum('MP', 'RS', 'BW'),
        default='MP',
        description="""
        Perturbation approach. The abbreviations stand for:
        | Abbreviation | Description |
        | ------------ | ----------- |
        | `'MP'`       | Møller-Plesset |
        | `'RS'`       | Rayleigh-Schrödinger |
        | `'BW'`       | Brillouin-Wigner |
        """,
    )

    order = Quantity(
        type=np.int32,
        description="""
        Order up to which the perturbation is expanded.
        """,
    )

    density = Quantity(
        type=MEnum('relaxed', 'unrelaxed'),
        description="""
        unrelaxed density: no orbital-response terms.
        relaxed density  : incorporates orbital relaxation.
        """,
    )

    # TODO : later on, the details about custom scaling factors will be added
    spin_component_scaling = Quantity(
        type=MEnum('SCS', 'SOS', 'custom'),
        description="""
        Spin-component scaling approach for perturbation methods:
          - SCS   : spin-component scaled (Grimme's approach, https://doi.org/10.1002/wcms.1110)
          - SOS   : spin-opposite scaled
          - custom: user-defined scaling factors
        Typically used for MP2; SCS/SOS variants also exist for some approximate CC models.
        """,
    )


class CoupledCluster(ModelMethodElectronic):
    """
    A base section used to define the parameters of a Coupled Cluster calculation.
    A standard schema is defined, though the most common cases can be summarized in the `type` quantity.
    """

    type = Quantity(
        type=str,
        description="""
        String labeling the Coupled Cluster flavor (e.g., CC2, CC3, CCD, CCSD, CCSDT, etc.).
        If a known standard approach, it might match these examples:
          - CC2, CC3  : approximate CC models (commonly used for excited-state calculations)
          - CCD       : Coupled Cluster Doubles
          - CCSD      : Singles and Doubles
          - CCSDT     : Singles, Doubles, and Triples
          - CCSDTQ    : Singles, Doubles, Triples, and Quadruples
        By default, the "perturbative corrections" like (T) are not included in this string.
        """,
    )

    excitation_order = Quantity(
        type=np.int32,
        shape=['*'],
        description="""
        The excitation orders explicitly included in the cluster operator, e.g. [1,2]
        for CCSD.
        - 1 = singles
        - 2 = doubles
        - 3 = triples
        - 4 = quadruples, etc.
        Example: CCSDT => [1, 2, 3].
        """,
    )

    perturbative_correction_order = Quantity(
        type=np.int32,
        shape=['*'],
        description="""
        The excitation orders included only in a perturbative manner.
        For instance, in CCSD(T), singles and doubles are solved iteratively,
        while triples appear as a perturbative correction => [3].
        """,
    )

    perturbative_correction = Quantity(
        type=MEnum('(T)', '[T]', '(T0)', '[T0]', '(Q)'),
        description="""
        Label for the perturbative corrections:
          - '(T)'   : standard perturbative triples
          - '[T]'   : Brueckner-based or other variant
          - '(T0)'  : approximate version of (T)
          - '[T0]'  : approximate, typically for Brueckner references
          - '(Q)'   : perturbative quadruples, e.g., CCSDT(Q)
        """,
    )

    explicit_correlation = Quantity(
        type=MEnum('F12', 'F12a', 'F12b', 'F12c', 'R12'),
        description="""
        Explicit correlation treatment.
        These methods introduce the interelectronic distance coordinate
        directly into the wavefunction to treat dynamical electron correlation.
        It can be added linearly (R12) or exponentially (F12).
        """,
    )


class ConfigurationInteraction(ModelMethodElectronic):
    """
    Single-reference Configuration Interaction (CI) methods using atom-centered basis sets.

    Variants include:
      - CIS    : Configuration Interaction Singles
      - CID    : Configuration Interaction Doubles
      - CISD   : Configuration Interaction Singles and Doubles
      - CISDT  : Configuration Interaction Singles, Doubles and Triples
      - CISDTQ : Configuration Interaction Singles, Doubles, Triples and Quadruples
      - FCI    : Full Configuration Interaction
    """

    type = Quantity(
        type=MEnum(
            'CIS',
            'CID',
            'CISD',
            'CISDT',
            'CISDTQ',
            'FCI',
            'QCISD',
            'QCISD(T)',
        ),
        description='CI variant to employ',
    )

    excitation_order = Quantity(
        type=np.int32,
        shape=['*'],
        description="""
            List of excitation orders included in the CI expansion
            (1=singles, 2=doubles, 3=triples, 4=quadruples, …).
            """,
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)
        # If excitation_order isn’t explicitly set, infer it from the chosen variant:
        default_orders = {
            'CIS': [1],
            'CID': [2],
            'CISD': [1, 2],
            'CISDT': [1, 2, 3],
            'CISDTQ': [1, 2, 3, 4],
            'QCISD': [1, 2],
            'QCISD(T)': [1, 2],
            'FCI': None,  # full space; leave excitation_order unset
        }
        if self.excitation_order is None:
            orders = default_orders.get(self.type)
            if orders is not None:
                self.excitation_order = np.array(orders, dtype=np.int32)
