from typing import TYPE_CHECKING

import numpy as np
from nomad.config import config
from nomad.metainfo import Quantity, SchemaPackage, Section, SubSection
from nomad_simulations.schema_packages.general import ModelBaseSection

configuration = config.get_plugin_entry_point(
    'nomad_simulations.schema_packages:nomad_simulations_plugin'
)

m_package = SchemaPackage()


class Spin(ModelBaseSection):
    pass

class DOS(ModelBaseSection):
    """Collection of Electronic Density of States"""
    m_def = Section()

    class SemanticDOS(ModelBaseSection):
        """Electronic Density of State set that has a clear semantic meaning,
        e.g. total DOS, projected DOS, etc."""

        class SpinResolvedDOS(ModelBaseSection):
            """Spin resolved DOS"""

            spin = Quantity(
                type=Spin,
                description="Spin channel",
            )

            values = Quantity(
                type=np.float64,
                shape=['*'],
                description="Actual DOS values",
            )  # ? add renormalized_values

            def name_from_section(self, section):
                return self.spin.name_from_section()

        label = Quantity(
            type=str,
            description="Label of the DOS",
        )  # TODO: el n m

        energies = Quantity(
            type=np.float64,
            unit='J',
            shape=['*'],
            description="Energy values at which the DOS is evaluated",
        )

        spin_channels = SubSection(subsection=SpinResolvedDOS.m_def, repeats=True)

        def name_from_section(self, section):
            if section.label:
                return section.label
            else:
                return 'total'

    collections = SubSection(subsection=SemanticDOS.m_def, repeats=True)


m_package.__init_metainfo__()
