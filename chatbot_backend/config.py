from pydantic import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "FastAPI Chatbot"
    DEBUG_MODE: bool = False
    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "chatbot_db"
    API_V1_STR: str = "/api/v1"
    API_KEY: str = "your-secret-api-key-here"  # Change this!
    GEMINI_API_KEY: str = "your-gemini-api-key-here"  # Change this!

    class Config:
        env_file = ".env"

settings = Settings()