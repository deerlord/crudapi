import uvicorn  # type: ignore

from crudapi import setup_application
from crudapi.settings import Settings


def main():
    settings = Settings()
    log_level = settings.log_level.lower()
    debug = log_level == "debug"
    app = setup_application(debug)
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        loop="uvloop",
        log_level=log_level,
        use_colors=debug,
    )


if __name__ == "__main__":
    main()
