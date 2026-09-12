"""Application Configuration using Pydantic BaseSettings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Global configuration settings for CampusVoice API."""

    PROJECT_NAME: str = "CampusVoice API"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = "AI-Powered Student Feedback Intelligence System"
    API_V1_STR: str = "/api/v1"

    class Config:
        case_sensitive = True


settings = Settings()
