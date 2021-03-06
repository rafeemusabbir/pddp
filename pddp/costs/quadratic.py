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
"""Quadratic cost functions."""

import torch
import numpy as np

from .base import Cost
from ..utils.encoding import StateEncoding, decode_covar, decode_mean


class QRCost(Cost):

    r"""Quadratic cost function.

    Instantaneous cost:
        E[L(x, u)] = tr(Q \Sigma)
                   + (\mu - x_goal)^T Q (\mu - x_goal)
                   + (u - u_goal)^T R (u - u_goal)

    Terminal cost:
        E[L(x)] = tr(Q \Sigma) + (\mu - x_goal)^T Q (\mu - x_goal)
    """

    def __init__(self, Q, R, Q_term=None, x_goal=0.0, u_goal=0.0):
        """Constructs a QRCost.

        Args:
            Q (Tensor<state_size, state_size>): Q matrix.
            R (Tensor<action_size, action_size>): R matrix.
            Q_term (Tensor<state_size, state_size>): Terminal Q matrix,
                default: Q.
            x_goal (Tensor<state_size>): Goal state, default: 0.0.
            u_goal (Tensor<action_size>): Goal action, default: 0.0.
        """
        super(QRCost, self).__init__()
        Q_term = Q if Q_term is None else Q_term

        self.Q = torch.nn.Parameter(Q, requires_grad=False)
        self.R = torch.nn.Parameter(R, requires_grad=False)
        self.Q_term = torch.nn.Parameter(Q_term, requires_grad=False)

        self.x_goal = torch.nn.Parameter(
            torch.tensor(x_goal), requires_grad=False)
        self.u_goal = torch.nn.Parameter(
            torch.tensor(u_goal), requires_grad=False)

    def forward(self,
                z,
                u,
                i,
                terminal=False,
                encoding=StateEncoding.DEFAULT,
                **kwargs):
        """Cost function.

        Args:
            z (Tensor<..., encoded_state_size): Encoded state distribution.
            u (Tensor<..., action_size>): Action vector.
            i (Tensor<...>): Time index.
            terminal (bool): Whether the cost is terminal. If so, u should be
                `None`.
            encoding (int): StateEncoding enum.

        Returns:
            The expectation of the cost (Tensor<...>).
        """
        Q = self.Q_term if terminal else self.Q
        dims = z.dim()
        mean = decode_mean(z, encoding)
        dx = mean - self.x_goal
        dxQ = dx.matmul(Q)
        cost = (dxQ * dx).sum(-1) if dims > 1 else dxQ.matmul(dx)

        if not terminal:
            du = u - self.u_goal
            duR = du.matmul(self.R)
            cost += (duR * du).sum(-1) if dims > 1 else duR.matmul(du)

        if encoding != StateEncoding.IGNORE_UNCERTAINTY:
            # Batch compute trace.
            C = decode_covar(z, encoding)
            CQ = C * Q.t()
            trace = CQ.sum(list(range(1, C.dim()))) if dims > 1 else CQ.sum()
            cost += trace

        return cost


class SaturatingQRCost(Cost):

    r"""Saturating quadratic cost function.
    """

    def __init__(self, Q, R, Q_term=None, x_goal=0.0, u_goal=0.0):
        """Constructs a QRCost.

        Args:
            Q (Tensor<state_size, state_size>): Q matrix.
            R (Tensor<action_size, action_size>): R matrix.
            Q_term (Tensor<state_size, state_size>): Terminal Q matrix,
                default: Q.
            x_goal (Tensor<state_size>): Goal state, default: 0.0.
            u_goal (Tensor<action_size>): Goal action, default: 0.0.
        """
        super(SaturatingQRCost, self).__init__()
        Q_term = Q if Q_term is None else Q_term

        self.Q = torch.nn.Parameter(Q, requires_grad=False)
        self.R = torch.nn.Parameter(R, requires_grad=False)
        self.Q_term = torch.nn.Parameter(Q_term, requires_grad=False)

        self.x_goal = torch.nn.Parameter(
            torch.tensor(x_goal), requires_grad=False)
        self.u_goal = torch.nn.Parameter(
            torch.tensor(u_goal), requires_grad=False)

    def forward(self,
                z,
                u,
                i,
                terminal=False,
                encoding=StateEncoding.DEFAULT,
                **kwargs):
        """Cost function.

        Args:
            z (Tensor<..., encoded_state_size): Encoded state distribution.
            u (Tensor<..., action_size>): Action vector.
            i (Tensor<...>): Time index.
            terminal (bool): Whether the cost is terminal. If so, u should be
                `None`.
            encoding (int): StateEncoding enum.

        Returns:
            The expectation of the cost (Tensor<...>).
        """
        Q = self.Q_term if terminal else self.Q
        dims = z.dim()
        mean = decode_mean(z, encoding)
        dx = mean - self.x_goal

        if encoding != StateEncoding.IGNORE_UNCERTAINTY:
            # mean cost under normal distributed inputs
            C = decode_covar(z, encoding)
            CQ = C.bmm(Q.expand(C.shape[0], -1, -1)) if dims > 1 else C.mm(Q)
            I_ = torch.eye(dx.shape[-1])
            IpCQ = I_ + CQ
            if dims > 1:
                S1 = torch.gesv(Q.t().expand(C.shape[0], -1, -1),
                                IpCQ.transpose(-1, -2))[0].transpose(-1, -2)
                detIpCQ = torch.stack([m.det().sqrt() for m in IpCQ])
                S1dx = S1.bmm(dx.unsqueeze(-1)).squeeze()
                cost = 1.0 - (-0.5 * (dx * S1dx).sum(-1)).exp() / detIpCQ
            else:
                S1 = Q.mm(IpCQ.inverse())
                detIpCQ = IpCQ.det().sqrt()
                S1dx = S1.matmul(dx)
                cost = 1.0 - (-0.5 * dx.matmul(S1dx)).exp() / detIpCQ
        else:
            dx = mean - self.x_goal
            dxQ = dx.matmul(Q)
            qcost = (dxQ * dx).sum(-1) if dims > 1 else dxQ.matmul(dx)
            cost = 1.0 - (-0.5 * qcost).exp()

        if not terminal:
            du = u - self.u_goal
            duR = du.matmul(self.R)
            cost += (duR * du).sum(-1) if dims > 1 else duR.matmul(du)

        return cost
