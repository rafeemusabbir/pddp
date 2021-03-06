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
"""Base dynamics model."""

import torch

from ..utils.encoding import StateEncoding
from ..utils.classproperty import classproperty


class DynamicsModel(torch.nn.Module):

    """Base dynamics model."""

    def reset_parameters(self, initializer=torch.nn.init.normal_):
        """Resets all parameters that require gradients with random values.

        Args:
            initializer (callable): In-place function to initialize module
                parameters.

        Returns:
            self.
        """
        for p in self.parameters():
            if p.requires_grad:
                initializer(p)
        return self

    @classproperty
    def action_size(cls):
        """Action size (int)."""
        raise NotImplementedError

    @classproperty
    def state_size(cls):
        """State size (int)."""
        raise NotImplementedError

    def fit(self, X, U, dX, quiet=False, **kwargs):
        """Fits the dynamics model.

        Args:
            X (Tensor<N, state_size>): State trajectory.
            U (Tensor<N, action_size>): Action trajectory.
            dX (Tensor<N, state_size>): Next state trajectory.
            quiet (bool): Whether to print anything to screen or not.
        """
        raise NotImplementedError

    def forward(self,
                z,
                u,
                i,
                encoding=StateEncoding.DEFAULT,
                identical_inputs=False,
                **kwargs):
        """Dynamics model function.

        Args:
            z (Tensor<..., encoded_state_size>): Encoded state distribution.
            u (Tensor<..., action_size>): Action vector(s).
            i (Tensor<...>): Time index.
            encoding (int): StateEncoding enum.
            identical_inputs (bool): Whether the batched inputs can be
                assumed identical or not.

        Returns:
            Next encoded state distribution (Tensor<..., encoded_state_size>).
        """
        raise NotImplementedError
