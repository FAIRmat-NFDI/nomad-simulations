# docs-snippet: runnable
from nomad.units import ureg

from nomad_simulations.schema_packages.outputs import Outputs
from nomad_simulations.schema_packages.properties import ElectronicBandGap

outputs = Outputs()
outputs.electronic_band_gaps.append(ElectronicBandGap(value=2.0 * ureg.eV))
outputs.electronic_band_gaps.append(
    ElectronicBandGap(value=1.8 * ureg.eV, spin_channel=0)
)
outputs.electronic_band_gaps.append(
    ElectronicBandGap(value=1.9 * ureg.eV, spin_channel=1)
)

spin_polarized = outputs.extract_spin_polarized_property('electronic_band_gaps')

assert len(outputs.electronic_band_gaps) == 3
assert len(spin_polarized) == 2
assert {gap.spin_channel for gap in spin_polarized} == {0, 1}
