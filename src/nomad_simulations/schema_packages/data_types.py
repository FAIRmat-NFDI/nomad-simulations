#
# Copyright The NOMAD Authors.
#
# This file is part of NOMAD. See https://nomad-lab.eu for further info.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import numpy as np

from nomad.metainfo.data_type import ExactNumber, InexactNumber


class PositiveInt(ExactNumber):
    """
    Integer data type that only allows positive values (> 0).
    """

    __slots__ = ()

    def __init__(self, *, dtype: type[int | np.int32] = int):
        if isinstance(dtype, np.dtype):
            dtype = dtype.type

        if dtype not in (int, np.int32, np.int64):
            raise ValueError(f'Invalid dtype for {self.__class__.__name__}.')

        super().__init__(dtype)
        self._np_base = np.integer

    def convertible_from(self, other):
        if other in (int, np.int64, np.int32, np.int16, np.int8):
            return True
        return False

    def normalize(self, value, **kwargs):
        normalized_value = super().normalize(value, **kwargs)
        
        if normalized_value is None:
            return normalized_value

        # Handle arrays
        if isinstance(normalized_value, (list, np.ndarray)):
            if isinstance(normalized_value, np.ndarray):
                if np.any(normalized_value <= 0):
                    raise ValueError(f"All values must be positive, got array with min value {np.min(normalized_value)}")
            else:  # list
                if any(v <= 0 for v in normalized_value):
                    min_val = min(normalized_value)
                    raise ValueError(f"All values must be positive, got list with min value {min_val}")
        else:
            # Handle scalars
            if normalized_value <= 0:
                raise ValueError(f"Value must be positive, got {normalized_value}")

        return normalized_value


class PositiveFloat(InexactNumber):
    """
    Float data type that only allows positive values (> 0).
    """

    __slots__ = ()

    def __init__(self, *, dtype: type[float | np.float64] = float):
        if isinstance(dtype, np.dtype):
            dtype = dtype.type

        if dtype not in (float, np.float64, np.float32):
            raise ValueError(f'Invalid dtype for {self.__class__.__name__}.')

        super().__init__(dtype)
        self._np_base = np.inexact

    def convertible_from(self, other):
        if other in (float, np.float64, np.float32, np.float16):
            return True
        return False

    def normalize(self, value, **kwargs):
        normalized_value = super().normalize(value, **kwargs)
        
        if normalized_value is None:
            return normalized_value

        # Handle arrays
        if isinstance(normalized_value, (list, np.ndarray)):
            if isinstance(normalized_value, np.ndarray):
                # Check for NaN values and non-positive values
                valid_mask = ~np.isnan(normalized_value)
                if np.any(valid_mask) and np.any(normalized_value[valid_mask] <= 0):
                    min_val = np.min(normalized_value[valid_mask])
                    raise ValueError(f"All non-NaN values must be positive, got array with min value {min_val}")
            else:  # list
                valid_values = [v for v in normalized_value if not (isinstance(v, float) and np.isnan(v))]
                if valid_values and any(v <= 0 for v in valid_values):
                    min_val = min(valid_values)
                    raise ValueError(f"All non-NaN values must be positive, got list with min value {min_val}")
        else:
            # Handle scalars
            if not (isinstance(normalized_value, float) and np.isnan(normalized_value)) and normalized_value <= 0:
                raise ValueError(f"Value must be positive, got {normalized_value}")

        return normalized_value