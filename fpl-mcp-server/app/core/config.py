# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
# Author: Anshul Kapoor
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This module defines the configuration settings for the FPL MCP server application.

It uses Pydantic's BaseSettings to load configuration from environment variables
or a .env file, ensuring that settings are loaded only once and cached for efficiency.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Defines the application's configuration settings.
    Pydantic automatically reads these from environment variables or a .env file.
    """
    GCP_PROJECT_ID: str
    FPL_API_BASE_URL: str
    SYNC_INTERVAL_HOURS: int = 8
    SYNC_SECRET: str
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

@lru_cache()
def get_settings() -> Settings:
    """
    Returns a cached instance of the Settings object.
    Using lru_cache ensures the settings are loaded only once.
    """
    return Settings()
