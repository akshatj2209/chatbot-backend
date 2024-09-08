from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from chatbot_backend.config import settings
from motor.motor_asyncio import AsyncIOMotorClient

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def get_database_client() -> AsyncIOMotorClient:
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    return client

# Add this function to get the database
async def get_db():
    client = get_database_client()
    try:
        yield client[settings.DATABASE_NAME]
    finally:
        client.close()

async def get_api_key(api_key: str = Depends(api_key_header)):
    if api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key"
        )
    return api_key