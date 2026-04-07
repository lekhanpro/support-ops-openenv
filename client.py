"""Typed OpenEnv client for SupportOps."""

from __future__ import annotations

from typing import Any, Dict

from openenv.core import EnvClient
from openenv.core.client_types import StepResult

try:
    from .models import SupportOpsAction, SupportOpsObservation, SupportOpsState
except ImportError:
    from models import SupportOpsAction, SupportOpsObservation, SupportOpsState


class SupportOpsEnv(EnvClient[SupportOpsAction, SupportOpsObservation, SupportOpsState]):
    """Async client for the SupportOps environment."""

    def _step_payload(self, action: SupportOpsAction) -> Dict[str, Any]:
        return action.model_dump(exclude_none=True)

    def _parse_result(self, payload: Dict[str, Any]) -> StepResult[SupportOpsObservation]:
        obs_data = dict(payload.get("observation", {}))
        obs_data.setdefault("done", payload.get("done", False))
        obs_data.setdefault("reward", payload.get("reward"))
        observation = SupportOpsObservation.model_validate(obs_data)
        return StepResult(
            observation=observation,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict[str, Any]) -> SupportOpsState:
        return SupportOpsState.model_validate(payload)
