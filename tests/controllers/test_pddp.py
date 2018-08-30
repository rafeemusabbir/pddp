"""Unit tests for pddp.controllers.pddp."""

import torch
import pytest

from pddp.examples import *
from pddp.costs import QRCost
from pddp.controllers.pddp import *
from pddp.utils.gaussian_variable import GaussianVariable
from pddp.utils.encoding import infer_encoded_state_size
from pddp.utils.angular import infer_augmented_state_size

STATE_ENCODINGS = [
    StateEncoding.FULL_COVARIANCE_MATRIX,
    StateEncoding.UPPER_TRIANGULAR_CHOLESKY,
    StateEncoding.VARIANCE_ONLY,
    StateEncoding.STANDARD_DEVIATION_ONLY,
    StateEncoding.IGNORE_UNCERTAINTY,
]

COSTS = [
    cartpole.CartpoleCost,
    pendulum.PendulumCost,
    rendezvous.RendezvousCost,
]
ENVS = [
    cartpole.CartpoleEnv,
    pendulum.PendulumEnv,
    rendezvous.RendezvousEnv,
]
MODELS = [
    cartpole.CartpoleDynamicsModel,
    pendulum.PendulumDynamicsModel,
    rendezvous.RendezvousDynamicsModel,
]


def _setup(model_class, cost_class, encoding, N):
    model = model_class(0.1)
    cost = cost_class()

    z0 = GaussianVariable.random(model.state_size).encode(encoding)
    U = torch.randn(N, model.action_size, requires_grad=True)

    return z0, U, model, cost


@pytest.mark.parametrize("N", [1, 3])
@pytest.mark.parametrize("encoding", STATE_ENCODINGS)
@pytest.mark.parametrize("model_class, cost_class", zip(MODELS, COSTS))
def test_forward_backward(model_class, cost_class, encoding, N):
    z0, U, model, cost = _setup(model_class, cost_class, encoding, N)
    encoded_state_size = z0.shape[-1]

    # FORWARD PASS
    Z, F_z, F_u, L, L_z, L_u, L_zz, L_uz, L_uu = forward(
        z0, U, model, cost, encoding)

    assert Z.shape == (N + 1, encoded_state_size)
    assert F_z.shape == (N, encoded_state_size, encoded_state_size)
    assert F_u.shape == (N, encoded_state_size, model.action_size)

    assert L.shape == torch.Size([N + 1])
    assert L_z.shape == (N + 1, encoded_state_size)
    assert L_u.shape == (N, model.action_size)
    assert L_zz.shape == (N + 1, encoded_state_size, encoded_state_size)
    assert L_uz.shape == (N, model.action_size, encoded_state_size)
    assert L_uu.shape == (N, model.action_size, model.action_size)

    # Q FUNCTION SANITY CHECK
    Q_z, Q_u, Q_zz, Q_uz, Q_uu = Q(F_z[0], F_u[0], L_z[0], L_u[0], L_zz[0],
                                   L_uz[0], L_uu[0], L_z[-1], L_zz[-1])

    assert Q_z.shape == torch.Size([encoded_state_size])
    assert Q_u.shape == torch.Size([model.action_size])
    assert Q_zz.shape == (encoded_state_size, encoded_state_size)
    assert Q_uz.shape == (model.action_size, encoded_state_size)
    assert Q_uu.shape == (model.action_size, model.action_size)

    # BACKWARD PASS
    k, K = backward(Z, F_z, F_u, L, L_z, L_u, L_zz, L_uz, L_uu)

    assert k.shape == (N, model.action_size)
    assert K.shape == (N, model.action_size, encoded_state_size)


@pytest.mark.filterwarnings("ignore:exceeded max regularization term")
@pytest.mark.parametrize("N", [1, 3])
@pytest.mark.parametrize("encoding", STATE_ENCODINGS)
@pytest.mark.parametrize("env_class, model_class, cost_class",
                         zip(ENVS, MODELS, COSTS))
def test_fit(env_class, model_class, cost_class, encoding, N):
    env = env_class()
    _, U, model, cost = _setup(model_class, cost_class, encoding, N)
    controller = PDDPController(env, model, cost)

    Z, U = controller.fit(U, encoding=encoding)


@pytest.mark.parametrize("N", [1, 3])
@pytest.mark.parametrize("encoding", STATE_ENCODINGS)
@pytest.mark.parametrize("model_class, cost_class", zip(MODELS, COSTS))
def test_benchmark_forward(benchmark, model_class, cost_class, encoding, N):
    z0, U, model, cost = _setup(model_class, cost_class, encoding, N)
    benchmark(forward, z0, U, model, cost, encoding)


@pytest.mark.parametrize("N", [1, 3])
@pytest.mark.parametrize("encoding", STATE_ENCODINGS)
@pytest.mark.parametrize("model_class, cost_class", zip(MODELS, COSTS))
def test_benchmark_backward(benchmark, model_class, cost_class, encoding, N):
    z0, U, model, cost = _setup(model_class, cost_class, encoding, N)
    Z, F_z, F_u, L, L_z, L_u, L_zz, L_uz, L_uu = forward(
        z0, U, model, cost, encoding)
    benchmark(backward, Z, F_z, F_u, L, L_z, L_u, L_zz, L_uz, L_uu)