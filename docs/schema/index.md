# Schema Documentation

This section contains auto-generated documentation for the NOMAD simulations schema.

The schema is organized into vertical domains, each covering a specific aspect of simulation metadata:

## [Methods & Parameters](methods.md)

Code-agnostic method choices and numerical controls that drive reproducibility.

**In scope:** electronic-structure family, XC selection, smearing, numerical cutoffs/settings

**Key sections:** ModelMethod, ModelMethodElectronic, DFT, TB, DMFT, GW, XCFunctional, NumericalSettings, Smearing, Program

## [Basis & Orbitals](basis.md)

Representations used to expand wavefunctions or Hamiltonians.

**In scope:** plane wave parameters, APW/APW+lo, localized atomic basis, tight-binding tables

**Key sections:** PlaneWaveBasisSet, AtomCenteredBasisSet, APWPlaneWaveBasisSet, APWLocalOrbital, APWOrbital, AtomCenteredFunction, SlaterKoster, SlaterKosterBond

## [System & Geometry](system.md)

Atomic structure, cell, symmetry and reciprocal space definitions.

**In scope:** lattice, positions, periodicity, k-space definitions, symmetry

**Key sections:** ModelSystem, System, AtomicCell, Cell, Symmetry, KSpace, KMesh, ChemicalFormula

## [Workflows](workflows.md)

End-to-end procedures composed of tasks (e.g., SCF, MD, geometry optimization).

**In scope:** task graphs, iteration loops, task references

**Key sections:** Workflow, SimulationWorkflow, ParallelWorkflow, SerialWorkflow, GeometryOptimization, MolecularDynamics, SinglePoint, Task, SimulationTask, SelfConsistency

## [Results & Provenance](results.md)

Canonical scientific outputs and provenance bundles.

**In scope:** band structures, DOS, gaps, SCF history, trajectories

**Key sections:** Outputs, ElectronicStructureResults, ElectronicBandStructure, ElectronicDensityOfStates, ElectronicBandGap, FermiSurface, SCFOutputs, TrajectoryOutputs, ThermodynamicsResults, GeometryOptimizationResults

## [Vibrations, Phonons & Elastic](phonon_elastic.md)

Lattice dynamics models and results, elastic tensors, and Hessians.

**In scope:** phonon dispersions, force constants, elastic constants

**Key sections:** Phonon, PhononModel, PhononResults, Elastic, ElasticModel, ElasticResults, Hessian

## [Spectroscopy & Excitations](spectroscopy.md)

Excited-state methods and spectra.

**In scope:** BSE/GW artifacts, response functions, quasiparticles

**Key sections:** AbsorptionSpectrum, XASSpectrum, BSE, Screening, ElectronicGreensFunction, ElectronicSelfEnergy, QuasiparticleWeight, DFTGWModel, DFTGWResults, DFTGWWorkflow

## [Thermodynamics](thermo.md)

Thermodynamic state functions and models.

**In scope:** state functions, derived thermodynamic curves

**Key sections:** Thermodynamics, ThermodynamicsModel, ThermodynamicsResults, HeatCapacity, Entropy, HelmholtzFreeEnergy, GibbsFreeEnergy, Enthalpy, InternalEnergy


---

## How to use this documentation

Each vertical page contains:

- **Purpose**: High-level description of what the vertical covers
- **Relationship map**: Mermaid diagram showing connections between sections
- **Key sections**: Table linking to detailed class definitions in the MetaInfo browser
- **Micro-examples**: Sample YAML snippets demonstrating structure

For detailed information about each class, follow the MetaInfo browser links on the individual vertical pages.