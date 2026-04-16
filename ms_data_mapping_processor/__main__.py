"""Main entry point for the microservice HTTP server."""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_health import health

from ms_data_mapping_processor.core.service_process import get_asset_values
from ms_data_mapping_processor.core.service_setup import setup_service
from ms_data_mapping_processor.endpoint_routes import default_endpoints, submodels_endpoints
from ms_data_mapping_processor.models.configuration_models import load_configuration_file
from ms_data_mapping_processor.models.constants import CONFIG_BASE_PATH
from ms_data_mapping_processor.models.process_models import ServiceStates
from ms_data_mapping_processor.utilities import logging_handler

logger = logging.getLogger(__name__)


async def worker(stop_event: asyncio.Event, states, interval: int = 5):
    """Worker thread that handles the polling of mqtt data.

    :param stop_event: _description_
    :param states: _description_
    :param interval: _description_
    """
    while not stop_event.is_set():
        try:
            get_asset_values(states)
            # get_asset_values_old(states.references, states.asset_connector, states.influx_client)
        except Exception as e:
            logger.error(f"Error in worker: {e}")

        # Either wait for timeout or quit sooner if stop_event is triggered
        _, pending = await asyncio.wait(
            [asyncio.create_task(stop_event.wait()), asyncio.create_task(asyncio.sleep(interval))],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()  # cancel not needed tasks


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI application.

    :param app: FastAPI application
    """
    logger.info("Initialize the microservice ")
    app.state.service_states = None

    try:
        # Load configuration
        logger.debug("Get configuration file name from environment variable 'CONFIG_FILE_NAME'.")
        config_file_name = os.getenv("CONFIG_FILE_NAME", "service_config.json")
        config_file_path = Path(CONFIG_BASE_PATH) / config_file_name

        configuration = load_configuration_file(config_file_path)

        if configuration is None:
            logger.error("Failed to load runtime configuration. Shutting down the application.")
            raise RuntimeError("Failed to load runtime configuration.")

        # Setup microservice
        service_states: ServiceStates = setup_service(configuration)

        app.state.service_states = service_states
        logger.info("Microservice initialized successfully.")

    except Exception as e:
        logger.error(f"Error during microservice initialization: {e}")
        raise e

    # Start background worker for microservice main processing
    try:
        logger.info("Start asset connector polling")

        stop_event = asyncio.Event()
        task = asyncio.create_task(
            worker(
                stop_event,
                service_states,
                configuration.polling_interval,
            )
        )  # start background task

        yield
        stop_event.set()
        await task  # wait until finished correctly
    except Exception as e:
        logger.exception(f"Shutdown failed: {e}")
        raise e

    finally:
        logger.info("Shutdown microservice complete.")

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
app.include_router(submodels_endpoints.router)
app.add_middleware(CORSMiddleware, allow_origins=["*"])

if __name__ == "__main__" and os.getenv("RUN_SERVER", "1") == "1":
    """Run the FastAPI application."""
    logging_handler.initialize_logging(logging.INFO)
    host = os.getenv("APP_HOST", "127.0.0.1")
    port = int(os.getenv("APP_PORT", "3088"))
    uvicorn.run(app, host=host, port=port, log_config=None)
