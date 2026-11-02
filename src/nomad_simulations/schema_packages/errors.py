import numpy as np
from nomad.datamodel.data import ArchiveSection
from nomad.metainfo import MEnum, Quantity

from nomad_simulations.schema_packages.utils.log_rules import log_when


# TODO This entire module is a prototype, to be tested and refined
class ErrorEstimate(ArchiveSection):
    """
    A generic container for uncertainty/error information associated with a PhysicalProperty.

    Supports:
      - Scalar or array errors (aligned to the property's `value` shape).
      - Confidence/prediction intervals.
      - Named metrics (std, stderr, RMSE, MAE, ...).
      - Method/provenance metadata (bootstrap, jackknife, analytical, validation).
    """

    # What kind of measure is this?
    metric = Quantity(
        type=MEnum(
            'std',
            'stderr',
            'variance',
            'rmse',
            'mae',
            'mape',
            'ci',  # confidence interval
            'pi',  # prediction interval
            'iqr',
            'mad',
            'systematic_bias',
            'model_uncertainty',
            'other',
        ),
        description="""
        The type of error or uncertainty metric being reported.

        Allowed values are:

        | Value             | Description                                                                 |
        |-------------------|-----------------------------------------------------------------------------|
        | `"std"`           | Standard deviation of the observable.                                       |
        | `"stderr"`        | Standard error of the mean (std / √N).                                      |
        | `"variance"`      | Variance of the observable (σ²).                                            |
        | `"rmse"`          | Root-mean-square error between predictions and reference values.            |
        | `"mae"`           | Mean absolute error between predictions and reference values.               |
        | `"mape"`          | Mean absolute percentage error, expressed relative to reference values.     |
        | `"ci"`            | Confidence interval for the observable, typically with a specified level.   |
        | `"pi"`            | Prediction interval for new observations.                                   |
        | `"iqr"`           | Interquartile range (Q3 – Q1).                                              |
        | `"mad"`           | Median absolute deviation (robust alternative to standard deviation).       |
        | `"systematic_bias"` | Estimated systematic offset (bias) between observed and true values.      |
        | `"model_uncertainty"` | Uncertainty arising from the model itself (e.g., ML predictive spread). |
        | `"other"`         | A different metric not covered above; further specified in `notes` or `definition_iri`. |
        """,
    )

    # Optional URI to a formal definition (VIM/GUM, CODATA, or internal ontology)
    definition_iri = Quantity(
        type=str, description='IRI/URL pointing to a formal metric definition.'
    )

    # Optional tags that further qualify the estimate (e.g., "bootstrap", "jackknife", "analytical")
    method = Quantity(
        type=str,
        description='Computation method for the estimate (e.g., bootstrap, jackknife, analytical).',
    )

    n_samples = Quantity(
        type=np.int32,
        description='Number of samples used to compute the estimate (if applicable).',
    )

    # Scope clarifies where this error applies
    scope = Quantity(
        type=MEnum('global', 'per_value', 'per_component', 'per_entity'),
        description="""
        The application scope of the estimate:
        - global: single number applies to the whole property;
        - per_value: array aligned with the property's value array;
        - per_component: aligned with a named component axis (see `component_axis`);
        - per_entity: aligned with referenced entities.
        """,
    )

    # If scope == per_component, name the axis (e.g., "spin", "kpoint", "band", "species")
    component_axis = Quantity(
        type=str,
        description='Name of the component axis this estimate aligns to (used with scope=per_component).',
    )

    # Scalar/array error value (std, stderr, rmse, mae, etc.)
    value = Quantity(
        type=np.float64,
        shape=['*'],  # allow scalar (len 1) or arbitrary flatten/broadcast
        description='Error/uncertainty values for metrics such as std, stderr, rmse, mae, etc.',
    )

    # Intervals (confidence or prediction)
    interval_type = Quantity(
        type=MEnum('confidence', 'prediction'),
        description='Type of interval if an interval is provided.',
    )

    level = Quantity(
        type=np.float64, description='Interval level (e.g., 0.95 for 95% intervals).'
    )

    lower = Quantity(
        type=np.float64,
        shape=['*'],
        description='Lower bound of the interval (scalar or array aligned to the target).',
    )

    upper = Quantity(
        type=np.float64,
        shape=['*'],
        description='Upper bound of the interval (scalar or array aligned to the target).',
    )

    # Optional note about known systematic effects (units should match the property)
    bias = Quantity(
        type=np.float64,
        shape=['*'],
        description='Estimated systematic bias (scalar or array).',
    )

    # Free-form notes (e.g., cross-validation split, dataset, calibration model, etc.)
    notes = Quantity(
        type=str, description='Free-text provenance or remarks about the estimate.'
    )

    @log_when(
        'warning',
        on=('metric', 'interval_type'),
        condition=lambda self: (
            self.metric in ('ci', 'pi') and self.interval_type is None
        ),
        message='Interval-type metric is used without specifying an interval type.',
    )
    @log_when(
        'warning',
        on=('interval_type', 'metric'),
        condition=lambda self: (
            self.interval_type is not None and self.metric not in ('ci', 'pi', 'other')
        ),
        message='Interval type is set but the metric is not an interval metric.',
    )
    @log_when(
        'warning',
        on=('level',),
        condition=lambda self: self.level is not None and not 0.0 < self.level < 1.0,
        message='Interval level is outside the typical open interval (0, 1).',
    )
    @log_when(
        'warning',
        on=('lower', 'upper'),
        condition=lambda self: (self.lower is None) ^ (self.upper is None),
        message=(
            'Only one interval bound is provided; both lower and upper are recommended.'
        ),
        samples={'lower': [np.array([0.1])], 'upper': [np.array([0.9])]},
    )
    @log_when(
        'info',
        on=('scope',),
        condition=lambda self: self.scope is None,
        message=(
            'No scope specified for the error estimate; default interpretation may apply.'
        ),
    )
    def normalize(self, archive, logger):
        super().normalize(archive, logger)
