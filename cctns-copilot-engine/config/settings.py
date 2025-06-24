"""
CCTNS Copilot Engine Configuration
"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "CCTNS Copilot Engine"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database
    ORACLE_CONNECTION_STRING: Optional[str] = None
    DATABASE_POOL_SIZE: int = 10
    DATABASE_TIMEOUT: int = 30
    
    # Models Configuration
    MODELS_DIR: Path = Path("./models_cache")
    USE_GPU: bool = torch.cuda.is_available() if 'torch' in globals() else False
    
    # Speech-to-Text
    STT_MODEL_PRIMARY: str = "ai4bharat/indicconformer"
    STT_MODEL_FALLBACK: str = "openai/whisper-medium"
    STT_LANGUAGE_DEFAULT: str = "te"  # Telugu
    STT_CONFIDENCE_THRESHOLD: float = 0.7
    
    # Text Processing
    TEXT_CLEANUP_MODEL: str = "google/flan-t5-base"
    TEXT_MAX_LENGTH: int = 512
    
    # SQL Generation
    NL2SQL_MODEL: str = "microsoft/CodeT5-base"
    SQL_TIMEOUT: int = 30
    SQL_MAX_RESULTS: int = 1000
    
    # Report Generation
    SUMMARY_MODEL: str = "google/pegasus-cnn_dailymail"
    REPORTS_DIR: Path = Path("./reports")
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    API_KEY_HEADER: str = "X-API-Key"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()