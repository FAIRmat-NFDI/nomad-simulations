# Code Review: PR #260 - Refactor SCF quantities and convergence

**Reviewer**: Claude Code
**Review Date**: 2026-01-29
**Branch**: `warnings_and_errors`
**PR**: https://github.com/FAIRmat-NFDI/nomad-simulations/pull/260
**Author**: @kubanmar
**Status**: Draft/In Progress

## Executive Summary

This PR introduces a significant architectural refactoring of convergence handling in the nomad-simulations schema. The changes replace scattered convergence parameters with a unified target-result pattern using `WorkflowConvergenceTarget` and `WorkflowConvergenceResults`. While the design is sound and addresses real architectural issues, the PR has **critical blockers** that prevent merging:

### Critical Blockers (Must Fix)
1. ✗ **Abinit parser completely broken** - prevents tests from running
2. ✗ **Zero test coverage for new convergence system** - 169 lines of tests removed, 0 added
3. ✗ **Unit handling inconsistency** - threshold loses quantity information (documented TODO)

### Major Concerns (Should Fix)
4. ⚠ **Breaking changes undocumented** - no migration guide for parser developers
5. ⚠ **Code organization unclear** - multiple TODOs about class placement
6. ⚠ **Edge case handling incomplete** - limited error handling in convergence resolution

### Positive Aspects
- ✓ Well-structured target-result pattern
- ✓ Unified convergence approach across workflow types
- ✓ Comprehensive docstrings for new schema sections
- ✓ Good cleanup of empty normalize() methods
- ✓ Existing unit tests pass (175/175)

---

## 1. Architecture Review

### 1.1 Convergence Pattern Design ✓

**Rating**: Good

The new convergence system uses a clean **target-result pattern**:

```
WorkflowConvergenceTarget (input)
├── convergence_parameter_name: MEnum
├── convergence_threshold: float
├── threshold_unit: str
└── threshold_type: MEnum

WorkflowConvergenceResults (output)
├── convergence_target_ref: WorkflowConvergenceTarget
└── is_reached: bool
```

**Strengths**:
- Clear separation of concerns: targets (what to check) vs results (what was achieved)
- Reusable across workflow types (GeometryOptimization, SinglePoint, etc.)
- Extensible: easy to add new convergence parameter types

**Concerns**:
- Threshold as `float` instead of `Quantity` loses unit information during processing (line 391 in general.py has TODO about this)
- The mapping between parameter names and archive paths is hardcoded in `CONVERGENCE_QUANTITY_MAPPING` (line 28-34)

### 1.2 JMESPath Integration ⚠

**Rating**: Mixed

The PR introduces `jmespath` for querying archive data to extract convergence values.

**Location**: `workflow/general.py:359-405`

**Strengths**:
- Powerful query syntax for nested data
- Reduces manual path traversal code

**Concerns**:
- **New dependency** not mentioned in PR description
- **Hybrid approach**: Lines 373-385 manually split the path and extract the last component because "jmespath only returns the raw values and not quantities" (TODO comment)
- **Limited error handling**: Returns `None` if path doesn't exist, but doesn't log why
- **Hardcoded mapping**: `CONVERGENCE_QUANTITY_MAPPING` dict couples parameter names to specific archive paths

**Recommendation**: Consider whether JMESPath adds enough value to justify the dependency, given that manual path handling is still needed for quantities.

### 1.3 SCF Data Structure Changes ✓

**Rating**: Good

**Before** (removed):
```python
class SCFOutputs(Outputs):
    scf_steps = SubSection(sub_section=Outputs.m_def, repeats=True)
    # nested Outputs for each SCF step
```

**After** (new):
```python
class SCFSteps(ArchiveSection):
    energies_total = Quantity(shape=['*'], unit='joule')
    delta_energies_total = Quantity(shape=['*'], unit='joule')
    delta_potential_rms = Quantity(shape=['*'], unit='joule')
    delta_density_rms = Quantity(shape=['*'], unit='coulomb')
    delta_force_abs = Quantity(shape=['*'], unit='newton')
    durations = Quantity(shape=['*'], unit='s')
    code_specific_quantities = Quantity(type=JSON)

class Outputs:
    scf_steps = SubSection(sub_section=SCFSteps.m_def, repeats=False)
```

**Strengths**:
- Flatter structure: array-based rather than nested sections
- More efficient: single section with arrays vs. list of full Output sections
- Clearer intent: SCFSteps explicitly models iteration data
- Better type safety: specific quantities vs. generic Outputs

**Concerns**:
- Author notes "I don't think this should live here" (line 42 in outputs.py) - placement unclear
- No migration path documented for parsers using old `SCFOutputs`

### 1.4 Task Generation in GeometryOptimization ✓

**Rating**: Good

**Location**: `workflow/geometry_optimization.py:195-258`

The `map_tasks()` method now intelligently creates different task types:
- `SinglePoint` tasks for outputs with `scf_steps`
- Generic `Task` for outputs without `scf_steps`

**Strengths**:
- Dynamic task generation from output structure
- Correctly links convergence targets to individual SinglePoint tasks
- Preserves timing-based task ordering

**Concerns**:
- Uses JMESPath to fetch `single_point_convergence` from archive (line 226-232)
- Calls protected method `_resolve_convergence()` from outside the class (line 230)
- No error handling if convergence resolution fails

---

## 2. Breaking Changes Audit

### 2.1 Critical: Abinit Parser Broken ✗

**Severity**: BLOCKER

**Location**: `packages/nomad-parser-plugins-simulation/src/nomad_simulation_parsers/schema_packages/abinit.py:27`

```python
class GeometryOptimizationMethod(workflow.geometry_optimization.GeometryOptimizationMethod):
    add_mapping_annotation(
        workflow.geometry_optimization.GeometryOptimizationMethod.convergence_tolerance_energy_difference,  # ← DOES NOT EXIST
        OUT_KEY,
        ('get_input_var', [], dict(name='tolmxde', n_dataset=1, default=0.0)),
        unit='hartree',
    )
```

**Error**:
```
AttributeError: type object 'GeometryOptimizationMethod' has no attribute 'convergence_tolerance_energy_difference'
```

**Impact**: All tests fail on collection because abinit parser cannot be loaded.

**Root Cause**: The following fields were removed from `GeometryOptimizationMethod`:
- `convergence_tolerance_energy_difference`
- `convergence_tolerance_force_maximum`
- `convergence_tolerance_stress_maximum`
- `convergence_tolerance_displacement_maximum`

These were replaced by the generic `convergence` subsection with `WorkflowConvergenceTarget`.

**Resolution Required**:
1. Update abinit parser to use new `WorkflowConvergenceTarget` pattern
2. Document migration steps for other parser maintainers
3. Consider deprecation strategy vs. immediate breaking change

### 2.2 SelfConsistency Class Removed ✗

**Severity**: HIGH (Breaking Change)

**Location**: Removed from `numerical_settings.py`

**What was removed** (58 lines):
- `scf_minimization_algorithm` (str)
- `n_max_iterations` (int)
- `threshold_change` (float)
- `threshold_change_unit` (str)

**Impact**:
- Any parser populating `SelfConsistency` will break
- Old archives with `SelfConsistency` data may not display correctly
- No migration documented

**Replacement**: Convergence settings now live in `WorkflowConvergenceTarget` within workflow sections, not in `NumericalSettings`.

### 2.3 SCFOutputs Class Removed ✗

**Severity**: HIGH (Breaking Change)

**Location**: Removed from `outputs.py`

**What was removed** (142 lines):
- `SCFOutputs` class with `scf_steps` subsection
- `get_last_scf_steps_value()` method
- `resolve_is_scf_converged()` method
- Automatic convergence checking logic

**Impact**:
- Parsers using `SCFOutputs` will break
- Old normalization logic that relied on `SCFOutputs` must be rewritten

**Replacement**: Use `Outputs` with new `scf_steps` subsection of type `SCFSteps`, and convergence checking is handled by workflow normalization.

### 2.4 PhysicalProperty API Changes ⚠

**Severity**: MEDIUM (Rename + Removal)

**Location**: `physical_property.py`

**Changes**:
1. `is_scf_converged` → `is_converged` (renamed)
2. `self_consistency_ref` removed entirely

**Impact**:
- Code accessing `is_scf_converged` will break
- Properties linked to `self_consistency_ref` lose that connection

**Mitigation**: The rename is reasonable (broader scope), but needs documentation.

### 2.5 Other Breaking Changes

#### Program Class Additions ✓
**Location**: `general.py`

**New fields** (non-breaking additions):
- `compiler_name` (str)
- `compiler_version` (str)
- `warnings` (str, shape=['*'])

#### BaseSimulation Class Additions ✓
**Location**: `general.py`

**New fields** (non-breaking additions):
- `datetime_end` (Datetime)
- `cpu1_start`, `cpu1_end` (float, unit='second')
- `wall_start`, `wall_end` (float, unit='second')
- `finished_without_errors` (bool)

**Note**: These overlap with fields in `WorkflowTime` (TODO line 149 in workflow/general.py)

---

## 3. Implementation Quality Review

### 3.1 Code Quality ✓

**Rating**: Good

**Strengths**:
- Comprehensive docstrings with tables for MEnum values
- Type hints throughout
- Proper inheritance patterns
- Good use of @log decorator for observability

**Concerns**:
- Multiple TODO comments from author (6 total)
- Some logic complexity in `_resolve_convergence()` method (lines 359-405)

### 3.2 Error Handling ⚠

**Rating**: Needs Improvement

**Issues**:

1. **Silent failures in `_resolve_convergence()`**:
   ```python
   quantity_values = jmespath.search('.'.join(quantity_path[:-1]), archive)
   if quantity_values is None:
       continue  # ← Silent skip, no logging
   ```
   **Location**: `workflow/general.py:379-381`

2. **Incomplete type checking**:
   ```python
   if (isinstance(convergence_data, Iterable) and
       hasattr(convergence_data, '__getitem__') and  # TODO this is all due to the type checker
       hasattr(convergence_data, 'shape') and
       len(convergence_data.shape) > 0):
   ```
   **Location**: `workflow/general.py:393-399`

   This is a workaround for type checking rather than proper typing.

3. **No validation of threshold units**:
   ```python
   convergence_result.is_reached = (
       convergence_data.to(unit).magnitude < threshold
   )
   ```
   **Location**: `workflow/general.py:401-403`

   Will raise exception if `unit` is invalid, not caught.

### 3.3 Edge Cases ⚠

**Rating**: Needs Improvement

**Untested scenarios**:

1. **Missing convergence data**: What if `scf_steps` is `None`?
2. **Mismatched units**: What if parser uses different units than expected?
3. **Empty arrays**: What if `delta_energies_total` is `[]`?
4. **Non-converged calculations**: Do workflows handle incomplete runs?
5. **Mixed convergence states**: Some targets reached, others not

### 3.4 Performance Considerations ✓

**Rating**: Good

**Observations**:
- JMESPath queries are relatively efficient
- Array-based `SCFSteps` is more memory efficient than nested `Outputs`
- Task generation is O(n²) in worst case (nested loop lines 289-311 in workflow/general.py) but acceptable for typical workflow sizes

---

## 4. Test Coverage Gaps

### 4.1 Current Test Status

**Baseline tests**: ✓ 175/175 passing
- `test_general.py`: 30 tests
- `test_numerical_settings.py`: 45 tests
- `test_physical_properties.py`: 25 tests
- `test_outputs.py`: 14 tests
- `test_atoms_state.py`: 29 tests
- `test_basis_set.py`: 32 tests

**Workflow tests**: ✗ Cannot run (abinit parser blocks test collection)

**Tests removed**: 169 lines from `test_outputs.py`
- Entire `TestSCFOutputs` class deleted
- `test_get_last_scf_steps_value()` (7 test cases)
- `test_resolve_is_scf_converged()` (5 test cases)
- `test_normalize()` (4 test cases)

**Tests added**: 0 lines

### 4.2 Critical Missing Tests ✗

**Priority 1: Core convergence functionality**

1. **Test `WorkflowConvergenceTarget` creation**:
   - Valid parameter names and threshold types
   - Invalid combinations
   - Unit handling

2. **Test `_resolve_convergence()` method**:
   - Successful convergence detection
   - Failed convergence detection
   - Missing data scenarios
   - Unit conversion edge cases
   - JMESPath query failures

3. **Test `map_convergence()` integration**:
   - Setting `is_converged` flag correctly
   - Multiple convergence targets
   - Partial convergence (some targets met, others not)

4. **Test `SCFSteps` data structure**:
   - Parsing from simulation output
   - Array shapes and units
   - Missing optional fields

**Priority 2: Workflow integration**

5. **Test `GeometryOptimization.map_tasks()`**:
   - SinglePoint task creation for SCF outputs
   - Generic Task creation for non-SCF outputs
   - Convergence target propagation
   - Task linking based on timing

6. **Test `GeometryOptimization` convergence**:
   - `is_single_point_converged` flag
   - Independent SCF vs geometry convergence
   - Mixed convergence states

7. **Test `SinglePoint` convergence**:
   - Simple SCF convergence case
   - Non-converged case
   - Missing convergence targets

**Priority 3: Edge cases**

8. **Test error scenarios**:
   - Invalid JMESPath queries
   - Missing `scf_steps` data
   - Mismatched units
   - Empty convergence targets
   - Archive structure variations

9. **Test backward compatibility**:
   - Old archives without convergence data
   - Mixed old/new data structures

### 4.3 Test Coverage Recommendations

**Suggested test structure**:

```python
# tests/workflow/test_convergence.py (NEW FILE)

class TestWorkflowConvergenceTarget:
    """Test convergence target schema and validation."""

    @pytest.mark.parametrize('parameter,threshold_type', [
        ('energy', 'absolute'),
        ('force', 'maximum'),
        ('potential', 'rms'),
        ('charge', 'absolute'),
        ('density', 'rms'),
    ])
    def test_valid_convergence_target(self, parameter, threshold_type):
        ...

    def test_threshold_unit_handling(self):
        ...

class TestWorkflowConvergenceResults:
    """Test convergence result creation and evaluation."""

    def test_convergence_reached(self):
        ...

    def test_convergence_not_reached(self):
        ...

    def test_missing_data(self):
        ...

class TestSimulationWorkflowConvergence:
    """Test convergence integration in workflows."""

    def test_map_convergence_single_target(self):
        ...

    def test_map_convergence_multiple_targets(self):
        ...

    def test_partial_convergence(self):
        ...

    def test_missing_convergence_data(self):
        ...

class TestGeometryOptimizationConvergence:
    """Test convergence in geometry optimization workflows."""

    def test_map_tasks_with_scf(self):
        ...

    def test_map_tasks_without_scf(self):
        ...

    def test_single_point_convergence_propagation(self):
        ...

    def test_is_single_point_converged(self):
        ...

class TestSCFSteps:
    """Test SCFSteps data structure."""

    def test_scf_steps_arrays(self):
        ...

    def test_scf_steps_units(self):
        ...

    def test_scf_steps_code_specific(self):
        ...
```

---

## 5. Code Organization Issues

### 5.1 Unresolved TODOs

**Location**: Multiple files

1. **`workflow/general.py:149`**:
   ```python
   # TODO: Is this nomad_simulations.common.SimulationTime ?
   class WorkflowTime(ArchiveSection):
   ```
   **Issue**: Duplication with existing `SimulationTime` and new fields in `BaseSimulation`.
   **Recommendation**: Consolidate time-related fields into a single, well-defined location.

2. **`workflow/general.py:487`**:
   ```python
   # TODO @all: Does this belong here?
   class ElectronicStructureResults(SimulationWorkflowResults):
   ```
   **Issue**: Specific result type in general workflow module.
   **Recommendation**: Move to electronic structure specific module or justify placement.

3. **`outputs.py:42-43`**:
   ```python
   # MK: I don't think this should live here.
   # @all: where to move this?
   class SCFSteps(ArchiveSection):
   ```
   **Issue**: Author uncertain about placement.
   **Recommendation**: Move to dedicated SCF module or workflow module.

4. **`outputs.py:49`**:
   ```python
   # @ND: Should this be of type TotalEnergy? Do we have a type system for this?
   energies_total = Quantity(shape=['*'], type=float, unit='joule')
   ```
   **Issue**: Type system design question.
   **Recommendation**: Investigate existing type system and apply consistently.

5. **`workflow/general.py:389`**:
   ```python
   # TODO @all: For some reason threshold is just a value and not a quantity
   # I don't know how or where to fix this
   ```
   **Issue**: Unit information lost during processing (CRITICAL).
   **Recommendation**: Store threshold as Quantity or ensure unit preservation in workflow.

6. **`workflow/general.py:73`**:
   ```python
   # TODO @ND: Do all of them apply?
   threshold_type = Quantity(type=MEnum('absolute', 'relative', 'maximum', 'rms', 'residuum'), ...)
   ```
   **Issue**: Uncertain if all threshold types are applicable.
   **Recommendation**: Validate with domain experts, potentially restrict per parameter type.

### 5.2 Naming and Documentation

**Issues**:

1. **`WorkflowTime` vs `SimulationTime`**: Overlapping purposes, unclear distinction
2. **`SCFSteps` location**: In `outputs.py` but feels like workflow/scf concern
3. **`_resolve_convergence()`**: Protected method called from outside class (GeometryOptimization line 230)

---

## 6. Specific Code Review Comments

### workflow/general.py

#### Line 28-34: Hardcoded convergence mapping
```python
CONVERGENCE_QUANTITY_MAPPING = {
    'force:maximum': 'workflow2.results.final_force_maximum',
    'potential:rms': 'data.outputs[*].scf_steps.delta_potential_rms',
    ...
}
```

**Issue**: Hardcoded archive paths couple convergence system to specific schema structure.
**Severity**: Medium
**Recommendation**: Consider making this configurable or using a more flexible lookup mechanism.

#### Line 359-405: `_resolve_convergence()` complexity
**Issue**: Method has multiple responsibilities and complex logic.
**Severity**: Low
**Recommendation**: Consider breaking into smaller helper methods:
- `_extract_convergence_data()`
- `_evaluate_convergence_threshold()`
- `_create_convergence_result()`

#### Line 374-385: Manual path handling
```python
# do last step of path manually because jmespath only returns the raw values
# and not quantites - TODO this is pretty much a hack
quantity_path = CONVERGENCE_QUANTITY_MAPPING[...].split('.')
quantity_name = quantity_path[-1]
quantity_values = jmespath.search('.'.join(quantity_path[:-1]), archive)
```

**Issue**: Hybrid JMESPath + manual approach feels awkward.
**Severity**: Medium
**Recommendation**: Either fully embrace JMESPath or use manual path traversal throughout for consistency.

#### Line 335: Silent JMESPath usage
```python
all_reached = all(jmespath.search('[*].is_reached', convergence_results))
```

**Issue**: JMESPath used without null checking.
**Severity**: Low
**Recommendation**: Add null check or document that convergence_results is guaranteed non-empty here.

### workflow/geometry_optimization.py

#### Line 220-233: Task type determination
```python
if output.get('scf_steps') is not None:
    task = SinglePoint(...)
    single_point_convergence = jmespath.search('workflow2.method.single_point_convergence', archive)
    if single_point_convergence is not None:
        single_point_convergence_result = task._resolve_convergence(...)
```

**Issue**: Calling protected method `_resolve_convergence()` from outside class.
**Severity**: Medium
**Recommendation**: Make method public or refactor to use public API.

#### Line 262-268: Convergence aggregation
```python
single_point_convergence_results = jmespath.search(
    'workflow2.tasks[*].results.convergence[*].is_reached', archive
)
...
all_scf_converged = all(all(x) for x in single_point_convergence_results)
```

**Issue**: Nested `all()` is elegant but fragile if structure changes.
**Severity**: Low
**Recommendation**: Add null checks and consider explicit iteration for clarity.

#### Line 166-170: Force extraction using JMESPath
```python
if self.final_force_maximum is None:
    final_forces = jmespath.search('data.outputs[-1].total_forces[-1]', archive)
    if final_forces is not None:
        force_abs = np.linalg.norm(final_forces.value, axis=1)
        self.final_force_maximum = max(force_abs)
```

**Issue**: Assumes `final_forces` has `.value` attribute and correct shape.
**Severity**: Low
**Recommendation**: Add error handling for AttributeError and shape mismatches.

### outputs.py

#### Line 44-110: SCFSteps definition
**Issue**: Well-defined structure, but placement questioned by author.
**Severity**: Low
**Recommendation**: Resolve placement question before merge (see 5.1.3).

#### Line 199: scf_steps subsection
```python
scf_steps = SubSection(sub_section=SCFSteps.m_def, repeats=False)
```

**Question**: Why `repeats=False`? Could there be multiple SCF convergence attempts?
**Recommendation**: Document decision in docstring.

### physical_property.py

#### Line 102-108: `is_converged` field
```python
# TODO: should this information be obtained from the normalize method?
is_converged = Quantity(type=bool, description="""
    Flag indicating whether the calculation that yields this physical property is converged
    or not after a SCF or optimization process. This information is obtained from the workflow section.
""")
```

**Issue**: TODO suggests uncertainty about design.
**Severity**: Low
**Recommendation**: Clarify ownership: is convergence a property of the property or the workflow that produced it?

---

## 7. Recommendations

### 7.1 Critical (Must Fix Before Merge)

1. **Fix abinit parser** ✗
   - Update parser to use `WorkflowConvergenceTarget` API
   - Test that all parsers load successfully
   - **Estimated effort**: 2-4 hours

2. **Add comprehensive tests** ✗
   - Implement test suite as outlined in section 4.3
   - Minimum coverage: core convergence functionality (Priority 1)
   - **Estimated effort**: 1-2 days

3. **Resolve unit handling** ✗
   - Fix threshold quantity loss (TODO line 389)
   - Ensure units are preserved throughout convergence checking
   - **Estimated effort**: 4-8 hours

### 7.2 High Priority (Should Fix Before Merge)

4. **Document breaking changes** ⚠
   - Create migration guide for parser developers
   - Document API changes in CHANGELOG
   - Add examples of converting from old to new API
   - **Estimated effort**: 4-6 hours

5. **Resolve code organization TODOs** ⚠
   - Decide on `SCFSteps` placement
   - Consolidate time-related fields
   - Move `ElectronicStructureResults` or justify placement
   - **Estimated effort**: 2-3 hours

6. **Improve error handling** ⚠
   - Add null checks and error logging in `_resolve_convergence()`
   - Validate units before conversion
   - Handle missing data gracefully
   - **Estimated effort**: 3-4 hours

### 7.3 Medium Priority (Nice to Have)

7. **Refactor convergence resolution** ⚠
   - Break down `_resolve_convergence()` into smaller methods
   - Make method public or refactor API
   - Improve type hints to avoid hasattr checks
   - **Estimated effort**: 3-4 hours

8. **Review JMESPath usage** ⚠
   - Decide on consistent query approach (full JMESPath vs hybrid)
   - Consider caching compiled queries for performance
   - Document query patterns
   - **Estimated effort**: 2-3 hours

9. **Add integration tests** ⚠
   - Test with real parser outputs (exciting, VASP, etc.)
   - Test backward compatibility with old archives
   - **Estimated effort**: 1 day

### 7.4 Low Priority (Future Work)

10. **Consider convergence criteria extensibility** ℹ
    - Allow custom convergence parameters beyond MEnum
    - Support parser-specific convergence logic
    - **Estimated effort**: 1-2 days

11. **Performance profiling** ℹ
    - Profile JMESPath queries on large archives
    - Optimize task generation if needed
    - **Estimated effort**: 0.5 day

---

## 8. Conclusion

### Summary Assessment

| Category | Rating | Status |
|----------|--------|--------|
| **Architecture** | ✓ Good | Well-designed target-result pattern |
| **Implementation** | ⚠ Mixed | Solid code, but TODOs and edge cases |
| **Testing** | ✗ Poor | Zero coverage for new functionality |
| **Breaking Changes** | ✗ Poor | Undocumented, abinit parser broken |
| **Code Quality** | ✓ Good | Clean, well-documented, type-hinted |
| **Error Handling** | ⚠ Needs Work | Silent failures, incomplete validation |

### Merge Readiness: **NOT READY**

**Blocking Issues**:
1. Abinit parser completely broken
2. Zero test coverage for convergence system
3. Unit handling bug (threshold loses quantity info)

**Estimated Work to Merge**: 3-5 days
- Fix parser: 2-4 hours
- Add tests: 1-2 days
- Fix unit handling: 4-8 hours
- Documentation: 4-6 hours
- Code organization: 2-3 hours
- Error handling: 3-4 hours

### Recommendation

**Do not merge** until:
1. ✗ Abinit parser updated and all parsers load successfully
2. ✗ Comprehensive test suite added (minimum: Priority 1 tests from section 4.3)
3. ✗ Unit handling fixed (threshold as Quantity)
4. ⚠ Migration guide documented
5. ⚠ Code organization TODOs resolved

The architectural direction is sound and addresses real issues with scattered convergence handling. However, the implementation needs additional work to be production-ready. The lack of tests is particularly concerning given the scope of changes.

### Next Steps

1. **Author**: Address critical blockers (abinit, tests, units)
2. **Author**: Resolve TODOs and document migration
3. **Reviewer**: Re-review after updates
4. **Team**: Validate with parser maintainers before final merge

---

## Appendix A: Files Modified

### Core Schema Changes (6 files)
1. `src/nomad_simulations/schema_packages/general.py` (+69/-0)
2. `src/nomad_simulations/schema_packages/workflow/general.py` (+177/-15)
3. `src/nomad_simulations/schema_packages/workflow/geometry_optimization.py` (+106/-46)
4. `src/nomad_simulations/schema_packages/outputs.py` (+77/-140)
5. `src/nomad_simulations/schema_packages/numerical_settings.py` (+1/-51)
6. `src/nomad_simulations/schema_packages/physical_property.py` (+5/-13)

### Cleanup Changes (5 files)
7. `src/nomad_simulations/schema_packages/atoms_state.py` (+0/-3)
8. `src/nomad_simulations/schema_packages/model_method.py` (+0/-6)
9. `src/nomad_simulations/schema_packages/variables.py` (+0/-24)
10. `src/nomad_simulations/schema_packages/basis_set.py` (+10/-10)
11-12. `src/nomad_simulations/schema_packages/properties/*.py` (empty normalize removals)

### Test Changes (2 files)
13. `tests/conftest.py` (+2/-47)
14. `tests/test_outputs.py` (+1/-169)

**Total**: +443/-534 lines (net -91)

---

## Appendix B: Convergence System API

### For Parser Developers

#### Old API (removed):
```python
from nomad_simulations.schema_packages.numerical_settings import SelfConsistency
from nomad_simulations.schema_packages.outputs import SCFOutputs

# Convergence settings
scf_settings = SelfConsistency()
scf_settings.n_max_iterations = 100
scf_settings.threshold_change = 1e-6
scf_settings.threshold_change_unit = 'eV'

# SCF outputs with nested steps
scf_outputs = SCFOutputs()
for step_data in scf_steps:
    step_output = Outputs()
    step_output.total_energies = [TotalEnergy(value=...)]
    scf_outputs.scf_steps.append(step_output)
```

#### New API (use this):
```python
from nomad_simulations.schema_packages.workflow.general import WorkflowConvergenceTarget
from nomad_simulations.schema_packages.outputs import Outputs, SCFSteps

# Convergence target (in workflow method section)
convergence_target = WorkflowConvergenceTarget()
convergence_target.convergence_parameter_name = 'energy'
convergence_target.threshold_type = 'absolute'
convergence_target.convergence_threshold = 1e-6
convergence_target.threshold_unit = 'eV'
workflow.method.convergence.append(convergence_target)

# SCF data (in output section)
output = Outputs()
output.scf_steps = SCFSteps()
output.scf_steps.energies_total = [1.0, 0.5, 0.2, 0.1] * ureg.eV
output.scf_steps.delta_energies_total = [0.5, 0.3, 0.1, 0.05] * ureg.eV
```

#### Convergence checking:
```python
# Old: manual checking in SCFOutputs.resolve_is_scf_converged()
# New: automatic during workflow.normalize()
workflow.normalize(archive, logger)
# Results:
# - workflow.results.is_converged (bool)
# - workflow.results.convergence (list of WorkflowConvergenceResults)
```

---

*End of Review*
