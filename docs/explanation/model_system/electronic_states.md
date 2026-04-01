# Electronic States and Quantum Number Representation

## Introduction

The representation of electronic states in the NOMAD simulations schema follows a two-level architecture that separates the organizational aspects of electronic structure from the quantum mechanical description of individual states. At the top level, the `ElectronicState` class provides a hierarchical navigation structure for organizing electronic configurations. The actual quantum mechanical information resides in instances of `BaseSpinOrbitalState` subclasses, most commonly `SphericalSymmetryState`, which use quantum numbers to precisely define states.

This design emphasizes semantic organization over numerical representation. The `ElectronicState` hierarchy labels and organizes which orbitals participate in a calculation, providing reference points for projection operations in density of states, band structure, or Green's function calculations. The numerical details of how these states are represented computationally reside elsewhere in the schema: basis set definitions live in the `numerical_settings` module, while expansion coefficients and eigenvalues appear in property sections like `BandStructure` or `DOSElectronic`. This separation allows the same electronic state labels to apply across different numerical treatments, whether plane-wave, localized orbital, or other basis set approaches.

The semantic focus proves essential when complex electronic structures require multiple decomposition views. The same d-electrons in a transition metal atom can be organized by orbital angular momentum (L-S coupling), by total angular momentum (j-j coupling), or by crystal field symmetry labels. The `ElectronicState` hierarchy accommodates all these perspectives while the underlying quantum numbers remain consistently defined.

## The ElectronicState Container

Each `ElectronicState` instance contains a `spin_orbit_state` field referencing a `BaseSpinOrbitalState` that describes the quantum state at that hierarchy level. The `sub_states` field enables recursive decomposition, building complex electronic structures from progressively finer-grained components. This recursive structure naturally expresses manifolds decomposing into individual orbitals, which further split into spin components.

For systems where electronic states arise from linear combinations of simpler basis functions, the `basis_orbitals` field holds a list of `BaseSpinOrbitalState` objects representing the constituent orbitals. This pattern applies to hybrid orbitals like sp³, molecular orbitals constructed via LCAO methods, or Wannier functions expressed as linear combinations of Bloch states. The actual expansion coefficients belong in the relevant electronic eigenvalue sections rather than being duplicated in the state definition.

The container also tracks occupation numbers and degeneracy. For non-interacting systems, occupations follow integer values or Fermi-Dirac distributions. In strongly correlated systems described by many-body methods like DMFT, fractional occupations reflect the quantum nature of the many-body state rather than partial filling of individual orbitals. The degeneracy can be computed automatically from quantum numbers or set explicitly for symmetry-adapted states.

## Quantum State Description with SphericalSymmetryState

The `SphericalSymmetryState` class provides quantum mechanical descriptions using spherical symmetry quantum numbers. The principal quantum number `n_quantum_number` identifies the shell, while `l_quantum_number` specifies the orbital angular momentum with values 0, 1, 2, 3 corresponding to s, p, d, f orbitals. The azimuthal projection `ml_quantum_number` must satisfy -l ≤ ml ≤ l and determines the orbital's directional character.

For systems with significant spin-orbit coupling, the total angular momentum quantum number `j_quantum_number` becomes relevant. The relationship j = |l - s|, |l - s| + 1, ..., l + s follows from Russell-Saunders coupling theory. The projection `mj_quantum_number` ranges from -j to j in integer steps. Similarly, the spin projection `ms_quantum_number` relates to the spin quantum number `s_quantum_number`, which defaults to 0.5 for electrons.

In relativistic calculations, the `kappa_quantum_number` provides an alternative labeling scheme. The relationship j = |κ| - 0.5 connects κ to the total angular momentum, while the sign of κ encodes information about the orbital angular momentum. Specifically, l = |κ| - 1 for negative κ and l = κ for positive κ. However, the schema deliberately avoids automatic conversion between κ and (j, l) during normalization to prevent baking relativistic assumptions into the data representation.

## Derived Properties

The quantum number symbols `l_quantum_symbol`, `ml_quantum_symbol`, and `ms_quantum_symbol` are derived automatically from their corresponding quantum numbers. Setting `l_quantum_number = 1` causes `l_quantum_symbol` to return 'p', while `l_quantum_number = 2` yields 'd'. The ml symbols map to directional labels like 'x', 'y', 'z' for p-orbitals or 'xy', 'xz', 'z^2', 'yz', 'x^2-y^2' for d-orbitals.

These symbol properties should therefore be understood as derived views of the underlying quantum numbers rather than as independently stored inputs. In NOMAD-Simulations archives, the quantum number values remain the canonical representation. Likewise, `j_quantum_number` and `mj_quantum_number` appear as scalar quantities in normalized data.

The `_name` property generates human-readable orbital labels by combining available quantum number information. A state with n=2 and l=1 produces "2p", while specifying ml=-1 yields "2px". When j is provided without ml, the format uses parentheses as in "2p(j=0.5)". This automatic naming is generally useful for inspection and visualization but can be overridden by explicitly setting the `name` field on the parent `ElectronicState`.

## Understanding Electronic-State Hierarchies

In NOMAD-Simulations archives, `SphericalSymmetryState` information appears through an `ElectronicState` container rather than as a standalone atom-level section. At the `AtomsState` level, the `electronic_state` field holds one `ElectronicState` instance, which can in turn carry a single quantum state descriptor in `spin_orbit_state`, a list of basis functions in `basis_orbitals`, or a hierarchy of finer-grained states in `sub_states`.

For a simple hydrogen atom, the archive may contain an `ElectronicState` with a `SphericalSymmetryState` in its `basis_orbitals` list. For a transition metal with multiple d-orbitals, a parent `ElectronicState` can describe the d-manifold while its `sub_states` resolve the individual orbital components. Each child inherits context from the parent, so specifying n=3 and l=2 at the parent level means children need only specify their ml values.

When dealing with correlated systems, the hierarchy may be minimal or absent entirely. A DMFT calculation of 3d electrons cannot decompose the many-body state into single-particle orbitals, so the electronic structure consists of a single `ElectronicState` with the manifold's quantum numbers and a fractional occupation reflecting the correlated nature. The absence of `sub_states` signals that further decomposition is not physically meaningful.

## Validation and Normalization

During normalization, the schema validates quantum number relationships. Setting ml outside the range [-l, l] triggers an error and prevents normalization from completing. Similarly, mj must satisfy -j ≤ mj ≤ j. The validation for κ and j consistency checks that j = |κ| - 0.5 within numerical tolerance, logging errors when this relationship fails.

However, normalization deliberately avoids automatic derivation of quantum numbers from relationships. A state with κ defined but j undefined will not populate j automatically. This design choice prevents the schema from imposing physical assumptions about relativistic effects or coupling schemes, and it means readers of NOMAD-Simulations archives should not assume that missing quantum numbers will be inferred automatically.

When `name` or `degeneracy` remain unset, normalization computes them from available quantum information. The degeneracy calculation considers whether projection quantum numbers are specified. For j without mj, the degeneracy equals 2j+1. For l without ml and no j information, the orbital degeneracy is 2l+1, optionally multiplied by spin degeneracy if ms is unspecified. When both ml and ms are defined, the degeneracy becomes 1 since the state is fully specified.

## Hierarchical Decomposition Examples

Consider a copper atom's 3d electrons in a DFT calculation. One possible representation in a NOMAD-Simulations archive uses an `ElectronicState` with n=3 and l=2 in its `spin_orbit_state` to represent the d-manifold. Five child states with ml values -2, -1, 0, 1, 2 then resolve the conventional d-orbital components dxy, dxz, dz², dyz, dx²-y². Each of these can further split into spin-up and spin-down components through children with ms=±0.5. This three-level hierarchy from manifold to orbital to spin matches the decomposition in typical DFT+U implementations.

For a system in an octahedral crystal field, the decomposition follows symmetry rather than pure angular momentum. In that case, child states labeled t2g and eg can carry the appropriate symmetry labels and point group information. The t2g state has degeneracy 6 (three orbitals times two spins) while eg has degeneracy 4. This symmetry-adapted decomposition coexists with the angular momentum decomposition as an alternative view of the same electronic structure, selected based on the physical question being addressed.

For Wannier-function-based descriptions, `ElectronicState` instances can use the `basis_orbitals` field to record the atomic orbitals participating in the Wannierization. Each basis orbital is a `SphericalSymmetryState` with specific n, l, ml values. The expansion coefficients connecting Bloch states to Wannier functions reside in the band structure eigenvector arrays rather than in the state definition, maintaining clean separation between basis-set definition and wavefunction coefficients.

