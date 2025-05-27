from typing import TYPE_CHECKING

import numpy as np
from nomad.metainfo import MEnum, Quantity

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
    """

    iri = 'http://fairmat-nfdi.eu/taxonomy/OneElectronIntegral'

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

    n_basis_functions = Quantity(
        type=np.int32,
        description="""
        Number of basis functions in the selected representation
        (TREXIO: `ao.num` or `mo.num`).
        """,
    )

    value = Quantity(
        type=np.float64,
        unit='hartree',  # overlap is unitless but harmless
        shape=['n_basis_functions', 'n_basis_functions'],
        description="""
        Square matrix holding the chosen component of the operator.  Stored in
        row-major order, identical to TREXIO, so no transposition is required
        when writing/reading.
        """,
    )


class TwoElectronIntegral(PhysicalProperty):
    """
    Electron-electron repulsion integrals (ij|kl).
    One section instance = **one basis (AO/MO) + one component (real/imag)**.
    """

    basis_representation = Quantity(
        type=MEnum('ao', 'mo'),
        description='See `OneElectronIntegral.basis_representation`.',
    )  # EBB TODO

    component = Quantity(
        type=MEnum('real', 'imag'), description='See `OneElectronIntegral.component`.'
    )

    n_basis_functions = Quantity(
        type=np.int32,
        description='Number of AO or MO basis functions (`ao.num` / `mo.num`).',
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

    # Dense tensor
    eri_dense = Quantity(
        type=np.float64,
        unit='hartree',
        shape=[
            'n_basis_functions',
            'n_basis_functions',
            'n_basis_functions',
            'n_basis_functions',
        ],
        description="Present only when `storage_scheme == 'dense'`.",
    )

    # Sparse COO
    eri_indices = Quantity(
        type=np.int64,
        shape=['*', 4],
        description='Index quadruplets (i,j,k,l) for sparse COO representation.',
    )
    eri_values = Quantity(
        type=np.float64,
        unit='hartree',
        shape=['*'],
        description='Values paired with `eri_indices`.',
    )

    # Cholesky
    eri_cholesky = Quantity(
        type=np.float64,
        unit='sqrt(hartree)',
        shape=['*', 'n_basis_functions', 'n_basis_functions'],
        description="Cholesky factors when `storage_scheme == 'cholesky'`.",
    )
