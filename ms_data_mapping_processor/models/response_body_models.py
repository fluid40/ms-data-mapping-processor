"""Module defining the response body model classes."""

from typing import Any

from pydantic import BaseModel, Field


class AssetConnectorResponseBody(BaseModel):  # noqa: D101
    status_code: int = Field(
        default=200,
        description="The HTTP status code of the response.",
        alias="StatusCode",
        example=200,
    )

    message: str = Field(
        default="Successfully",
        description="A message providing additional information about the response.",
        alias="Message",
        example="Successfully invoked `/set-config` with raw JSON in payload",
    )

    payload: Any = Field(
        default={},
        description="Json content of the response.",
        alias="Payload",
        example="",
    )

    value: str = Field(
        default="",
        description="The value returned by the operation, if applicable.",
        alias="Value",
        example="myResult",
    )

    def get_success(self) -> bool:  # noqa: D102
        return self.status_code == 200
