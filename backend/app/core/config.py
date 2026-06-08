import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    APP_BASE_URL: str = os.getenv("APP_BASE_URL", "http://localhost:5173")
    LIVEKIT_URL: str = os.getenv("LIVEKIT_URL", "ws://localhost:7880")
    # PUBLIC URL is what browsers (Mac + Android) use to connect to LiveKit.
    # Must be the Mac's WiFi IP, not the Docker-internal hostname.
    LIVEKIT_PUBLIC_URL: str = os.getenv("LIVEKIT_PUBLIC_URL", os.getenv("LIVEKIT_URL", "ws://localhost:7880"))
    LIVEKIT_API_KEY: str = os.getenv("LIVEKIT_API_KEY", "devkey")
    LIVEKIT_API_SECRET: str = os.getenv("LIVEKIT_API_SECRET", "secret")
    LIVEKIT_TOKEN_TTL_SECONDS: int = int(os.getenv("LIVEKIT_TOKEN_TTL_SECONDS", "7200"))

settings = Settings()
