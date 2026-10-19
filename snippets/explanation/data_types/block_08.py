try:
    section.probability = 1.5
except ValueError as e:
    print(e)  # "All values must be in [0.0,1.0], got range [1.5, 1.5]"

try:
    section.values = [0.5, 2.0, 15.0]
except ValueError as e:
    print(e)  # "All values must be in [0,10], got range [0.5, 15.0]"
