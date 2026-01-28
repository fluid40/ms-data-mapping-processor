import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_health import health

from ms_data_mapping_processor.endpoint_routes import default_endpoints
from ms_data_mapping_processor.models.configuration import load_configuration_file
from ms_data_mapping_processor.utilities import logging_handler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI application.

    :param app: FastAPI application
    """
    logger.info("Initialize the microservice HTTP server")
    app.state.service_states = None

    try:
        logger.debug("Get configuration file path from environment variable 'RUNTIME_CONFIGURATION_FILE'.")
        config_file_path = os.getenv("CONFIG_FILE_PATH", "config/DevContainerEnv.json")
        configuration = load_configuration_file(config_file_path)

        if configuration is None:
            logger.error("Failed to load runtime configuration. Shutting down the application.")
            raise RuntimeError("Failed to load runtime configuration.")

    except Exception as e:
        logger.error(f"Error during application startup: {e}")
        raise e

    yield
    # Perform any necessary cleanup here


app = FastAPI(
    title="runtime REST API",
    description="Fluid4.0 Runtime REST API",
    version="v1",
    lifespan=lifespan,
)


def is_healthy() -> bool:
    """Check if the application is healthy. This is a placeholder function that always returns True.

    :return: True if the application is healthy, False otherwise.
    """
    return True
    # return app.state.runtime is not None


app.add_api_route("/health", health([is_healthy]), tags=["Root"])

app.include_router(default_endpoints.router)
app.add_middleware(CORSMiddleware, allow_origins=["*"])

if __name__ == "__main__" and os.getenv("RUN_SERVER", "1") == "1":
    """Run the FastAPI application."""
    logging_handler.initialize_logging()
    host = os.getenv("APP_HOST", "127.0.0.1")
    port = int(os.getenv("APP_PORT", "3088"))
    uvicorn.run(app, host=host, port=port, log_config=None)
