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
"""Pendulum cost."""

import torch

from .model import PendulumDynamicsModel

from ...costs import QRCost
from ...utils.angular import augment_state


class PendulumCost(QRCost):

    """Pendulum cost."""

    def __init__(self):
        """Constructs a PendulumCost."""
        model = PendulumDynamicsModel

        Q_term = 100.0 * torch.eye(model.state_size)
        Q = 100.0 * torch.eye(model.state_size)

        # Don't penalize instantaneous velocities as much.
        # Note: we are operating on the augmented state vectors here:
        #   [theta', sin(theta), cos(theta)]
        Q[0, 0] = 1.0

        R = torch.eye(model.action_size)

        # Goal is not all zeroes after augmenting the state.
        x_goal = augment_state(
            torch.zeros(model.state_size), model.angular_indices,
            model.non_angular_indices)

        super(PendulumCost, self).__init__(Q, R, Q_term=Q_term, x_goal=x_goal)