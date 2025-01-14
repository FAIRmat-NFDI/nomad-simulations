from typing import TYPE_CHECKING

from ..physical_property import PhysicalPropertyDecomposition
from ..variables import Force, MethodReference
from nomad.metainfo.datasets import DatasetTemplate

ForceTemplateGenerator = PhysicalPropertyDecomposition(
    Force,
    reference_type=MethodReference,
)


class ModelForceSection('ArchiveSection'):
    force = ForceTemplateGenerator()()


# OR

ModelForceSection = DatasetTemplate(
    mandatory_fields=[Force],
)()
