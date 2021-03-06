# Copyright (C) 2018, Anass Al
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>
"""Base controller."""

import torch
from ..utils.encoding import StateEncoding


class Controller(torch.nn.Module):

    """Base controller."""

    def eval(self):
        """Sets the module in evaluation mode.

        Returns:
            self (Controller).
        """
        return super(Controller, self).eval()

    def train(self, mode=True):
        """Sets the module in training mode.

        Args:
            mode (bool): Mode.

        Returns:
            self (Controller).
        """
        return super(Controller, self).train(mode)

    def fit(self, U, encoding=StateEncoding.DEFAULT, **kwargs):
        """Determines the optimal path to minimize the cost.

        Args:
            U (Tensor<N, action_size>): Initial action path.
            encoding (int): StateEncoding enum.

        Returns:
            Tuple of:
                Z (Tensor<N+1, encoded_state_size>): Optimal encoded state path.
                U (Tensor<N, action_size>): Optimal action path.
        """
        raise NotImplementedError

    def forward(self, z, i, encoding=StateEncoding.DEFAULT, **kwargs):
        """Determines the optimal single-step control to minimize the cost.

        Note: You must `fit()` first.

        Args:
            z (Tensor<encoded_state_size>): Current encoded state distribution.
            i (int): Current time step.
            encoding (int): StateEncoding enum.

        Returns:
            Optimal action (Tensor<action_size>).
        """
        raise NotImplementedError
