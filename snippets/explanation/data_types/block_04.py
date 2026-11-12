section = MySection()

# Valid assignments
section.probability = 0.5        # ✓ Valid
section.probability = 0.0        # ✓ Valid (inclusive bound)
section.probability = 1.0        # ✓ Valid (inclusive bound)

# Invalid assignments
section.probability = 1.5        # ✗ Raises ValueError
section.probability = -0.1       # ✗ Raises ValueError

# Special values (always valid)
section.probability = None       # ✓ Valid
section.probability = float('nan')  # ✓ Valid
