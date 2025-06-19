"""
Electronic structure utility functions.
"""

import numpy as np

def inner_copy(
    tensor: np.ndarray, rank_selection: int | tuple[int] | slice, repeat: int = 0
) -> np.ndarray:
    """
    Take a chunk of a high-ranked array and extend it with exact copies of the selection.

    This function selects a portion of a tensor along its first axis and repeats it
    the specified number of times, effectively extending the tensor.

    Args:
        tensor: Input `numpy` array to copy from
        rank_selection: `int`, `tuple`, `slice` specifying which elements to select
        repeat: Number of times to repeat the selection. Counting starts from 0 (default: 0)

    Example:
        >>> arr = np.array([[1, 2], [3, 4], [5, 6]])
        >>> inner_copy(arr, slice(0, None), repeat=2)
        array([[1, 2], [1, 2], [1, 2]])
    """
    if tensor.size == 0:
        return tensor

    selected_chunk = tensor[rank_selection]

    # If selection results in 1D array, ensure it maintains proper shape
    if selected_chunk.ndim == tensor.ndim - 1:
        selected_chunk = np.expand_dims(selected_chunk, axis=0)

    repeated_chunks = np.tile(selected_chunk, (repeat + 1, *([1] * (tensor.ndim - 1))))
    return np.concatenate([tensor, repeated_chunks], axis=0)
