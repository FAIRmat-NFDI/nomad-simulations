# docs-snippet: runnable
from nomad_simulations.schema_packages.model_method import DFT
from nomad_simulations.schema_packages.numerical_settings import SelfConsistency

scf = SelfConsistency(threshold_change=1e-3, threshold_change_unit='joule')
dft = DFT(name='DFT', type='KS', numerical_settings=[scf])

assert dft.numerical_settings[0].threshold_change == 1e-3
assert dft.numerical_settings[0].threshold_change_unit == 'joule'
assert scf.m_parent is dft
