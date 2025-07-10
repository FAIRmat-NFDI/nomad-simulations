"""
Electronic structure utility functions.
"""

import numpy as np
from scipy.stats import gaussian_kde
from pymatgen.electronic_structure.core import Spin
from nomad_simulations.schema_packages.properties import (
    ElectronicBandStructure,
    ElectronicDensityOfStates,
    ElectronicBandGap,
)
from nomad_simulations.schema_packages.utils.utils import check_not_none
from nomad.units import ureg


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
    energy_bins: int = None,
    sigma: float = 0.05,
) -> 'ElectronicDensityOfStates':
    """
    Convert an `ElectronicBandStructure` to an `ElectronicDensityOfStates` using pymatgen's
    Gaussian smearing for smooth DOS curves.
    
    Args:
        bandstructure: The electronic band structure to convert.
        energy_bins: Number of energy bins. If None, calculated dynamically.
        sigma: Gaussian smearing width in eV for DOS broadening.

    Returns:
        An `ElectronicDensityOfStates` object derived from the band structure.
    """
    dos = ElectronicDensityOfStates(is_derived=True)
    n_spins = bandstructure.value.shape[0]
    all_energies = bandstructure.value.magnitude.flatten()
    e_min, e_max = np.min(all_energies), np.max(all_energies)
    
    # Calculate dynamic energy bins if not provided
    if energy_bins is None:
        energy_range = e_max - e_min
        n_bands = bandstructure.value.shape[1] if len(bandstructure.value.shape) > 1 else 1
        n_kpoints = bandstructure.value.shape[2] if len(bandstructure.value.shape) > 2 else 1
        
        # Base bins on energy range with minimum resolution of sigma/4
        min_bins = int(energy_range / (sigma / 4))
        
        # Scale with data density: more data points = more bins
        data_factor = np.sqrt(n_bands * n_kpoints)
        data_bins = int(data_factor * 50)  # 50 bins per sqrt(data_points)
        
        # Use the larger of the two, but cap at reasonable limits
        energy_bins = max(min_bins, data_bins)
        energy_bins = min(max(energy_bins, 500), 5000)  # Between 500-5000 bins
    
    energies = np.linspace(e_min, e_max, energy_bins)
    
    # Create smooth DOS using kernel density estimation
    dos_dict = {}
    for spin_idx in range(n_spins):
        spin = Spin.up if spin_idx == 0 else Spin.down
        energies_spin = bandstructure.value.magnitude[spin_idx].flatten()
        occupations_spin = bandstructure.occupation[spin_idx].flatten()
        
        # Only use occupied states for KDE
        occupied_mask = occupations_spin > 0.01  # Small threshold to avoid numerical issues
        if np.sum(occupied_mask) > 1:  # Need at least 2 points for KDE
            occupied_energies = energies_spin[occupied_mask]
            occupied_weights = occupations_spin[occupied_mask]
            
            # Use weighted KDE - repeat energies based on occupation
            weighted_energies = []
            # Scale weights to have better dynamic range
            max_weight = np.max(occupied_weights)
            for e, w in zip(occupied_energies, occupied_weights):
                # Nonlinear scaling to emphasize variations in occupation
                normalized_w = w / max_weight
                n_reps = max(1, int(normalized_w ** 0.7 * 300))  # Power scaling + higher base
                weighted_energies.extend([e] * n_reps)
            
            if len(weighted_energies) > 1:
                # Create KDE and evaluate on energy grid
                kde = gaussian_kde(weighted_energies)
                
                # Smart bandwidth selection based on data characteristics
                energy_range = e_max - e_min
                data_density = len(weighted_energies) / energy_range
                
                # Calculate local energy spacing to assess clustering
                sorted_energies = np.sort(occupied_energies)
                energy_spacings = np.diff(sorted_energies)
                median_spacing = np.median(energy_spacings) if len(energy_spacings) > 0 else energy_range / len(occupied_energies)
                
                # Advanced adaptive bandwidth for better substructure preservation
                base_bandwidth = kde.factor
                
                # Data density factor: logarithmic scaling for better dynamic range
                log_density = np.log10(data_density + 1)
                density_factor = np.clip(0.3 + log_density / 5, 0.15, 1.8)
                
                # Spacing factor: more sensitive to local structure
                relative_spacing = median_spacing / (energy_range / 200)  # Finer resolution
                spacing_factor = np.clip(relative_spacing ** 0.8, 0.2, 1.2)  # Nonlinear response
                
                # Size factor: reduced influence for better detail preservation
                size_factor = (len(weighted_energies) / 2000) ** 0.08  # Much gentler scaling
                
                # Combine factors with emphasis on preserving structure
                adaptive_bandwidth = base_bandwidth * density_factor * spacing_factor * size_factor
                kde.set_bandwidth(adaptive_bandwidth)
                
                dos_values = kde(energies)
                
                # Normalize to conserve total electron count
                total_electrons = np.sum(occupations_spin)
                dos_values = dos_values * total_electrons / np.trapz(dos_values, energies)
                
                dos_dict[spin] = dos_values
            else:
                dos_dict[spin] = np.zeros(energy_bins)
        else:
            dos_dict[spin] = np.zeros(energy_bins)
    
    # Use the energies and densities directly from KDE
    dos.energies = energies
    
    if n_spins == 1:
        dos.value = np.array([dos_dict[Spin.up]])
    else:
        dos.value = np.array([
            dos_dict[Spin.up],
            dos_dict[Spin.down]
        ])

    return dos
