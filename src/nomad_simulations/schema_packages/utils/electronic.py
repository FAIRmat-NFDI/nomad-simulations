"""
Electronic structure utility functions.
"""

import numpy as np
from pymatgen.electronic_structure.dos import Dos
from pymatgen.electronic_structure.core import Spin
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
    if (hasattr(bandstructure, 'kpoint') and bandstructure.kpoint is not None and 
        hasattr(bandstructure.kpoint, 'all_points') and bandstructure.kpoint.all_points is not None):
        homo_k = bandstructure.kpoint.all_points[homo_idx[-1]]

    lumo_idx = np.unravel_index(np.argmin(bandstructure.lowest_unoccupied), bandstructure.lowest_unoccupied.shape)
    lumo = bandstructure.lowest_unoccupied[lumo_idx]
    if (hasattr(bandstructure, 'kpoint') and bandstructure.kpoint is not None and 
        hasattr(bandstructure.kpoint, 'all_points') and bandstructure.kpoint.all_points is not None):
        lumo_k = bandstructure.kpoint.all_points[lumo_idx[-1]]

    band_gap.value = lumo - homo
    if homo_k is not None and lumo_k is not None:
        band_gap.momentum_transfer = np.linalg.norm(lumo_k - homo_k)

    return band_gap

@check_not_none('input.bandstructure.value', 'input.bandstructure.occupation')
def bandstructure_to_dos(
    bandstructure: 'ElectronicBandStructure',
    energy_bins: int = 1000,
    sigma: float = 0.1,
) -> 'ElectronicDensityOfStates':
    """
    Convert an `ElectronicBandStructure` to an `ElectronicDensityOfStates` using pymatgen's
    Gaussian smearing for smooth DOS curves.
    
    Args:
        bandstructure: The electronic band structure to convert.
        energy_bins: Number of energy bins for the DOS histogram.
        sigma: Gaussian smearing width in eV for DOS broadening.

    Returns:
        An `ElectronicDensityOfStates` object derived from the band structure.
    """
    dos = ElectronicDensityOfStates(is_derived=True)
    
    n_spins = bandstructure.value.shape[0]
    all_energies = bandstructure.value.magnitude.flatten()
    e_min, e_max = np.min(all_energies), np.max(all_energies)
    energies = np.linspace(e_min, e_max, energy_bins)
    
    # Create histogram-based DOS for each spin channel
    dos_dict = {}
    for spin_idx in range(n_spins):
        spin = Spin.up if spin_idx == 0 else Spin.down
        energies_spin = bandstructure.value.magnitude[spin_idx].flatten()
        occupations_spin = bandstructure.occupation[spin_idx].flatten()
        
        dos_hist, _ = np.histogram(energies_spin, bins=energy_bins, 
                                 range=(e_min, e_max), weights=occupations_spin)
        dos_dict[spin] = dos_hist
    
    # Estimate Fermi level from occupied states
    occupied_energies = all_energies[bandstructure.occupation.flatten() > 0.5]
    efermi = np.max(occupied_energies) if len(occupied_energies) > 0 else 0.0
    
    pymatgen_dos = Dos(efermi=efermi, energies=energies, densities=dos_dict)
    
    # Apply Gaussian smearing with bounds checking
    energy_spacing = (e_max - e_min) / energy_bins
    safe_sigma = max(sigma, energy_spacing * 2)
    
    try:
        smeared_densities = pymatgen_dos.get_smeared_densities(safe_sigma)
    except ValueError as e:
        if "Maximum allowed size exceeded" in str(e):
            smeared_densities = pymatgen_dos.densities
        else:
            raise
    
    dos.energies = energies * bandstructure.value.u
    
    if n_spins == 1:
        dos.value = np.array([smeared_densities[Spin.up]]) * (1 / bandstructure.value.u)
    else:
        dos.value = np.array([
            smeared_densities[Spin.up],
            smeared_densities[Spin.down]
        ]) * (1 / bandstructure.value.u)

    return dos
