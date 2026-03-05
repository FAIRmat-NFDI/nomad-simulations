import numpy as np
import pint
from nomad.datamodel import ArchiveSection, EntryArchive
from nomad.datamodel.metainfo.workflow import Link, Task, TaskReference, Workflow
from nomad.metainfo import Datetime, MEnum, Quantity, SchemaPackage, SubSection
from nomad.units import ureg
from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.data_types import positive_float
from nomad_simulations.schema_packages.model_method import ModelMethod
from nomad_simulations.schema_packages.model_system import ModelSystem
from nomad_simulations.schema_packages.properties import ElectronicDensityOfStates
from nomad_simulations.schema_packages.utils import log
from nomad_simulations.schema_packages.workflow.trajectory import (
    FreeEnergyCalculations,
    Pressures,
    RadiiOfGyration,
    Temperatures,
)

# TODO make this a function to check required number of tasks
INCORRECT_N_TASKS = 'Incorrect number of tasks found.'

m_package = SchemaPackage()


class SimulationTask(Task):
    pass


class WorkflowConvergenceTarget(ArchiveSection):
    """
    Base section for defining convergence targets.
    It handles all convergence checking logic based on `threshold_type`.

    Use inheritance todefine specific physical properties (e.g., energy, force).
    This is most relevant when defining the appropriate units.
    """

    threshold: Quantity = (
        None  # to be defined in child classes with appropriate type and unit
    )

    threshold_type = Quantity(
        type=MEnum('absolute', 'relative', 'maximum', 'rms'),
        description=r"""Specifies the mathematical method used to evaluate convergence between successive self-consistent field (SCF) iterations.
This determines how differences between iterations are calculated and compared against the convergence threshold.

The available comparison modes are:

| Mode | Description |
| --------- | -------------------------------- |
| `'absolute'` | Measures the absolute difference between two subsequent iterations (e.g., \|E_n - E_{n-1}\|). Most common for energy convergence. |
| `'relative'` | Calculates the relative difference as a fraction of the total property value (e.g., \|E_n - E_{n-1}\|/\|E_n\|). Useful when the magnitude of the property varies widely across systems. |
| `'maximum'` | Reports the maximum absolute difference across all components of a multi-component property (e.g., max\|F_i,n - F_i,{n-1}\| for forces). Suitable for vector quantities like forces or stress tensor elements. |
| `'rms'` | Calculates the root mean square of differences across all components (e.g., √(∑\|F_i,n - F_i,{n-1}\|²/N)). Provides a statistical measure of overall convergence for multi-component properties. |

The mode used affects both convergence behavior and computational efficiency. Different codes may default to different comparison modes for the same physical property.
        """,
    )

    @staticmethod
    def _is_scalar_pint(value) -> bool:
        """
        Check if a Pint Quantity contains a scalar value or an array.

        Args:
            value: The value to check (expected to be a Pint Quantity)

        Returns:
            True if scalar Pint Quantity, False if array Pint Quantity
        """
        if hasattr(value, 'magnitude'):
            return np.isscalar(value.magnitude)
        # Fallback for non-Pint values
        return np.isscalar(value)

    def _get_convergence_value(self, archive: EntryArchive, logger: BoundLogger):
        """
        Extract the value to check for convergence from the archive.

        Uses the path(s) defined in the `a_convergence` annotation on the threshold
        Quantity to locate convergence data. Supports fallback paths - if the first
        path returns None, tries subsequent paths.

        Annotation format:
        - Single path: `a_convergence={'path': '@.scf_steps.delta_energies_total'}`
        - Fallback paths: `a_convergence={'paths': ['workflow2.results.X', '@.scf_steps.X']}`

        Path notation (JMESPath-inspired, uses `getattr()` for navigation):
        - `@.scf_steps.delta_energies_total` - Relative to `archive.data.outputs[-1]` (current output)
        - `workflow2.results.X` or `archive.X` - Absolute from archive root

        The `@` prefix follows JMESPath convention where `@` represents the current node.
        All paths must have an explicit prefix (`@.`, `workflow2.`, or `archive.`).
        Uses direct attribute access via `getattr()` to preserve Pint Quantity units.

        Returns:
            The value to check as a Pint Quantity (with units),
            or None if the value cannot be determined.
        """
        # Access annotation from the threshold Quantity definition
        threshold_quantity = self.m_def.all_quantities.get('threshold')
        if not threshold_quantity:
            logger.warning(
                f'No threshold quantity found for {self.__class__.__name__}',
                data={'class': self.__class__.__name__},
            )
            return None

        annotation = threshold_quantity.m_get_annotation('convergence')
        if not annotation:
            logger.warning(
                f'No convergence annotation on threshold for {self.__class__.__name__}',
                data={'class': self.__class__.__name__},
            )
            return None

        # Support both 'path' (single) and 'paths' (fallback list)
        paths = []
        if 'paths' in annotation:
            paths = (
                annotation['paths']
                if isinstance(annotation['paths'], list)
                else [annotation['paths']]
            )
        elif 'path' in annotation:
            paths = [annotation['path']]
        else:
            logger.warning(
                f'No path or paths in convergence annotation for {self.__class__.__name__}',
                data={'class': self.__class__.__name__},
            )
            return None

        # Try each path in order (fallback logic)
        for path in paths:
            value = self._resolve_path(archive, path, logger)
            if value is not None:
                # Handle arrays: for 'absolute' threshold_type, extract last iteration value
                # For 'rms' and 'maximum', keep full array for aggregation
                conv_type = self.threshold_type or 'absolute'
                if hasattr(value, '__getitem__') and not isinstance(value, str):
                    if conv_type in ('rms', 'maximum'):
                        return value  # Keep full array
                    else:
                        return value[-1]  # Extract last iteration value
                return value

        # All paths failed
        logger.debug(
            f'All convergence paths resolved to None',
            data={'paths': paths, 'class': self.__class__.__name__},
        )
        return None

    def _resolve_path(self, archive: EntryArchive, path: str, logger: BoundLogger):
        """
        Resolve a single path in the archive.

        Paths are dot-notation strings with required prefixes (JMESPath-inspired):
        - `@.scf_steps.X` - Relative to `archive.data.outputs[-1]` (current output)
        - `workflow2.X` or `archive.X` - Absolute from archive root

        The `@` prefix follows JMESPath convention where `@` represents the current node.
        All paths must have an explicit prefix.

        Args:
            archive: The archive to search
            path: Dot-notation path string with required prefix
            logger: Logger instance

        Returns:
            The value at the path, or None if not found
        """
        try:
            # Determine starting point based on path prefix
            if path.startswith('@.'):
                # Explicit relative path (JMESPath-inspired current node)
                if not archive.data or not archive.data.outputs:
                    return None
                root = archive.data.outputs[-1]
                path_parts = path[2:].split('.')  # Strip '@.' prefix
            elif path.startswith('workflow2.') or path.startswith('archive.'):
                # Absolute path from archive root
                root = archive
                path_parts = path.split('.')
            else:
                # No valid prefix - path must be explicit
                logger.warning(
                    f'Convergence path missing required prefix (@., workflow2., or archive.): {path}',
                    data={'path': path, 'class': self.__class__.__name__},
                )
                return None

            # Navigate the path
            value = root
            for part in path_parts:
                value = getattr(value, part, None)
                if value is None:
                    return None

            return value

        except Exception as e:
            logger.debug(
                f'Failed to resolve path',
                data={'path': path, 'error': str(e), 'class': self.__class__.__name__},
            )
            return None

    def _check_absolute(self, value, logger: BoundLogger) -> bool | None:
        """Check absolute convergence: |value| < threshold"""
        if self.threshold is None:
            return None
        try:
            # Handle unit mismatches between value and threshold
            value_has_units = hasattr(value, 'magnitude')
            threshold_has_units = hasattr(self.threshold, 'magnitude')

            if value_has_units and not threshold_has_units:
                # Value has units, threshold doesn't - compare magnitudes
                return bool(abs(value.magnitude) <= self.threshold)
            elif not value_has_units and threshold_has_units:
                # Threshold has units, value doesn't - compare with threshold magnitude
                return bool(abs(value) <= self.threshold.magnitude)
            elif not value_has_units and not threshold_has_units:
                # Neither has units - direct comparison
                return bool(abs(value) <= self.threshold)
            else:
                # Both have units - Pint handles unit conversion
                return bool(abs(value) <= self.threshold)
        except (pint.DimensionalityError, ValueError) as e:
            logger.error(
                f'Unit mismatch or comparison error in {self.__class__.__name__}: {e}'
            )
            return None

    def _check_relative(self, value, reference, logger: BoundLogger) -> bool | None:
        """Check relative convergence: |value|/|reference| < threshold"""
        if self.threshold is None:
            return None
        try:
            # Check if reference is effectively zero (unit-aware)
            ref_epsilon = 1e-15 * reference.units
            if abs(reference) < ref_epsilon:
                # Special case: both zero means converged
                val_epsilon = 1e-15 * value.units
                if abs(value) < val_epsilon:
                    return True
                # Cannot compute relative if reference is zero
                return None

            # Compute relative change (dimensionless)
            relative_change = abs(value / reference)

            # For relative convergence, compare with threshold magnitude
            # (threshold may have units from the Quantity definition but should be treated as dimensionless)
            threshold_value = (
                self.threshold.magnitude
                if hasattr(self.threshold, 'magnitude')
                else self.threshold
            )

            return bool(relative_change < threshold_value)
        except (pint.DimensionalityError, ValueError) as e:
            logger.error(
                f'Unit mismatch or comparison error in {self.__class__.__name__}: {e}'
            )
            return None

    def _check_maximum(self, values, logger: BoundLogger) -> bool | None:
        """Check maximum convergence: max(|values|) < threshold"""
        if self.threshold is None:
            return None
        try:
            # Convert list to numpy array if needed (preserves Pint quantities)
            if isinstance(values, list):
                if len(values) > 0 and hasattr(values[0], 'magnitude'):
                    # Pint quantity list - extract magnitudes and units
                    magnitudes = [v.magnitude for v in values]
                    units = values[0].units
                    values = np.array(magnitudes) * units
                else:
                    values = np.array(values)

            max_value = np.max(np.abs(values))

            # Handle unit mismatches
            value_has_units = hasattr(max_value, 'magnitude')
            threshold_has_units = hasattr(self.threshold, 'magnitude')

            if value_has_units and not threshold_has_units:
                return bool(max_value.magnitude < self.threshold)
            elif not value_has_units and threshold_has_units:
                return bool(max_value < self.threshold.magnitude)
            else:
                # Both have units or both don't - direct comparison
                return bool(max_value < self.threshold)
        except (pint.DimensionalityError, ValueError, TypeError) as e:
            logger.error(
                f'Unit mismatch or comparison error in {self.__class__.__name__}: {e}'
            )
            return None

    def _check_rms(self, values, logger: BoundLogger) -> bool | None:
        """Check RMS convergence: sqrt(mean(values²)) < threshold"""
        if self.threshold is None:
            return None
        try:
            # Convert list to numpy array if needed (preserves Pint quantities)
            if isinstance(values, list):
                if len(values) > 0 and hasattr(values[0], 'magnitude'):
                    # Pint quantity list - extract magnitudes and units
                    magnitudes = [v.magnitude for v in values]
                    units = values[0].units
                    values = np.array(magnitudes) * units
                else:
                    values = np.array(values)

            rms_value = np.sqrt(np.mean(values**2))

            # Handle unit mismatches
            value_has_units = hasattr(rms_value, 'magnitude')
            threshold_has_units = hasattr(self.threshold, 'magnitude')

            if value_has_units and not threshold_has_units:
                return bool(rms_value.magnitude < self.threshold)
            elif not value_has_units and threshold_has_units:
                return bool(rms_value < self.threshold.magnitude)
            else:
                # Both have units or both don't - direct comparison
                return bool(rms_value < self.threshold)
        except (pint.DimensionalityError, ValueError, TypeError) as e:
            logger.error(
                f'Unit mismatch or comparison error in {self.__class__.__name__}: {e}'
            )
            return None

    def normalize(self, archive: EntryArchive, logger: BoundLogger) -> bool | None:
        """
        Check if convergence criterion is met.

        Returns:
            True if converged, False if not, None if cannot be determined.
        """
        if not archive.data:
            return None

        try:
            value = self._get_convergence_value(archive, logger)
            if value is None:
                return None

            conv_type = self.threshold_type or 'absolute'

            # Handle scalar vs array values using Pint-aware detection
            if self._is_scalar_pint(value):
                # Scalar value - use absolute or relative
                if conv_type == 'absolute':
                    return self._check_absolute(value, logger)
                elif conv_type == 'relative':
                    # For relative, child class should provide reference
                    logger.warning(
                        f'Relative convergence requires reference value in '
                        f'{self.__class__.__name__}'
                    )
                    return None
                else:
                    return self._check_absolute(value, logger)

            else:
                # Array value - can use maximum or rms
                if conv_type == 'maximum':
                    return self._check_maximum(value, logger)
                elif conv_type == 'rms':
                    return self._check_rms(value, logger)
                elif conv_type == 'absolute':
                    # For array, treat as maximum
                    return self._check_maximum(value, logger)
                else:
                    return self._check_maximum(value, logger)

        except Exception as e:
            logger.debug(
                f'Could not check convergence for {self.__class__.__name__}: {e}'
            )
        return None


class EnergyConvergenceTarget(WorkflowConvergenceTarget):
    """
    Convergence target for energy in SCF or optimization workflows.
    The threshold_type determines how energy convergence is evaluated.
    """

    threshold = Quantity(
        type=positive_float(),
        unit='joule',
        description="""
        Energy convergence threshold. Must be non-negative.
        """,
        a_convergence={'path': '@.scf_steps.delta_energies_total'},
    )


class ForceConvergenceTarget(WorkflowConvergenceTarget):
    """
    Convergence target for forces in optimization or SCF workflows.
    The threshold_type determines how force convergence is evaluated.
    """

    threshold = Quantity(
        type=positive_float(),
        unit='newton',
        description="""
        Force convergence threshold. Must be non-negative.
        """,
        a_convergence={
            'paths': [
                'workflow2.results.final_force_maximum',  # Absolute: workflow level
                '@.scf_steps.delta_force_abs',  # Relative: SCF level
            ]
        },
    )

    def _get_convergence_value(self, archive: EntryArchive, logger: BoundLogger):
        """
        Extract force convergence value from archive.

        Uses fallback paths from annotation, then computes from total_forces if needed.
        """
        # Try annotation-based fallback paths first
        value = super()._get_convergence_value(archive, logger)
        if value is not None:
            return value

        # Final fallback: compute force norms from total_forces
        try:
            if archive.data and archive.data.outputs:
                forces = archive.data.outputs[-1].total_forces
                if forces is not None and len(forces) > 0:
                    # Get force values (Pint Quantity with shape [n_atoms, 3])
                    force_values = forces[-1].value
                    # Compute norm per atom using Pint-native operations
                    force_magnitudes = ((force_values**2).sum(axis=1)) ** 0.5
                    return force_magnitudes
        except (AttributeError, IndexError, TypeError) as e:
            logger.debug(f'Could not extract force convergence value: {e}')

        return None


class PotentialConvergenceTarget(WorkflowConvergenceTarget):
    """
    Convergence target for potential in SCF workflows.
    The threshold_type determines how potential convergence is evaluated.
    """

    threshold = Quantity(
        type=positive_float(),
        unit='joule',
        description="""
        Potential convergence threshold. Must be non-negative.
        """,
        a_convergence={'path': '@.scf_steps.delta_potential_rms'},
    )


class ChargeConvergenceTarget(WorkflowConvergenceTarget):
    """
    Convergence target for charge/electron density in SCF workflows.
    The threshold_type determines how density convergence is evaluated.
    """

    threshold = Quantity(
        type=positive_float(),
        unit='coulomb',
        description="""
        Charge/density convergence threshold. Must be non-negative.
        """,
        a_convergence={'path': '@.scf_steps.delta_density_rms'},
    )


class WavefunctionConvergenceTarget(WorkflowConvergenceTarget):
    """
    Convergence target for wavefunction coefficients in SCF workflows.

    Measures convergence of wavefunction or orbital coefficients between
    successive SCF iterations. This is less commonly reported than density
    convergence but is available in some quantum chemistry codes.

    Note: This is distinct from density convergence. Some codes report both
    wavefunction and density convergence independently.
    """

    threshold = Quantity(
        type=positive_float(),
        unit='dimensionless',
        description="""
        Wavefunction convergence threshold. Must be non-negative.
        Typically dimensionless as it represents changes in wavefunction coefficients.
        """,
        a_convergence={'path': '@.scf_steps.delta_wavefunction_rms'},
    )


class SimulationWorkflowModel(ArchiveSection):
    """
    Base class for simulation workflow model sub-section definition.
    """

    _label = 'Input model'

    initial_system = Quantity(
        type=ModelSystem,
        description="""
        Reference to the input model_system.
        """,
    )

    initial_method = Quantity(
        type=ModelMethod,
        description="""
        Reference to the input model_method.
        """,
    )

    convergence_targets = SubSection(
        sub_section=WorkflowConvergenceTarget.m_def, repeats=True
    )

    def normalize(self, archive: EntryArchive, logger: BoundLogger) -> None:
        if not archive.data:
            return

        # set references to initial system and method
        if not self.initial_system and archive.data.model_system:
            self.initial_system = archive.data.model_system[0]
        if not self.initial_method and archive.data.model_method:
            self.initial_method = archive.data.model_method[0]


# Backwards-compatible alias used across workflows/tests.
class SimulationWorkflowMethod(SimulationWorkflowModel):
    pass


# TODO: Is this nomad_simulations.common.SimulationTime ?
class WorkflowTime(ArchiveSection):
    """
    Contains time-related quantities.
    """

    datetime_end = Quantity(
        type=Datetime,
        description="""
        The date and time when the workflow ended.
        """,
    )

    cpu1_start = Quantity(
        type=np.float64,
        unit='second',
        description="""
        The starting time of the workflow on the (first) CPU 1.
        """,
    )

    cpu1_end = Quantity(
        type=np.float64,
        unit='second',
        description="""
        The end time of the workflow on the (first) CPU 1.
        """,
    )

    wall_start = Quantity(
        type=np.float64,
        unit='second',
        description="""
        The internal wall-clock time from the starting of the workflow.
        """,
    )

    wall_end = Quantity(
        type=np.float64,
        unit='second',
        description="""
        The internal wall-clock time from the end of the workflow.
        """,
    )


class WorkflowConvergenceResults(ArchiveSection):
    """
    Results of workflow convergence checks.

    This class allows for flexible convergence result reporting, especially useful
    in nested workflow hierarchies where convergence results may need to be
    aggregated from multiple sources or represent composite convergence criteria.

    For simple cases, convergence targets can use their built-in `is_reached` field.
    For complex cases (e.g., nested workflows), use this class to reference targets
    and provide aggregated results.
    """

    convergence_target_ref = Quantity(
        type=WorkflowConvergenceTarget,
        description="""
        Reference to the workflow convergence target that this result corresponds to.
        """,
    )

    is_reached = Quantity(
        type=bool,
        description="""
        Indicates whether this convergence target was reached (True) or not (False).
        """,
    )


class SimulationWorkflowResults(WorkflowTime):
    """
    Base class for simulation workflow results sub-section definition.
    """

    _label = 'Workflow results'

    finished_normally = Quantity(
        type=bool,
        shape=[],
        description="""
        Indicates if calculation terminated normally.
        """,
    )

    is_converged = Quantity(
        type=bool,
        description="""
        Represents if the convergence targets have been reached (True) or not (False).
        """,
    )

    convergence = SubSection(
        sub_section=WorkflowConvergenceResults.m_def,
        repeats=True,
        description="""
        Convergence results for workflows.
        Each result references a convergence target and stores its reached status.
        """,
    )

    def get_convergence_value(
        self,
        property_name: str,
        threshold_type: str,
        archive: 'EntryArchive',
        logger: 'BoundLogger',
    ) -> Quantity | None:
        """
        Extract convergence value for checking against convergence targets.

        This method provides a standardized interface for convergence targets to
        retrieve convergence values without needing to know the internal archive
        structure. Subclasses override this to implement workflow-specific logic.

        The default implementation handles SCF-based workflows by extracting values
        from scf_steps in the last output.

        Args:
            property_name: Physical property to check ('energy', 'force', 'density',
                'potential', 'wavefunction')
            threshold_type: How to compute convergence ('absolute', 'relative',
                'maximum', 'rms')
            archive: Entry archive for data access
            logger: For logging warnings

        Returns:
            Convergence value ready for threshold comparison, or None if unavailable.

        Example:
            >>> # In WorkflowConvergenceTarget.normalize()
            >>> value = archive.workflow2.results.get_convergence_value(
            ...     'energy', 'relative', archive, logger
            ... )
            >>> if value is not None:
            ...     is_converged = value < self.threshold
        """
        # Default implementation returns None
        # Subclasses override for workflow-specific logic
        return None


class SimulationTaskReference(TaskReference, SimulationTask):
    pass


class SimulationWorkflow(Workflow, SimulationTask):
    """
    Base class for simulation workflows.

    It contains sub-sections model and results which are included in inputs and
    outputs, respectively.
    """

    _task_label = 'Task'

    method = SubSection(sub_section=SimulationWorkflowMethod.m_def)

    results = SubSection(sub_section=SimulationWorkflowResults.m_def)

    @log
    def map_inputs(self, archive: EntryArchive, logger: BoundLogger) -> None:
        if not self.method:
            self.method = SimulationWorkflowMethod()

        if self.method in [inp.section for inp in self.inputs]:
            return

        logger = self.map_inputs.__annotations__['logger']
        self.method.normalize(archive, logger)
        # add method to inputs
        self.inputs.append(Link(name=self.method._label, section=self.method))

    @log
    def map_outputs(self, archive: EntryArchive, logger: BoundLogger) -> None:
        if not self.results:
            self.results = SimulationWorkflowResults()

        if self.results in [out.section for out in self.outputs]:
            return

        logger = self.map_outputs.__annotations__['logger']
        self.results.normalize(archive, logger)
        # add results to outputs
        self.outputs.append(Link(name=self.results._label, section=self.results))

    @log
    def map_tasks(self, archive: EntryArchive) -> None:
        """
        Generate tasks from archive data outputs. Tasks are ordered and linked based
        on the execution time of the calculation corresponding to the output.
        """
        # do not overwrite assigned tasks
        if self.tasks:
            return

        if not archive.data or not archive.data.outputs:
            return

        # do not overwrite if tasks are set but give out a warning that it maybe
        # inconsistent with the outputs
        logger = self.map_tasks.__annotations__['logger']
        if self.tasks:
            logger.warning('Tasks are predefined and will not generate from outputs.')
            return

        outputs = list(archive.data.outputs)
        outputs.sort(key=lambda x: x.wall_start or 0)
        tasks = []
        parent_n = 0
        root_n = 0
        for n, output in enumerate(outputs):
            task = SimulationTask(
                name=f'{self._task_label} {n}',
                outputs=[Link(name='Outputs', section=output)],
            )
            tasks.append(task)
            tstart = output.wall_start
            tend = outputs[parent_n].wall_end
            if tstart is None and tend is None:
                continue
            if tstart >= tend:
                task.inputs.extend(
                    [Link(name='Linked task', section=t) for t in tasks[parent_n:n]]
                )
                root_n = parent_n
                parent_n = n
            elif n != parent_n:
                task.inputs.extend(
                    [
                        Link(name='Linked task', section=t)
                        for t in tasks[root_n:parent_n]
                    ]
                )

        self.tasks.extend(tasks)

    @log
    def map_convergence(self, archive: EntryArchive) -> None:
        """
        Normalize convergence targets and determine overall convergence status.
        """
        if not archive.data or not archive.data.outputs:
            return
        logger = self.map_convergence.__annotations__['logger']

        # Get convergence targets from method
        convergence_targets = self.method.get('convergence_targets')
        if not convergence_targets:
            return

        # Normalize each convergence target and collect results
        convergence_status = {}  # Map target -> is_reached
        for target in convergence_targets:
            is_reached = target.normalize(archive, logger)
            convergence_status[target] = is_reached

        # Create WorkflowConvergenceResults if needed.
        if not self.results.convergence:
            convergence_results = []
            for target in convergence_targets:
                result = WorkflowConvergenceResults()
                result.convergence_target_ref = target
                result.is_reached = convergence_status[target]
                convergence_results.append(result)
            if convergence_results:
                self.results.convergence = convergence_results

        # Determine overall convergence status
        all_reached = all(
            convergence_status[target]
            for target in convergence_targets
            if convergence_status[target] is not None
        )
        any_checked = any(
            convergence_status[target] is not None for target in convergence_targets
        )

        if any_checked:
            if self.results.get('is_converged') is None:
                self.results.is_converged = all_reached
            elif self.results.is_converged != all_reached:
                logger.warning(
                    f'Derived convergence ({all_reached}) differs from parsed convergence '
                    f'({self.results.is_converged}).'
                )

    def normalize(self, archive: EntryArchive, logger: BoundLogger):
        """
        Link tasks based on start and end times.
        """
        if not self.name:
            self.name: str = self.m_def.name

        self.map_inputs(archive, logger=logger)

        self.map_outputs(archive, logger=logger)

        self.map_tasks(archive, logger=logger)

        self.map_convergence(archive, logger=logger)

    def _resolve_convergence(
        self,
        archive: EntryArchive,
        convergence_targets: list[WorkflowConvergenceTarget],
        logger: BoundLogger,
    ) -> list[WorkflowConvergenceResults]:
        """
        Helper method to resolve convergence targets for outputs.
        Used primarily for multi-step workflows like geometry optimization.

        Creates temporary copies of convergence targets, normalizes them, and returns
        WorkflowConvergenceResults with the convergence status.
        Note: Currently checks convergence against the last output only.
        """
        convergence_results = []

        for target in convergence_targets:
            # Create a copy of the target to avoid modifying the original
            target_copy = target.m_copy(deep=True)

            # For multi-output scenarios, we may need to adjust the archive context
            # This is a simplified approach - child classes can override for more complex logic
            is_reached = target_copy.normalize(archive, logger)

            # Create a result object that holds both the target and the convergence status
            result = WorkflowConvergenceResults()
            # Reference the original target (which is in the archive hierarchy),
            # not the copy (which would be orphaned and cause serialization errors)
            result.convergence_target_ref = target
            result.is_reached = is_reached
            convergence_results.append(result)

        return convergence_results


class SerialWorkflowResults(SimulationWorkflowResults):
    temperatures = SubSection(sub_section=Temperatures.m_def, repeats=True)

    pressures = SubSection(sub_section=Pressures.m_def, repeats=True)

    radii_of_gyration = SubSection(sub_section=RadiiOfGyration.m_def, repeats=True)

    free_energy_calculations = SubSection(
        sub_section=FreeEnergyCalculations.m_def, repeats=True
    )


class SerialWorkflow(SimulationWorkflow):
    """
    Base class for workflows where tasks are executed sequentially.
    """

    @log
    def map_outputs(self, archive: EntryArchive, logger: BoundLogger) -> None:
        if not self.results:
            self.results = SerialWorkflowResults()
        logger = self.map_outputs.__annotations__['logger']
        super().map_outputs(archive, logger=logger)

    def normalize(self, archive: EntryArchive, logger: BoundLogger) -> None:
        super().normalize(archive, logger)

        if not self.tasks:
            logger.error(INCORRECT_N_TASKS)
            return

        # link tasks sequentially
        for n, task in enumerate(self.tasks):
            if task.inputs:
                continue
            if n == 0:
                inputs = self.inputs
            else:
                previous_task = self.tasks[n - 1]
                inputs = [
                    Link(
                        name='Linked task',
                        section=previous_task.task
                        if isinstance(previous_task, TaskReference)
                        else previous_task,
                    )
                ]

            task.inputs.extend([inp for inp in inputs if inp not in task.inputs])

        # add outputs of last task to outputs
        self.outputs.extend(
            [out for out in self.tasks[-1].outputs if out not in self.outputs]
        )


class ParallelWorkflow(SimulationWorkflow):
    """
    Base class for workflows where tasks are executed concurrently.
    """

    def normalize(self, archive: EntryArchive, logger: BoundLogger) -> None:
        super().normalize(archive, logger=logger)

        if not self.tasks:
            logger.error(INCORRECT_N_TASKS)
            return

        for task in self.tasks:
            if not task.inputs:
                # link inputs to all tasks
                task.inputs.extend(self.inputs)

                # link tasks outputs to outputs
                self.outputs.extend(
                    [out for out in task.outputs if out not in self.outputs]
                )


# TODO @all: Does this belong here?
class ElectronicStructureResults(SimulationWorkflowResults):
    """
    Contains definitions for results of an electronic structure simulation.
    """

    dos = Quantity(
        type=ElectronicDensityOfStates,
        description="""
        Reference to the electronic density of states output.
        """,
    )


m_package.__init_metainfo__()
