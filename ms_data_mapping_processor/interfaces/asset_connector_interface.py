"""Interface for Asset Connector REST API communication."""

import json
import logging
import time
from urllib.parse import urljoin

import requests
from pydantic import BaseModel, Field, PrivateAttr, ValidationError
from requests import Session

from ms_data_mapping_processor.models.response_body_models import AssetConnectorResponseBody

_logger = logging.getLogger(__name__)


class AssetConnectorClient(BaseModel):
    """Represents a AssetConnectorClient to communicate with a Asset Connector REST API.

    :param BaseModel: BaseModel from pydantic
    :return: A AssetConnectorClient instance.
    """

    base_url: str = Field(default="http://localhost:8000", description="The base URL of the Asset Connector REST API.", alias="BaseUrl")
    time_out: int = Field(default=200, description="API call timeout in seconds.", alias="TimeOut")
    trust_env: bool = Field(default=True, description="Disable proxy usage from environment.", alias="TrustEnv")
    connection_time_out: int = Field(default=100, description="Connection establishment timeout in seconds.", alias="ConnectionTimeOut")
    _session: Session = PrivateAttr(default=None)

    def __init__(self, **data):
        """Initialize the ConnectorClient with the given data."""
        super().__init__(**data)

        if self.base_url.endswith("/"):
            self.base_url = self.base_url[:-1]

        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})
        self._session.trust_env = self.trust_env

    def add_config(self, configuration: dict) -> AssetConnectorResponseBody | None:
        """Sets the configuration for the Asset Connector.

        :param configuration: The configuration dictionary to use for the request.
        :return: The response from the Asset Connector or None if an error occurred.
        """
        _logger.debug(f"Set configuration for Asset Connector at '{self.base_url}'.")
        url = urljoin(self.base_url, "/add-config")

        try:
            response = self._session.post(url, json=configuration)
            _logger.debug(f"Call REST API url '{response.url}'")

            if response.status_code != 200:
                _logger.error(f"{response.status_code} - Failed to call '{response.url}': {response.text}")
                return None

            ac_response = AssetConnectorResponseBody(**json.loads(response.content))

            if ac_response.status_code != 200:
                _logger.error(f"Failed to set config. {ac_response.status_code}: {ac_response.message} - {ac_response.value}")
                return None

            if not ac_response.value:
                _logger.error(f"Failed to retrieve AID submodel ID from response: {ac_response.message}")
                return None

            return ac_response

        except Exception as e:
            _logger.error(f"Failed to set config: {e}")
            return None

    def get_value(self, configuration: dict) -> AssetConnectorResponseBody | None:
        """Returns MQTT data from a given configuration.

        :param configuration: The configuration dictionary to use for the request.
        :return: The MQTT data or an error message.
        """
        _logger.debug(f"Get value from Asset Connector at '{self.base_url}'.")
        url = urljoin(self.base_url, "/get-value")

        try:
            response = self._session.post(url, json=configuration)
            _logger.debug(f"Call REST API url '{response.url}'")

            if response.status_code != 200:
                _logger.error(f"{response.status_code} - {response.url}': {response.text}")

            ac_response = AssetConnectorResponseBody(**json.loads(response.content))

            if ac_response.status_code != 200:
                _logger.error(f"Failed to get value. {ac_response.status_code}: {ac_response.message}")
                return None

            return ac_response

        except Exception as e:
            _logger.error(f"Failed to get value: {e}")
            return None

    def get_root(self) -> dict | None:
        """Returns the root information from the Asset Connector.

        :return: The root information or an error message.
        """
        try:
            response = self._session.get(self.base_url)
            _logger.debug(f"Call REST API url '{response.url}'")

            if response.status_code != 200:
                _logger.error(f"{response.status_code} - Failed to call '{response.url}': {response.text}")
                return None

            return response.json()

        except Exception as e:
            _logger.error(f"Failed to get root: {e}")
            return None


def create_client(config_dict: dict) -> AssetConnectorClient | None:
    """Create a HTTP client for a Asset Connector connection from a given configuration.

    :param config_dict: The configuration dictionary for the Asset Connector.
    :raises ValidationError: If the configuration is invalid.
    :return: A AssetConnectorClient instance or None if creation failed.
    """
    _logger.info("Create Asset Connector client.")

    try:
        config_string = json.dumps(config_dict, indent=4)
        client = AssetConnectorClient.model_validate_json(config_string)
    except ValidationError as ve:
        raise ValidationError(f"Invalid Asset Connector configuration file: {ve}") from ve

    _logger.info(f"Using Asset Connector configuration: '{client.base_url}'.'")

    connected = _establish_connection(client)

    if not connected:
        return None

    return client


def _establish_connection(client: AssetConnectorClient) -> bool:
    start_time = time.time()
    _logger.info(f"Try to connect to Asset Connector REST API '{client.base_url}' for {client.connection_time_out} seconds")
    counter: int = 0
    while True:
        try:
            root = client.get_root()
            if root:
                _logger.info(f"Connected to Asset Connector REST API at '{client.base_url}' successfully.")
                return True
        except requests.exceptions.ConnectionError:
            pass
        if time.time() - start_time > client.connection_time_out:
            _logger.error(f"Connection to Asset Connector REST API timed out after {client.connection_time_out} seconds.")
            return False

        counter += 1
        _logger.warning(f"Retrying connection to Asset Connector (attempt: {counter})")
        time.sleep(5)
