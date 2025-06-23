"""
Electronic structure utility functions.
"""

import numpy as np
from nomad_simulations.schema_packages.properties import (
    ElectronicBandStructure,
    ElectronicDensityOfStates,
    ElectronicBandGap,
)
from nomad_simulations.schema_packages.utils.utils import check_not_none


@check_not_none('input.bandstructure.highest_occupied', 'input.bandstructure.lowest_unoccupied')
def bandstructure_to_bandgap(
    bandstructure: 'ElectronicBandStructure',
) -> 'ElectronicBandGap | None':
    """
    Convert an `ElectronicBandStructure` to an `ElectronicBandGap`
    based on the highest occupied and lowest unoccupied energies within the k-space.
    """
    band_gap = ElectronicBandGap(is_derived=True)
    homo_k, lumo_k = None, None
    
    homo_idx = np.unravel_index(np.argmax(bandstructure.highest_occupied), bandstructure.highest_occupied.shape)
    homo = bandstructure.highest_occupied[homo_idx]
    if hasattr(bandstructure, 'kpoint') and hasattr(bandstructure.kpoint, 'all_points'):
        homo_k = bandstructure.kpoint.all_points[homo_idx[-1]]

    lumo_idx = np.unravel_index(np.argmin(bandstructure.lowest_unoccupied), bandstructure.lowest_unoccupied.shape)
    lumo = bandstructure.lowest_unoccupied[lumo_idx]
    if hasattr(bandstructure, 'kpoint') and hasattr(bandstructure.kpoint, 'all_points'):
        lumo_k = bandstructure.kpoint.all_points[lumo_idx[-1]]

    band_gap.value = lumo - homo
    if homo_k is not None and lumo_k is not None:
        band_gap.momentum_transfer = np.linalg.norm(lumo_k - homo_k)

    return band_gap

@check_not_none('input.bandstructure.value', 'input.bandstructure.occupation')
def bandstructure_to_dos(
    bandstructure: 'ElectronicBandStructure',
    energy_bins: int = 1000,
) -> 'ElectronicDensityOfStates':
    """
    Convert an `ElectronicBandStructure` to an `ElectronicDensityOfStates` by binning occupations along k-points.
    
    Args:
        bandstructure: The electronic band structure to convert.
        energy_bins: Number of energy bins for the DOS histogram.

    Returns:
        An `ElectronicDensityOfStates` object derived from the band structure.
    """
    dos = ElectronicDensityOfStates(is_derived=True)
    
    # Process each spin channel separately
    n_spins = bandstructure.value.shape[0]
    all_energies = bandstructure.value.magnitude.flatten()
    e_min, e_max = np.min(all_energies), np.max(all_energies)
    energy_bin_edges = np.linspace(e_min, e_max, energy_bins + 1)
    energy_centers = (energy_bin_edges[:-1] + energy_bin_edges[1:]) / 2
    
    dos_values = []
    for spin in range(n_spins):
        # Flatten k-point and band dimensions, keep spin separate
        energies_spin = bandstructure.value.magnitude[spin].flatten()
        occupations_spin = bandstructure.occupation[spin].flatten()
        
        dos_hist, _ = np.histogram(energies_spin, bins=energy_bin_edges, weights=occupations_spin)
        dos_values.append(dos_hist)
    
    bin_width = energy_bin_edges[1] - energy_bin_edges[0]
    dos.energies = energy_centers * bandstructure.value.u
    dos.value = (np.array(dos_values) / bin_width) * (1 / bandstructure.value.u)

    return dos
