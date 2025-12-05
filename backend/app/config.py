from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "StreamProbeX"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4
    
    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost", "http://localhost:3000", "http://localhost:80"]
    
    # Storage
    LOGS_DIR: str = "./logs"
    DATA_DIR: str = "./data"
    THUMBNAILS_DIR: str = "./data/thumbnails"
    SPRITES_DIR: str = "./data/sprites"
    SEGMENTS_DIR: str = "./data/segments"
    
    # Monitoring
    MANIFEST_POLL_INTERVAL: int = 5  # seconds
    SPRITE_SEGMENT_COUNT: int = 100  # Create sprite every N segments
    THUMBNAIL_WIDTH: int = 160
    THUMBNAIL_HEIGHT: int = 90
    SPRITE_GRID_WIDTH: int = 10
    SPRITE_GRID_HEIGHT: int = 10
    
    # Logging
    LOG_ROTATION_HOUR: int = 0  # UTC hour for rotation
    LOG_COMPRESS_DAYS: int = 7
    LOG_DELETE_DAYS: int = 30
    
    # Performance
    MAX_CONCURRENT_DOWNLOADS: int = 10
    DOWNLOAD_TIMEOUT: int = 30
    SEGMENT_BUFFER_SIZE: int = 8192
    
    # Optional S3
    S3_ENABLED: bool = False
    S3_BUCKET: Optional[str] = None
    S3_REGION: Optional[str] = None
    S3_ACCESS_KEY: Optional[str] = None
    S3_SECRET_KEY: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
