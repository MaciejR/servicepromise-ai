from functools import lru_cache
import os
from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, model_validator


class Settings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    database_url: str = "sqlite:///./servicepromise.db"
    payment_mode: str = "demo"
    public_url: str = "http://localhost:5173"
    cors_origins: str = "http://localhost:5173"
    paypal_client_id: str = ""
    paypal_client_secret: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment: str = ""
    operator_token: str = ""
    auto_refund: bool = False
    catalog_paypal_sandbox_enabled: bool = False

    def __init__(self, _env_file=".env", **values):
        file_values = dotenv_values(_env_file) if _env_file else {}
        environment = {**file_values, **os.environ}
        resolved = {key: environment[key.upper()] for key in type(self).model_fields if key.upper() in environment}
        super().__init__(**{**resolved, **values})

    @model_validator(mode="after")
    def valid(self):
        if self.payment_mode not in {"demo", "sandbox"}:
            raise ValueError("Only demo and PayPal sandbox are supported")
        if self.payment_mode == "sandbox" and not all([
            self.paypal_client_id, self.paypal_client_secret, self.operator_token,
            self.azure_openai_endpoint, self.azure_openai_api_key, self.azure_openai_deployment,
        ]):
            raise ValueError("Sandbox requires PayPal credentials, Azure OpenAI and OPERATOR_TOKEN")
        if self.payment_mode == "sandbox" and len(self.operator_token) < 32:
            raise ValueError("OPERATOR_TOKEN must contain at least 32 characters")
        return self


@lru_cache
def settings():
    return Settings()
