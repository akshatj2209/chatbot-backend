from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient
from ..config import settings

class Database:
    client: AsyncIOMotorClient = None

db = Database()

def get_sync_database():
    return MongoClient(settings.MONGODB_URL)[settings.DATABASE_NAME]

async def get_database() -> AsyncIOMotorClient:
    return db.client[settings.DATABASE_NAME]

async def connect_to_mongo():
    db.client = AsyncIOMotorClient(settings.MONGODB_URL)
    print("Connected to MongoDB")

async def close_mongo_connection():
    db.client.close()
    print("Closed MongoDB connection")