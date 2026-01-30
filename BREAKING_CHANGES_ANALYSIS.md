# Breaking Changes Analysis - PR #260

**Branch**: `warnings_and_errors`
**Analysis Date**: 2026-01-29

## Executive Summary

PR #260 introduces **CRITICAL BREAKING CHANGES** that extend far beyond the nomad-simulations schema package. The breaking changes affect:

- ✗ **2 parser plugins** (Abinit, AMS)
- ✗ **NOMAD-FAIR core package** (separate repository!)
- ✗ **NOMAD GUI** (JavaScript frontend)
- ✗ **NOMAD tests** (normalizer tests)

**SEVERITY**: 🔴 **CRITICAL - BLOCKS MULTIPLE PACKAGES**

---

## Affected Components

### 1. Parser Plugins (nomad-parser-plugins-simulation)

#### 1.1 Abinit Parser ❌ BROKEN

**File**: `src/nomad_simulation_parsers/schema_packages/abinit.py`

**Lines**: 27-36

**Issue**: References removed fields in `GeometryOptimizationMethod`

```python
class GeometryOptimizationMethod(
    workflow.geometry_optimization.GeometryOptimizationMethod
):
    add_mapping_annotation(
        workflow.geometry_optimization.GeometryOptimizationMethod.convergence_tolerance_energy_difference,  # ❌ DOES NOT EXIST
        OUT_KEY,
        ('get_input_var', [], dict(name='tolmxde', n_dataset=1, default=0.0)),
        unit='hartree',
    )
    add_mapping_annotation(
        workflow.geometry_optimization.GeometryOptimizationMethod.convergence_tolerance_force_maximum,  # ❌ DOES NOT EXIST
        OUT_KEY,
        ('get_input_var', [], dict(name='tolmxf', n_dataset=1, default=0.0)),
        unit='hartree/bohr',
    )
```

**Error**:
```
AttributeError: type object 'GeometryOptimizationMethod' has no attribute 'convergence_tolerance_energy_difference'
```

**Impact**: Parser cannot load, blocking ALL tests

#### 1.2 AMS Parser ❌ BROKEN

**File**: `src/nomad_simulation_parsers/parsers/ams/file_parser.py`

**Lines**: 937-957

**Issue**: Parses convergence tolerance fields that no longer exist in schema

```python
Quantity(
    'convergence_tolerance_force_maximum',
    rf'Maximum gradient\s*({RE_FLOAT})',
    dtype=float,
    unit=ureg.hartree / ureg.bohr,
),
Quantity(
    'convergence_tolerance_energy_difference',
    rf'Maximum energy change allowe\s*({RE_FLOAT})',
    dtype=float,
    unit=ureg.hartree,
),
Quantity(
    'convergence_tolerance_displacement_maximum',
    rf'Maximum step allowed\s*({RE_FLOAT})',
    dtype=float,
    unit=ureg.bohr,
),
```

**Impact**: Parser will parse these fields but have nowhere to store them

#### 1.3 FHI-aims Parser ✓ NOT AFFECTED

**File**: `src/nomad_simulation_parsers/schema_packages/fhiaims.py`

**Status**: Has `GeometryOptimizationMethod` class but does not use removed fields

---

### 2. NOMAD-FAIR Core Package ❌ CRITICAL

**Package**: `nomad-FAIR` (separate repository, dependency of nomad-simulations)

#### 2.1 Results Datamodel ❌ BROKEN

**File**: `packages/nomad-FAIR/nomad/datamodel/results.py`

**Lines**: 3156-3168

**Issue**: Defines convergence tolerance fields and copies them from workflow

```python
class ResultsGeometryOptimization(MSection):
    type = Quantity(type=str)
    convergence_tolerance_energy_difference = Quantity(
        type=np.float64,
        shape=[],
        unit='joule',
        description="""
        The tolerance for differences in the total energy.
        """,
        a_elasticsearch=Elasticsearch(material_entry_type),
    )
    convergence_tolerance_force_maximum = Quantity(
        type=np.float64,
        shape=[],
        unit='newton',
        # ...
    )
```

**Impact**: Results section cannot be populated from workflow

#### 2.2 Results Normalizer ❌ BROKEN

**File**: `packages/nomad-FAIR/nomad/normalizing/results.py`

**Lines**: 918-923

**Issue**: Copies fields from workflow.method to results

```python
if workflow.method is not None:
    geo_opt.type = workflow.method.type
    geo_opt.convergence_tolerance_energy_difference = (
        workflow.method.convergence_tolerance_energy_difference  # ❌ DOES NOT EXIST
    )
    geo_opt.convergence_tolerance_force_maximum = (
        workflow.method.convergence_tolerance_force_maximum  # ❌ DOES NOT EXIST
    )
```

**Impact**: Results normalization fails for geometry optimizations

#### 2.3 Workflow Datamodel ❌ BROKEN

**File**: `packages/nomad-FAIR/nomad/datamodel/metainfo/simulation/workflow.py`

**Lines**: 924-954, 1177-1199

**Issue**: Defines fields AND uses them for convergence checking

**Definitions**:
```python
class GeometryOptimizationMethod(SimulationWorkflowMethod):
    convergence_tolerance_energy_difference = Quantity(
        type=np.float64, shape=[], unit='joule',
        description="""...""",
    )
    convergence_tolerance_force_maximum = Quantity(
        type=np.float64, shape=[], unit='newton',
        description="""...""",
    )
    convergence_tolerance_stress_maximum = Quantity(
        type=np.float64, shape=[], unit='pascal',
        description="""...""",
    )
    convergence_tolerance_displacement_maximum = Quantity(
        type=np.float64, shape=[], unit='meter',
        description="""...""",
    )
```

**Usage in normalize()**:
```python
def normalize(self, archive, logger):
    criteria = []
    try:
        criteria.append(
            self.results.final_energy_difference
            <= self.method.convergence_tolerance_energy_difference  # ❌ DOES NOT EXIST
        )
    except Exception:
        pass
    try:
        criteria.append(
            self.results.final_force_maximum
            <= self.method.convergence_tolerance_force_maximum  # ❌ DOES NOT EXIST
        )
    except Exception:
        pass
    try:
        criteria.append(
            self.results.final_displacement_maximum
            <= self.method.convergence_tolerance_displacement_maximum  # ❌ DOES NOT EXIST
        )
    except Exception:
        pass
```

**Impact**:
- Field definitions conflict with nomad-simulations schema
- Convergence checking logic broken
- **NOTE**: This is in the NOMAD-FAIR *core* package, not in nomad-simulations!

#### 2.4 Legacy Workflows ❌ BROKEN

**File**: `packages/nomad-FAIR/nomad/datamodel/metainfo/simulation/legacy_workflows.py`

**Lines**: 654-675

**Issue**: Legacy schema also defines these fields

```python
class LegacyGeometryOptimizationMethod(MSection):
    convergence_tolerance_energy_difference = Quantity(
        type=np.dtype(np.float64), shape=[], unit='joule',
        description="""...""",
    )
    convergence_tolerance_force_maximum = Quantity(
        type=np.dtype(np.float64), shape=[], unit='newton',
        description="""...""",
    )
    convergence_tolerance_displacement_maximum = Quantity(
        type=np.dtype(np.float64), shape=[], unit='meter',
        description="""...""",
    )
```

**Impact**: Legacy archives cannot be read correctly

---

### 3. NOMAD GUI ❌ BROKEN

**File**: `packages/nomad-FAIR/gui/src/components/visualization/GeometryOptimization.js`

**Lines**: 63-65

**Issue**: JavaScript code reads convergence tolerance for visualization

```javascript
const convergenceCriteria = isNil(convergence?.convergence_tolerance_energy_difference)
  ? undefined
  : new Quantity(convergence.convergence_tolerance_energy_difference, energyUnit).toSystem(units).value()
```

**Impact**: Geometry optimization visualization will not show convergence criteria

---

### 4. NOMAD Tests ❌ BROKEN

**File**: `packages/nomad-FAIR/tests/normalizing/conftest.py`

**Lines**: 1217-1219

**Issue**: Test fixtures use removed fields

```python
if simulationworkflowschema:
    template.workflow2 = simulationworkflowschema.GeometryOptimization(
        method=simulationworkflowschema.GeometryOptimizationMethod(
            convergence_tolerance_energy_difference=1e-3 * ureg.electron_volt,  # ❌ DOES NOT EXIST
            convergence_tolerance_force_maximum=1e-11 * ureg.newton,  # ❌ DOES NOT EXIST
            convergence_tolerance_displacement_maximum=1e-3 * ureg.angstrom,  # ❌ DOES NOT EXIST
            method='bfgs',
            type='atomic',
        )
    )
```

**Impact**: Normalizer tests will fail

---

## Summary of Removed Fields

### From `GeometryOptimizationMethod`:

1. ❌ `convergence_tolerance_energy_difference` (float64, unit='joule')
2. ❌ `convergence_tolerance_force_maximum` (float64, unit='newton')
3. ❌ `convergence_tolerance_stress_maximum` (float64, unit='pascal')
4. ❌ `convergence_tolerance_displacement_maximum` (float64, unit='meter')

### From `NumericalSettings`:

5. ❌ `SelfConsistency` class (entire class removed)
   - `scf_minimization_algorithm` (str)
   - `n_max_iterations` (int)
   - `threshold_change` (float64)
   - `threshold_change_unit` (str)

### From `Outputs`:

6. ❌ `SCFOutputs` class (entire class removed)
   - `scf_steps` subsection (list of Outputs)
   - `get_last_scf_steps_value()` method
   - `resolve_is_scf_converged()` method

### From `PhysicalProperty`:

7. ⚠️ `is_scf_converged` → `is_converged` (renamed)
8. ❌ `self_consistency_ref` removed

---

## Impact Severity Matrix

| Component | Severity | Status | Users Affected |
|-----------|----------|--------|----------------|
| **Abinit parser** | 🔴 Critical | Broken | All abinit users |
| **AMS parser** | 🔴 Critical | Broken | All AMS users |
| **NOMAD-FAIR datamodel** | 🔴 Critical | Broken | **ALL NOMAD users** |
| **NOMAD GUI** | 🟡 High | Degraded | All web users |
| **NOMAD tests** | 🟡 High | Failing | Developers |
| **Legacy archives** | 🟡 High | Incompatible | Archive users |

---

## Critical Issue: Cross-Package Dependencies

### The Core Problem

The breaking changes in PR #260 affect the **NOMAD-FAIR** package, which is a **separate repository** and the **core dependency** of nomad-simulations.

**Dependency Chain**:
```
nomad-FAIR (core)
    ↓ depends on
nomad-simulations (schema)
    ↓ depends on
nomad-parser-plugins-simulation (parsers)
```

### Why This Is Critical

1. **NOMAD-FAIR has its own `GeometryOptimizationMethod`** that:
   - Defines the same convergence tolerance fields
   - Uses them in normalization logic
   - Cannot be updated in this PR (different repo!)

2. **Schema Duplication**: The convergence tolerance fields exist in BOTH:
   - `nomad-simulations` (being removed)
   - `nomad-FAIR` (still present)

3. **Coordination Required**: Any breaking change requires:
   - Synchronized updates across multiple repos
   - Deprecation period for users
   - Migration guide for parsers

---

## Recommended Resolution Strategy

### Option 1: Deprecation Path (Recommended)

1. **Phase 1 - Deprecation (Current Release)**:
   - Keep old fields with deprecation warnings
   - Add new `WorkflowConvergenceTarget` system alongside
   - Update parsers to use new system
   - Log warnings when old fields are used

2. **Phase 2 - Migration (Next Release)**:
   - Provide migration script for old archives
   - Update all parsers and tests
   - Update NOMAD-FAIR core package

3. **Phase 3 - Removal (Future Release)**:
   - Remove deprecated fields
   - Clean up legacy code

**Estimated Timeline**: 3-6 months

### Option 2: Coordinated Breaking Change

1. **Create coordinated PRs**:
   - PR #260 in nomad-simulations (this PR)
   - Parallel PR in NOMAD-FAIR
   - Parallel PR for each affected parser

2. **Merge all together** in a single coordinated release

3. **Provide migration guide** for external parser developers

**Estimated Timeline**: 2-4 weeks

### Option 3: Feature Flag

1. **Use feature flag** to toggle between old and new systems
2. **Default to old system** initially
3. **Gradually migrate** parsers and users
4. **Remove flag** after migration complete

**Estimated Timeline**: 4-8 weeks

---

## Required Fixes (Minimum for Option 2)

### In nomad-simulations (This PR)

1. ✓ Already done - New convergence system implemented
2. ❌ TODO - Add tests for new system
3. ❌ TODO - Fix unit handling bug

### In NOMAD-FAIR (Separate PR Required)

1. ❌ Update `datamodel/results.py` to use new convergence system
2. ❌ Update `normalizing/results.py` to copy new convergence fields
3. ❌ Update `datamodel/metainfo/simulation/workflow.py`:
   - Remove old fields or mark deprecated
   - Update normalization logic to use new system
4. ❌ Update `datamodel/metainfo/simulation/legacy_workflows.py` for backwards compat
5. ❌ Update `gui/src/components/visualization/GeometryOptimization.js` to read new fields

### In nomad-parser-plugins-simulation (This PR)

1. ❌ Update abinit parser to use new convergence API
2. ❌ Update AMS parser to use new convergence API
3. ❌ Update tests to use new fields

---

## Migration Guide for External Parsers

### Old API:
```python
from nomad_simulations.schema_packages.workflow.geometry_optimization import GeometryOptimizationMethod

method = GeometryOptimizationMethod()
method.convergence_tolerance_energy_difference = 1e-6  # eV
method.convergence_tolerance_force_maximum = 1e-3  # eV/Angstrom
```

### New API:
```python
from nomad_simulations.schema_packages.workflow.general import WorkflowConvergenceTarget
from nomad_simulations.schema_packages.workflow.geometry_optimization import GeometryOptimizationMethod

method = GeometryOptimizationMethod()

# Energy convergence
energy_target = WorkflowConvergenceTarget()
energy_target.convergence_parameter_name = 'energy'
energy_target.threshold_type = 'absolute'
energy_target.convergence_threshold = 1e-6
energy_target.threshold_unit = 'eV'
method.convergence.append(energy_target)

# Force convergence
force_target = WorkflowConvergenceTarget()
force_target.convergence_parameter_name = 'force'
force_target.threshold_type = 'maximum'
force_target.convergence_threshold = 1e-3
force_target.threshold_unit = 'eV/angstrom'
method.convergence.append(force_target)
```

---

## Conclusion

PR #260 **CANNOT BE MERGED** without coordinated changes across multiple packages. The breaking changes extend to:

- **2 parsers** in this repo
- **4 modules** in NOMAD-FAIR core
- **1 GUI component**
- **Test fixtures**

**Recommended Action**: Implement **Option 1 (Deprecation Path)** or **Option 2 (Coordinated Breaking Change)** with full team coordination.

---

*Analysis by: Claude Code*
*Date: 2026-01-29*
