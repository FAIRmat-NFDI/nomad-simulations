from typing import TYPE_CHECKING

import numpy as np
from nomad.metainfo import MEnum, Quantity, Reference, SectionProxy

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from nomad.metainfo import Context, Section
    from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.physical_property import PhysicalProperty


class OneElectronIntegral(PhysicalProperty):
    """
    One-electron matrices **⟨χᵢ| Ô |χⱼ⟩** expressed in either an atomic-orbital (AO)
    or molecular-orbital (MO) basis.  A single instance of this section represents
    *one* operator kind *and* *one* tensor component (real or imaginary).

    This section mirrors the TREXIO format:
    Posenitsky et al., J. Chem. Phys. 158, 174801 (2023)

    Quantities
    ----------
    operator_kind
        Which operator: ``overlap``, ``kinetic``, ``potential_n_e``, ``ecp``,
        or ``core_hamiltonian``.
    basis_representation
        ``ao`` → matrix is expressed in AO space, will be written to
        ``ao_1e_int.<operator_kind>``;
        ``mo`` → MO space, written to ``mo_1e_int.<operator_kind>``.
    component
        Part of a possibly complex matrix: ``real`` or ``imag`` (*dataset*\_im).
    n_functions
        Dimension of the chosen basis (TREXIO ``ao.num`` or ``mo.num``).
    value
        Square matrix, stored row-major (Fortran) exactly as in TREXIO.

    """

    iri = 'http://fairmat-nfdi.eu/taxonomy/OneElectronIntegral'

    # ------------------------------------------------------------------ #
    #                       OPERATOR & BASIS TAGS                        #
    # ------------------------------------------------------------------ #
    operator_kind = Quantity(
        type=MEnum(
            'overlap',  # TREXIO: *_1e_int.overlap
            'kinetic',  #            *_1e_int.kinetic
            'potential_n_e',  #            *_1e_int.potential_n_e
            'ecp',  #            *_1e_int.ecp
            'core_hamiltonian',  #            *_1e_int.core_hamiltonian
        ),
        description="""
        Which one-electron operator this matrix represents.  The label is
        intentionally identical to the TREXIO dataset name, so a writer can do
        `trexio.write_ao_1e_int.{operator_kind}(...)` without a lookup table.

        * **overlap** - dimensionless S₍ᵢⱼ₎  
        * **kinetic** - kinetic energy T₍ᵢⱼ₎ in hartree  
        * **potential_n_e** - electron-nuclear attraction V⁽ⁿᵉ⁾₍ᵢⱼ₎ (hartree)  
        * **ecp** - non-local effective-core potential contribution (hartree)  
        * **core_hamiltonian** - h₍ᵢⱼ₎ = T + V⁽ⁿᵉ⁾ + V⁽ᴱᶜᵖ⁾ (hartree)
        """,
    )

    basis_representation = Quantity(
        type=MEnum('ao', 'mo'),
        description="""
        `ao` - atomic-orbital basis; matrix is stored under the TREXIO group
        `ao_1e_int`.  
        `mo` - molecular-orbital basis; matrix is stored under `mo_1e_int`.
        """,
    )

    component = Quantity(
        type=MEnum('real', 'imag'),
        description="""
        Part of the (possibly complex) matrix that is stored here:

        * **real** - Re [ ⟨χᵢ|Ô|χⱼ⟩ ]  
        * **imag** - Im [ ⟨χᵢ|Ô|χⱼ⟩ ]

        TREXIO keeps real and imaginary parts in *separate* datasets
        (`…_im`).  Creating one NOMAD section per component preserves that
        1-to-1 mapping.
        """,
    )

    # ------------------------------------------------------------------ #
    #                          BASIS REFERENCES                          #
    # ------------------------------------------------------------------ #
    basis_set_ref = Quantity(
        type=Reference(SectionProxy('AtomCenteredBasisSet')),
        description="Required when `basis_representation == 'ao'`.",
    )

    mo_ref = Quantity(
        type=Reference(SectionProxy('MolecularOrbitals')),
        description="Required when `basis_representation == 'mo'`.",
    )

    # ------------------------------------------------------------------ #
    #                         MATRIX DIMENSION                           #
    # ------------------------------------------------------------------ #
    n_functions = Quantity(
        type=np.int32,
        description='Size of the chosen basis (AO or MO).',
    )

    # ------------------------------------------------------------------ #
    #                               DATA                                 #
    # ------------------------------------------------------------------ #
    value = Quantity(
        type=np.float64,
        unit='hartree',  # overlap is unitless but harmless
        shape=['n_basis_functions', 'n_basis_functions'],
        description="""
        Square matrix holding the chosen component of the operator.
        """,
    )


class TwoElectronIntegral(PhysicalProperty):
    """
    Electron-electron repulsion integrals (ij|kl).
    One section instance = **one basis (AO/MO) + one component (real/imag)**.

    This section mirrors the TREXIO format:
    Posenitsky et al., J. Chem. Phys. 158, 174801 (2023)
    """

    # ------------------------------------------------------------------ #
    #                       BASIS & COMPONENT TAGS                       #
    # ------------------------------------------------------------------ #
    basis_representation = Quantity(
        type=MEnum('ao', 'mo'),
        description='See `OneElectronIntegral.basis_representation`.',
    )

    component = Quantity(
        type=MEnum('real', 'imag'), description='See `OneElectronIntegral.component`.'
    )

    storage_scheme = Quantity(
        type=MEnum('dense', 'sparse', 'cholesky'),
        description="""
        Encoding of the 4-index tensor:

        * **dense**   - full `eri_dense` (nbf⁴ values)  
        * **sparse**  - COO lists `eri_indices` / `eri_values`  
        * **cholesky** - low-rank factors `eri_cholesky`
        """,
    )

    # ------------------------------------------------------------------ #
    #                          BASIS REFERENCES                          #
    # ------------------------------------------------------------------ #
    basis_set_ref = Quantity(
        type=Reference(SectionProxy('AtomCenteredBasisSet')),
        description='Required for `ao` representation.',
    )

    mo_ref = Quantity(
        type=Reference(SectionProxy('MolecularOrbitals')),
        description='Required for `mo` representation.',
    )

    # ------------------------------------------------------------------ #
    #                        BASIS DIMENSION COUNT                       #
    # ------------------------------------------------------------------ #
    n_functions = Quantity(
        type=np.int32,
        description='Size of the chosen basis (AO or MO).',
    )

    # ------------------------------------------------------------------ #
    #                           DENSE TENSORS                            #
    # ------------------------------------------------------------------ #
    eri_dense = Quantity(
        type=np.float64,
        unit='hartree',
        shape=['n_functions', 'n_functions', 'n_functions', 'n_functions'],
        description="Present only when `storage_scheme == 'dense'`.",
    )

    eri_lr_dense = Quantity(
        type=np.float64,
        unit='hartree',
        shape=['n_functions', 'n_functions', 'n_functions', 'n_functions'],
        description='Long-range (erf-screened) part, dense encoding.',
    )

    # ------------------------------------------------------------------ #
    #                           SPARSE TENSORS                           #
    # ------------------------------------------------------------------ #
    eri_indices = Quantity(
        type=np.int64,
        shape=['*', 4],
        description='COO index quadruplets (i, j, k, l) – **0-based**.',
    )

    eri_values = Quantity(
        type=np.float64,
        unit='hartree',
        shape=['*'],
        description='Values paired with `eri_indices`.',
    )

    eri_lr_indices = Quantity(
        type=np.int64,
        shape=['*', 4],
        description='COO indices for long-range tensor.',
    )

    eri_lr_values = Quantity(
        type=np.float64,
        unit='hartree',
        shape=['*'],
        description='Values paired with `eri_lr_indices`.',
    )

    # ------------------------------------------------------------------ #
    #                 CHOLESKY LOW-RANK REPRESENTATION                   #
    # ------------------------------------------------------------------ #
    eri_cholesky_num = Quantity(
        type=np.int32,
        description='Number of Cholesky vectors (TREXIO dim).',
    )

    eri_cholesky = Quantity(
        type=np.float64,
        unit='sqrt(hartree)',
        shape=['eri_cholesky_num', 'n_functions', 'n_functions'],
        description='Cholesky factors (low-rank).',
    )

    eri_lr_cholesky_num = Quantity(
        type=np.int32,
        description='Number of long-range Cholesky vectors.',
    )

    eri_lr_cholesky = Quantity(
        type=np.float64,
        unit='sqrt(hartree)',
        shape=['eri_lr_cholesky_num', 'n_functions', 'n_functions'],
        description='Long-range Cholesky factors.',
    )
