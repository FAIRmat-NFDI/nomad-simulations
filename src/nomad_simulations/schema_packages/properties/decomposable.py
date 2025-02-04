from nomad.metainfo import placeholder, Quantity, SubSection, Reference
from nomad_simulations.schema_packages.general import ModelBaseSection
from nomad_simulations.schema_packages.model_method import BaseModelMethod
from nomad_simulations.schema_packages.properties import energy, force

class PropertyContribution(ModelBaseSection):
    """
    Abstract physical property section linking a property contribution to a contribution
    from some method.

    Abstract class for incorporating specific contributions of a physical property, while
    linking this contribution to a specific component (of class `BaseModelMethod`) of the
    over `ModelMethod` using the `model_method_ref` quantity.
    """

    value = placeholder

    method_definition = Quantity(
        type=Reference(BaseModelMethod),  # ! specialize to method definition
        description="""
        Further specification of the definition for the contribution, in terms of the method.
        """,
    )

    def normalize(self, *args, **kwargs) -> None:
        super().normalize(*args, **kwargs)
        if not self.name:
            self.name = self.get('model_method_ref').get('name')  # ? does this resolve references


class DecomposableProperty(ModelBaseSection):
    """
    Abstract physical property section for decomposable properties.

    Abstract class for incorporating decomposable physical properties, which can be
    decomposed into contributions from different components (of class `BaseModelMethod`)
    of the over `ModelMethod`.
    """

    value = placeholder

    contributions = SubSection(sub_section=PropertyContribution.m_def, repeats=True)

    # ! extract name from value


class TotalEnergy(DecomposableProperty):
    """
    The total energy of a system. `contributions` specify individual energetic
    contributions to the `TotalEnergy`.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.name = 'Total Energy'  # !

    class EnergyContribution(PropertyContribution):
        value = energy

    contributions = SubSection(sub_section=EnergyContribution.m_def, repeats=True)


class TotalForce(DecomposableProperty):  # ? connect to model_system
    """
    The total force on a system. `contributions` specify individual force
    contributions to the `TotalForce`.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.name = 'Total Force'  # !

    class ForceContribution(PropertyContribution):
        value = force

    contributions = SubSection(sub_section=ForceContribution.m_def, repeats=True)
