from bson import ObjectId
from chatbot_backend.models import Conversation, Message, Version
from chatbot_backend.schema import MessageCreate, MessageUpdate, MessageInDB, MessageOut,MessageVersion, VersionCreate, ConversationCreate
from chatbot_backend.api.deps import get_db
from motor.motor_asyncio import AsyncIOMotorClient
from typing import List, Tuple

async def create_conversation(db: AsyncIOMotorClient, conversation: ConversationCreate) -> Conversation:
    conversation_dict = conversation.dict()
    result = await db.conversations.insert_one(conversation_dict)
    return Conversation(**conversation_dict, id=result.inserted_id)


async def delete_message(db: AsyncIOMotorClient, message_id: ObjectId) -> bool:
    result = await db.messages.delete_one({"_id": message_id})
    return result.deleted_count > 0

async def get_message_versions(db: AsyncIOMotorClient,message_id: ObjectId) -> List[Version]:
    versions = await db.versions.find({"message_id": message_id}).to_list(None)
    return [Version(**version) for version in versions]

async def get_conversation_messages(db: AsyncIOMotorClient, conversation_id: ObjectId) -> List[Message]:
    messages = await db.messages.find({"conversation_id": conversation_id}).to_list(None)
    return [Message(**message) for message in messages]

async def create_message(db: AsyncIOMotorClient, message: MessageCreate, conversation_id: ObjectId) -> MessageInDB:
    db_message = MessageInDB(**message.dict(), conversation_id=conversation_id, version=1)
    message_dict = message.dict()
    message_dict['conversation_id'] = conversation_id
    message_dict['current_version'] = 1
    result = await db.messages.insert_one(message_dict)
    
    # Create initial version
    version = MessageVersion(message_id=result.inserted_id, content=message.content)
    await db.message_versions.insert_one(version.dict(by_alias=True))
    
    return MessageInDB(**message_dict, id=result.inserted_id)

async def update_message(db: AsyncIOMotorClient, message_id: ObjectId, message_update: MessageUpdate) -> Tuple[MessageInDB, MessageVersion]:
    message = await db.messages.find_one({"_id": message_id})
    if not message:
        return None, None
    
    # Create a new version
    new_version_number = message['current_version'] + 1
    new_version = MessageVersion(message_id=message_id, content=message_update.content)
    await db.message_versions.insert_one(new_version.dict(by_alias=True))
    
    # Update the message
    update_data = message_update.dict(exclude_unset=True)
    update_data['updated_at'] = datetime.utcnow()
    update_data['current_version'] = new_version_number
    
    await db.messages.update_one(
        {"_id": message_id},
        {"$set": update_data}
    )
    
    updated_message = await db.messages.find_one({"_id": message_id})
    return MessageInDB(**updated_message), new_version

async def get_message_with_versions(db: AsyncIOMotorClient, message_id: ObjectId) -> MessageOut:
    message = await db.messages.find_one({"_id": message_id})
    if not message:
        return None
    
    versions = await db.message_versions.find({"message_id": message_id}).sort("created_at", 1).to_list(None)
    return MessageOut(**message, versions=versions)

async def get_conversation_messages_with_versions(db: AsyncIOMotorClient, conversation_id: ObjectId) -> List[MessageOut]:
    messages = await db.messages.find({"conversation_id": conversation_id}).sort("created_at", 1).to_list(None)
    
    message_outs = []
    for message in messages:
        versions = await db.message_versions.find({"message_id": message["_id"]}).sort("created_at", 1).to_list(None)
        message_outs.append(MessageOut(**message, versions=versions))
    
    return message_outs
