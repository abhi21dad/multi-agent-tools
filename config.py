"""
Centralized configuration management for LangGraph Chatbot.

This module loads and validates all configuration from environment variables.
It uses Pydantic for type safety and validation, and fails fast if required
configuration is missing or invalid.
"""

import os
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class OpenAIConfig(BaseModel):
    """OpenAI API configuration."""
    api_key: str = Field(..., description="OpenAI API key")
    
    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v):
        if not v or v.startswith('YOUR_') or v == 'sk-proj-YOUR_OPENAI_API_KEY_HERE':
            raise ValueError(
                "OPENAI_API_KEY is not configured. "
                "Please set it in your .env file. "
                "Get your API key from: https://platform.openai.com/api-keys"
            )
        return v


class LangChainConfig(BaseModel):
    """LangChain/LangSmith configuration."""
    tracing_enabled: bool = Field(default=False, description="Enable LangSmith tracing")
    endpoint: str = Field(default="https://api.smith.langchain.com")
    api_key: Optional[str] = Field(default=None, description="LangSmith API key")
    project: str = Field(default="chatbot", description="LangSmith project name")


class TwitterConfig(BaseModel):
    """Twitter/X API configuration."""
    api_key: Optional[str] = Field(default=None)
    api_key_secret: Optional[str] = Field(default=None)
    access_token: Optional[str] = Field(default=None)
    access_token_secret: Optional[str] = Field(default=None)
    
    @property
    def is_configured(self) -> bool:
        """Check if Twitter is properly configured."""
        return all([
            self.api_key,
            self.api_key_secret,
            self.access_token,
            self.access_token_secret
        ]) and not any([
            self.api_key.startswith('YOUR_') if self.api_key else False,
            self.api_key_secret.startswith('YOUR_') if self.api_key_secret else False,
        ])


class AlphaVantageConfig(BaseModel):
    """Alpha Vantage API configuration for stock data."""
    api_key: Optional[str] = Field(default=None)
    
    @property
    def is_configured(self) -> bool:
        """Check if Alpha Vantage is properly configured."""
        return (
            self.api_key is not None 
            and not self.api_key.startswith('YOUR_')
        )


class ServiceAuthConfig(BaseModel):
    """Authentication tokens for internal services."""
    file_server_token: str = Field(..., description="File server auth token")
    gdrive_server_token: str = Field(..., description="Google Drive server auth token")
    gmail_server_token: str = Field(..., description="Gmail server auth token")
    twitter_server_token: str = Field(..., description="Twitter server auth token")
    
    @field_validator('file_server_token', 'gdrive_server_token', 'gmail_server_token', 'twitter_server_token')
    @classmethod
    def validate_token(cls, v, info):
        if not v or v.startswith('YOUR_') or len(v) < 16:
            raise ValueError(
                f"{info.field_name} is not properly configured. "
                "Generate a secure token using: openssl rand -hex 32"
            )
        return v


class ServiceURLConfig(BaseModel):
    """URLs for internal microservices."""
    twitter_url: str = Field(default="http://127.0.0.1:5001")
    file_url: str = Field(default="http://127.0.0.1:5002")
    gdrive_url: str = Field(default="http://127.0.0.1:5003")
    gmail_url: str = Field(default="http://127.0.0.1:5004")


class AppConfig(BaseModel):
    """General application configuration."""
    environment: Literal["development", "staging", "production"] = Field(
        default="development"
    )
    debug: bool = Field(default=False)
    database_path: str = Field(default="chatbot.db")
    sandbox_directory: str = Field(default="file_sandbox")
    log_level: str = Field(default="INFO")
    
    # Optional production settings
    cors_origins: Optional[list[str]] = Field(default=None)
    rate_limit_per_minute: int = Field(default=60)
    sentry_dsn: Optional[str] = Field(default=None)


class Settings(BaseSettings):
    """Main configuration class that loads all settings."""
    
    openai: OpenAIConfig
    langchain: LangChainConfig
    twitter: TwitterConfig
    alpha_vantage: AlphaVantageConfig
    service_auth: ServiceAuthConfig
    service_urls: ServiceURLConfig
    app: AppConfig
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = 'allow'  # Allow extra env vars that are manually loaded
    
    @classmethod
    def load(cls) -> "Settings":
        """Load and validate settings from environment."""
        try:
            # Parse individual configs
            openai = OpenAIConfig(
                api_key=os.getenv("OPENAI_API_KEY", "")
            )
            
            langchain = LangChainConfig(
                tracing_enabled=os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true",
                endpoint=os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com"),
                api_key=os.getenv("LANGCHAIN_API_KEY"),
                project=os.getenv("LANGCHAIN_PROJECT", "chatbot")
            )
            
            twitter = TwitterConfig(
                api_key=os.getenv("TWITTER_API_KEY"),
                api_key_secret=os.getenv("TWITTER_API_KEY_SECRET"),
                access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
                access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
            )
            
            alpha_vantage = AlphaVantageConfig(
                api_key=os.getenv("ALPHA_VANTAGE_API_KEY")
            )
            
            service_auth = ServiceAuthConfig(
                file_server_token=os.getenv("FILE_SERVER_AUTH_TOKEN", ""),
                gdrive_server_token=os.getenv("GOOGLE_DRIVE_SERVER_AUTH_TOKEN", ""),
                gmail_server_token=os.getenv("GMAIL_SERVER_AUTH_TOKEN", ""),
                twitter_server_token=os.getenv("TWITTER_COMMAND_SERVER_AUTH_TOKEN", "")
            )
            
            service_urls = ServiceURLConfig(
                twitter_url=os.getenv("TWITTER_SERVER_URL", "http://127.0.0.1:5001"),
                file_url=os.getenv("FILE_SERVER_URL", "http://127.0.0.1:5002"),
                gdrive_url=os.getenv("GDRIVE_SERVER_URL", "http://127.0.0.1:5003"),
                gmail_url=os.getenv("GMAIL_SERVER_URL", "http://127.0.0.1:5004")
            )
            
            cors_origins_str = os.getenv("CORS_ORIGINS")
            cors_origins = cors_origins_str.split(",") if cors_origins_str else None
            
            app = AppConfig(
                environment=os.getenv("ENVIRONMENT", "development"),
                debug=os.getenv("DEBUG", "false").lower() == "true",
                database_path=os.getenv("DATABASE_PATH", "chatbot.db"),
                sandbox_directory=os.getenv("SANDBOX_DIRECTORY", "file_sandbox"),
                log_level=os.getenv("LOG_LEVEL", "INFO"),
                cors_origins=cors_origins,
                rate_limit_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")),
                sentry_dsn=os.getenv("SENTRY_DSN")
            )
            
            return cls(
                openai=openai,
                langchain=langchain,
                twitter=twitter,
                alpha_vantage=alpha_vantage,
                service_auth=service_auth,
                service_urls=service_urls,
                app=app
            )
            
        except Exception as e:
            print("\n" + "="*60)
            print("CONFIGURATION ERROR")
            print("="*60)
            print(f"\n{str(e)}\n")
            print("Please check your .env file and ensure all required")
            print("variables are set correctly.")
            print("\nSee .env.example for a template with all required variables.")
            print("="*60 + "\n")
            raise


# Global settings instance
settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global settings instance, loading if necessary."""
    global settings
    if settings is None:
        settings = Settings.load()
    return settings


# For backwards compatibility and testing
if __name__ == "__main__":
    """Test configuration loading."""
    print("Loading configuration...")
    try:
        config = get_settings()
        print("\n✅ Configuration loaded successfully!")
        print(f"\nEnvironment: {config.app.environment}")
        print(f"Debug mode: {config.app.debug}")
        print(f"Database: {config.app.database_path}")
        print(f"\nTwitter configured: {config.twitter.is_configured}")
        print(f"Alpha Vantage configured: {config.alpha_vantage.is_configured}")
        print(f"LangSmith tracing: {config.langchain.tracing_enabled}")
    except Exception as e:
        print(f"\n❌ Configuration failed: {e}")
        exit(1)
