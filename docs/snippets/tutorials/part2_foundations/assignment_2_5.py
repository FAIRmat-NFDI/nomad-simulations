# docs-snippet: runnable
from nomad import utils

from nomad_simulations.schema_packages.atoms_state import AtomsState

logger = utils.get_logger(__name__)
atoms_states = [AtomsState(chemical_symbol=symbol) for symbol in ['Ga', 'As']]
atomic_numbers = [atom.resolve_atomic_number(logger=logger) for atom in atoms_states]

assert atomic_numbers == [31, 33]
