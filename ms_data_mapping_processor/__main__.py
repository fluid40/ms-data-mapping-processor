"""Main entry point for the microservice HTTP server."""

import asyncio
import logging
import os
from contextlib import asynccontextmanager, suppress
from pathlib import Path

import uvicorn
from aas_standard_parser import descriptor_json_helper
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_health import health

from ms_data_mapping_processor.core.service_process import get_asset_values
from ms_data_mapping_processor.core.service_setup import setup_service
from ms_data_mapping_processor.endpoint_routes import (
    default_endpoints,
    submodels_endpoints,
)
from ms_data_mapping_processor.models.configuration_models import load_configuration_file
from ms_data_mapping_processor.models.constants import CONFIG_BASE_PATH
from ms_data_mapping_processor.models.process_models import ServiceStates
from ms_data_mapping_processor.utilities import logging_handler

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Background worker
# ---------------------------------------------------------------------------


async def worker(
    stop_event: asyncio.Event,
    states: ServiceStates,
    interval: int = 5,
) -> None:
    """
    Background worker that periodically polls asset values.

    The worker cooperatively shuts down as soon as stop_event is set.
    """
    _logger.info("Worker started")

    try:
        while not stop_event.is_set():
            try:
                get_asset_values(states)
            except Exception:
                _logger.exception("Error while processing asset values")

            # Wait for either shutdown or next polling interval
            with suppress(TimeoutError):
                await asyncio.wait_for(stop_event.wait(), timeout=interval)

    finally:
        _logger.info("Worker stopped")


# ---------------------------------------------------------------------------
# Lifespan handling (startup / shutdown)
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI application. Handles startup and graceful shutdown."""
    _logger.info("Initializing microservice")

    stop_event = asyncio.Event()
    worker_task: asyncio.Task | None = None

    # start server
    try:
        config_file_name = os.getenv("CONFIG_FILE_NAME", "service_config.json")
        config_file_path = (Path(CONFIG_BASE_PATH) / config_file_name).resolve()

        _logger.debug(f"Loading configuration from '{config_file_path.as_posix()}'")

        configuration = load_configuration_file(config_file_path)
        if configuration is None:
            raise RuntimeError("Failed to load runtime configuration")

        service_states: ServiceStates = setup_service(configuration)
        app.state.service_states = service_states

        _logger.info("Microservice initialized successfully")

        _logger.info("Starting asset connector polling worker")
        worker_task = asyncio.create_task(
            worker(
                stop_event=stop_event,
                states=service_states,
                interval=configuration.polling_interval,
            )
        )

        # Yield control to FastAPI (application is running)
        yield

    # shutdown server
    finally:
        _logger.info("Shutdown initiated")

        stop_event.set()

        if worker_task:
            try:
                await worker_task
            except asyncio.CancelledError:
                _logger.debug("Worker task cancelled during shutdown")

        _logger.info("Reset submodel descriptors on registry server to original hrefs")

        if service_states.server_handler.sm_registry_client is None or service_states.descriptor_mapping is None:
            _logger.info("Registry client or descriptor mapping not available during shutdown, skipping descriptor reset")
        else:
            # reset all changed descriptors to old href on registry server
            for mapping in service_states.descriptor_mapping:
                href = descriptor_json_helper.get_endpoint_href_by_index(mapping.master_descriptor, 0)
                _logger.info(f"Reset descriptor for submodel '{mapping.submodel_id}' to original href '{href}'")
                # update 'slave' descriptor with old href on registry server
                service_states.server_handler.sm_registry_client.submodel_registry.put_submodel_descriptor_by_id(
                    mapping.submodel_id, mapping.master_descriptor
                )

        _logger.info("Shutdown microservice complete")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="runtime REST API",
    description="Fluid4.0 Runtime REST API",
    version="v1",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------


def is_healthy() -> bool:
    """Health check endpoint."""
    return True


app.add_api_route("/health", health([is_healthy]), tags=["Root"])


# ---------------------------------------------------------------------------
# Routers & middleware
# ---------------------------------------------------------------------------

app.include_router(default_endpoints.router)
app.include_router(submodels_endpoints.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Application entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__" and os.getenv("RUN_SERVER", "1") == "1":
    logging_handler.initialize_logging(logging.INFO)

    _logger.info("Starting microservice HTTP server")

    host = os.getenv("APP_HOST", "127.0.0.1")
    port = int(os.getenv("APP_PORT", "3088"))

    _logger.info(f"Application host: {host}")
    _logger.info(f"Application port: {port}")

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_config=None,
        timeout_graceful_shutdown=20,
    )
