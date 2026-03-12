# docs-snippet: runnable
from nomad_simulations.schema_packages.data_types import Bound

# Closed intervals (inclusive bounds)
Bound('[0,1]')  # 0 <= x <= 1
Bound('[1,10]')  # 1 <= x <= 10

# Open intervals (exclusive bounds)
Bound('(0,1)')  # 0 < x < 1
Bound('(-1,1)')  # -1 < x < 1

# Half-open intervals
Bound('[0,1)')  # 0 <= x < 1
Bound('(0,1]')  # 0 < x <= 1

# Unbounded intervals
Bound('[0,)')  # x >= 0 (non-negative)
Bound('(0,)')  # x > 0 (strictly positive)
Bound('(,10]')  # x <= 10 (upper bounded)
Bound('(,-1)')  # x < -1 (strictly negative)

# Unbounded (no constraints)
Bound('')  # No bounds (-inf, inf)
