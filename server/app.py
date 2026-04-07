"""FastAPI app entrypoint for the SupportOps environment."""

from __future__ import annotations

try:
    from openenv.core.env_server.http_server import create_app
except Exception as exc:  # pragma: no cover
    raise ImportError(
        "openenv is required to run the SupportOps web server. Install dependencies first."
    ) from exc

try:
    from ..models import SupportOpsAction, SupportOpsObservation
    from .support_ops_env_environment import SupportOpsEnvironment
except ImportError:
    from models import SupportOpsAction, SupportOpsObservation
    from server.support_ops_env_environment import SupportOpsEnvironment


app = create_app(
    SupportOpsEnvironment,
    SupportOpsAction,
    SupportOpsObservation,
    env_name="support_ops_env",
    max_concurrent_envs=4,
)


def main(host: str = "0.0.0.0", port: int = 8000) -> None:
    import uvicorn

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()

