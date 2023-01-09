import os
import sys

import uvicorn  # type: ignore

from application import setup_application
from application.settings import Settings


def main(host: str, port: int):
    settings = Settings()
    log_level = settings.log_level.lower()
    app = setup_application()
    kwargs = {
        "host": host,
        "port": port,
        "loop": "uvloop",
        "log_level": log_level,
        "use_colors": log_level == "DEBUG",
    }
    uvicorn.run(app, **kwargs)


def _get_args() -> tuple[str, int]:
    host = None
    port = None
    if len(sys.argv) == 3:
        host = sys.argv[1]
        port = sys.argv[2]
    else:
        host = os.environ.get("API_HOST")
        port = os.environ.get("API_PORT")
    if host is None or port is None:
        raise RuntimeError(f"No host/port provided: host={host}, port={port}")
    return str(host), int(port)


if __name__ == "__main__":
    args = _get_args()
    main(*args)
