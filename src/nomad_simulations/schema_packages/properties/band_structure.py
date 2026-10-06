from nomad.metainfo import SubSection

from nomad_simulations.schema_packages.properties.electronic_eigenvalues import (
    BaseElectronicEigenvalues,
)
from nomad_simulations.schema_packages.variables import KLinePath


class ElectronicBandStructure(BaseElectronicEigenvalues):
    """
    Accessible energies by the charges (electrons and holes) in the reciprocal space. The
    eigenvalues are sampled along a high-symmetry line path, whose structure is carried by the
    `k_path` axis. Reference levels and the electronic band gap are not derived from this
    property: a path does not sample the full Brillouin zone, so the true band extrema may lie
    off the path; that derivation belongs to the sibling `ElectronicEigenvalues`.
    """

    iri = 'http://fairmat-nfdi.eu/taxonomy/ElectronicBandStructure'

    k_path = SubSection(
        sub_section=KLinePath.m_def,
        description="""
        High-symmetry line path along which the eigenvalues are sampled. The sampled coordinates
        are stored directly in `points`; the delimiting high-symmetry points provide the segment
        structure for plotting.
        """,
    )
