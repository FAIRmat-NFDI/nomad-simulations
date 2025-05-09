# `ModelMethod`

The `ModelMethod` section contains all parameters and settings that define the mathematical model or Hamiltonian used in a simulation. This module abstracts the model into various levels so that the total Hamiltonian can be decomposed into contributions (or terms). The module currently covers common electronic structure methods (e.g., DFT, TB, GW,BSE, DMFT), and it is being actively developed to encompass further computational methods.


## Explanation of main sections

| Section                   | Key Quantities & Brief Explanation |
|---------------------------|--------------------------------------|
| **BaseModelMethod**       | - `name`: Identifier for the mathematical model (e.g., DFT, TB, GW, etc.).<br>- `type`: Specifies the model sub-type (e.g., Wannier, DFTB, xTB, Slater-Koster).<br>- `external_reference`: URL or DOI for an external reference to the model.<br>- `numerical_settings`: A subsection holding numerical parameters (e.g., convergence criteria). |
| **ModelMethod**           | Inherits from BaseModelMethod and adds:<br>- `contributions`: A subsection to include individual contributions or terms that build up the total Hamiltonian. |
| **ModelMethodElectronic** | Inherits from ModelMethod and adds electronic structure specific details:<br>- `is_spin_polarized`: Boolean indicating if spin polarization is considered (e.g., two spin channels).<br>- `relativity_method`: Specifies the relativistic treatment applied (e.g., scalar_relativistic, pseudo_scalar_relativistic). |


## List of electronic structure methods

<table>
  <tr>
    <th>Electronic Structure Method</th>
    <th>Quantity</th>
    <th>Explanation</th>
    <th>Quantity Type</th>
  </tr>
  <!-- DFT -->
  <tr>
    <td rowspan="5"><strong>DFT</strong></td>
    <td>jacobs_ladder</td>
    <td>Classifies the XC functional (e.g., LDA, GGA, metaGGA, hybrid).</td>
    <td>MEnum (options: LDA, GGA, metaGGA, hyperGGA, hybrid, unavailable)</td>
  </tr>
  <tr>
    <td>xc_functionals</td>
    <td>List of XCFunctional subsections.</td>
    <td>SubSection (list)</td>
  </tr>
  <tr>
    <td>exact_exchange_mixing_factor</td>
    <td>Fraction of exact exchange mixed in.</td>
    <td>np.float64</td>
  </tr>
  <tr>
    <td>self_interaction_correction_method</td>
    <td>Specifies any self-interaction correction applied.</td>
    <td>str</td>
  </tr>
  <tr>
    <td>van_der_waals_correction</td>
    <td>Method used for van der Waals correction.</td>
    <td>MEnum (options: TS, OBS, G06, JCHS, MDB, XC)</td>
  </tr>
  <!-- TB -->
  <tr>
    <td rowspan="4"><strong>TB</strong></td>
    <td>n_orbitals_per_atom</td>
    <td>Number of orbitals per atom used as basis.</td>
    <td>np.int32</td>
  </tr>
  <tr>
    <td>n_atoms_per_unit_cell</td>
    <td>Number of atoms per unit cell (derived from total orbitals).</td>
    <td>np.int32</td>
  </tr>
  <tr>
    <td>n_total_orbitals</td>
    <td>Total number of orbitals (n_orbitals_per_atom × n_atoms_per_unit_cell).</td>
    <td>np.int32</td>
  </tr>
  <tr>
    <td>orbitals_ref</td>
    <td>References to OrbitalsState sections representing the orbital basis.</td>
    <td>Reference</td>
  </tr>
  <!-- Wannier -->
  <tr>
    <td rowspan="4"><strong>Wannier</strong></td>
    <td>is_maximally_localized</td>
    <td>Flag indicating if orbitals are maximally localized.</td>
    <td>bool</td>
  </tr>
  <tr>
    <td>localization_type</td>
    <td>Specifies 'maximally_localized' or 'single_shot' projection.</td>
    <td>MEnum (options: single_shot, maximally_localized)</td>
  </tr>
  <tr>
    <td>n_bloch_bands</td>
    <td>Number of Bloch bands used for projection.</td>
    <td>np.int32</td>
  </tr>
  <tr>
    <td>energy_window_outer/inner</td>
    <td>Energy window boundaries for orbital projection.</td>
    <td>np.float64 (unit: electron_volt)</td>
  </tr>
  <!-- Slater-Koster -->
  <tr>
    <td rowspan="4"><strong>Slater-Koster</strong></td>
    <td>orbital_1 &amp; orbital_2</td>
    <td>References to the two OrbitalsState sections defining a bond.</td>
    <td>Reference</td>
  </tr>
  <tr>
    <td>bravais_vector</td>
    <td>Lattice vector indicating bond direction (cell indices).</td>
    <td>np.int32 array (shape: [3])</td>
  </tr>
  <tr>
    <td>integral_value</td>
    <td>Bond integral value.</td>
    <td>np.float64</td>
  </tr>
  <tr>
    <td>name</td>
    <td>Resolved bond name (e.g., 'sss', 'sps', 'sds').</td>
    <td>MEnum (options: sss, sps, sds)</td>
  </tr>
  <!-- GW -->
  <tr>
    <td rowspan="4"><strong>GW</strong></td>
    <td>type</td>
    <td>Specifies the GW cycle type (e.g., G0W0, scGW, etc.).</td>
    <td>MEnum (options: G0W0, scGW, scGW0, scG0W, ev-scGW0, ev-scGW, qp-scGW0, qp-scGW)</td>
  </tr>
  <tr>
    <td>analytical_continuation</td>
    <td>Method for self-energy continuation.</td>
    <td>MEnum (options: pade, contour_deformation, ppm_GodbyNeeds, ppm_HybertsenLouie, ppm_vonderLindenHorsh, ppm_FaridEngel, multi_pole)</td>
  </tr>
  <tr>
    <td>interval_qp_corrections</td>
    <td>Band index interval for quasiparticle corrections.</td>
    <td>np.int32 array</td>
  </tr>
  <tr>
    <td>screening_ref</td>
    <td>Reference to the Screening section for Coulomb interaction parameters.</td>
    <td>Reference</td>
  </tr>
  <!-- BSE -->
  <tr>
    <td rowspan="3"><strong>BSE</strong></td>
    <td>type</td>
    <td>BSE Hamiltonian type (Singlet, Triplet, IP, RPA).</td>
    <td>MEnum (options: Singlet, Triplet, IP, RPA)</td>
  </tr>
  <tr>
    <td>solver</td>
    <td>Diagonalization algorithm used for the BSE Hamiltonian.</td>
    <td>MEnum (options: Full-diagonalization, Lanczos-Haydock, GMRES, SLEPc, TDA)</td>
  </tr>
  <tr>
    <td>screening_ref</td>
    <td>Reference to the Screening section.</td>
    <td>Reference</td>
  </tr>
  <!-- DMFT -->
  <tr>
    <td rowspan="7"><strong>DMFT</strong></td>
    <td>impurity_solver</td>
    <td>Method used for solving the impurity problem.</td>
    <td>MEnum (options: CT-INT, CT-HYB, CT-AUX, ED, NRG, MPS, IPT, NCA, OCA, slave_bosons, hubbard_I)</td>
  </tr>
  <tr>
    <td>n_impurities</td>
    <td>Number of impurities mapped from the system.</td>
    <td>np.int32</td>
  </tr>
  <tr>
    <td>n_orbitals</td>
    <td>Number of orbitals per impurity.</td>
    <td>np.int32 array</td>
  </tr>
  <tr>
    <td>orbitals_ref</td>
    <td>References to OrbitalsState sections relevant for correlated orbitals.</td>
    <td>Reference</td>
  </tr>
  <tr>
    <td>n_electrons</td>
    <td>Initial number of valence electrons per impurity.</td>
    <td>np.float64 array</td>
  </tr>
  <tr>
    <td>inverse_temperature</td>
    <td>Inverse temperature (1/(kB*T)).</td>
    <td>np.float64</td>
  </tr>
  <tr>
    <td>magnetic_state</td>
    <td>Magnetic ordering (paramagnetic, ferromagnetic, antiferromagnetic).</td>
    <td>MEnum (options: paramagnetic, ferromagnetic, antiferromagnetic)</td>
  </tr>
  <!-- ExcitedStateMethodology -->
  <tr>
    <td rowspan="3"><strong>ExcitedStateMethodology</strong></td>
    <td>n_states</td>
    <td>Number of states used for excitations.</td>
    <td>np.int32</td>
  </tr>
  <tr>
    <td>n_empty_states</td>
    <td>Number of empty states considered.</td>
    <td>np.int32</td>
  </tr>
  <tr>
    <td>broadening</td>
    <td>Lifetime broadening applied to spectra.</td>
    <td>np.float64</td>
  </tr>
  <!-- Photon -->
  <tr>
    <td rowspan="4"><strong>Photon</strong></td>
    <td>multipole_type</td>
    <td>Type for multipolar expansion.</td>
    <td>MEnum (options: dipolar, quadrupolar, NRIXS, Raman)</td>
  </tr>
  <tr>
    <td>polarization</td>
    <td>Photon polarization vector (Cartesian coordinates).</td>
    <td>np.float64 array</td>
  </tr>
  <tr>
    <td>energy</td>
    <td>Photon energy.</td>
    <td>np.float64</td>
  </tr>
  <tr>
    <td>momentum_transfer</td>
    <td>Momentum transferred to the lattice (for inelastic scattering).</td>
    <td>np.float64 array</td>
  </tr>
</table>



## An example `ModelMethod` instance

```
# Create a SelfConsistency instance with SCF convergence criteria
scf_settings = SelfConsistency(
    scf_minimization_algorithm="Pulay",   # Example algorithm for SCF convergence
    n_max_iterations=100,                 # Maximum number of SCF iterations allowed
    threshold_change=1e-5,                # Convergence threshold (change between iterations)
    threshold_change_unit="hartree"       # Unit for the convergence threshold
)

# Create an XCFunctional instance for the TPSSh hybrid functional (10% exact exchange)
tpssh_functional = XCFunctional(
    libxc_name="XC_HYB_TPSSh",   # Identifier following the libxc naming convention
    name="hybrid",             # Indicates that this is a hybrid XC functional
    weight=0.10                # 10% exact exchange
)

# Instantiate a DFT method using TPSSh and enrich it with the numerical settings
dft_tpssh = DFT(
    name="DFT",
    type="DFT",
    numerical_settings=[scf_settings]
)

# Append the TPSSh XCFunctional to the DFT method
dft_tpssh.xc_functionals.append(tpssh_functional)

```