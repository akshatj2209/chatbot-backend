from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import List, Optional, Set
from datetime import datetime

# Importing our schemas
from chatbot_backend.schema import ConversationCreate, MessageCreate, MessageUpdate, ConversationUpdate
from chatbot_backend.models import Conversation, Message, MessageVersion

class ConversationCRUD:
    @staticmethod
    async def create_conversation(db: AsyncIOMotorDatabase, conversation: ConversationCreate) -> Conversation:
        conversation_dict = conversation.dict()
        conversation_dict['created_at'] = datetime.utcnow()
        conversation_dict['updated_at'] = conversation_dict['created_at']
        conversation_dict['messages'] = []
        result = await db.conversations.insert_one(conversation_dict)
        return await ConversationCRUD.get_conversation(db, result.inserted_id)

    @staticmethod
    async def get_conversation(db: AsyncIOMotorDatabase, conversation_id: ObjectId) -> Optional[Conversation]:
        conversation = await db.conversations.find_one({"_id": conversation_id})
        if conversation:
            return Conversation(**conversation)
        return None

    @staticmethod
    async def update_conversation(db: AsyncIOMotorDatabase, conversation_id: ObjectId, update_data: ConversationUpdate) -> Optional[Conversation]:
        update_dict = update_data.dict(exclude_unset=True)
        update_dict['updated_at'] = datetime.utcnow()
        result = await db.conversations.update_one(
            {"_id": conversation_id},
            {"$set": update_dict}
        )
        if result.modified_count:
            return await ConversationCRUD.get_conversation(db, conversation_id)
        return None

    @staticmethod
    async def delete_conversation(db: AsyncIOMotorDatabase, conversation_id: ObjectId) -> bool:
        result = await db.conversations.delete_one({"_id": conversation_id})
        return result.deleted_count > 0

    @staticmethod
    async def delete_message(db: AsyncIOMotorDatabase, conversation_id: ObjectId, message_id: ObjectId) -> bool:
        conversation = await ConversationCRUD.get_conversation(db, conversation_id)
        if not conversation:
            return False

        # Find the message to delete
        message_to_delete = next((m for m in conversation.messages if m.id == message_id), None)
        if not message_to_delete:
            return False

        # Collect all descendant message IDs
        messages_to_delete = ConversationCRUD._collect_descendant_messages(conversation.messages, message_id)
        messages_to_delete.add(message_id)

        # If we're deleting all messages, delete the entire conversation
        if len(messages_to_delete) == len(conversation.messages):
            result = await db.conversations.delete_one({"_id": conversation_id})
            return result.deleted_count > 0

        # Update the parent's child_messages
        if message_to_delete.parent_id:
            await db.conversations.update_one(
                {"_id": conversation_id, "messages._id": message_to_delete.parent_id},
                {"$unset": {f"messages.$.versions.$[ver].child_messages.{str(message_id)}": ""}},
                array_filters=[{"ver.id": message_to_delete.parent_version}]
            )

        # Delete all collected messages
        result = await db.conversations.update_one(
            {"_id": conversation_id},
            {
                "$pull": {"messages": {"_id": {"$in": list(messages_to_delete)}}},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )

        return result.modified_count > 0

    @staticmethod
    def _collect_descendant_messages(messages: List[Message], parent_id: ObjectId) -> Set[ObjectId]:
        descendants = set()
        for message in messages:
            if message.parent_id == parent_id:
                descendants.add(message.id)
                descendants.update(ConversationCRUD._collect_descendant_messages(messages, message.id))
        return descendants

    @staticmethod
    async def add_message(db: AsyncIOMotorDatabase, conversation_id: ObjectId, message: MessageCreate) -> Optional[Message]:
        message_dict = message.dict()
        message_dict['_id'] = ObjectId()
        message_dict['current_version'] = "v1"
        message_dict['versions'] = [
            {
                "id": "v1",
                "content": message_dict.pop('content'),
                "created_at": datetime.utcnow(),
                "child_messages": {}
            }
        ]

        # Get the correct parent version
        if message_dict.get('parent_id'):
            parent_message = await ConversationCRUD._get_message(db, conversation_id, message_dict['parent_id'])
            if parent_message:
                message_dict['parent_version'] = parent_message.current_version

        update_result = await db.conversations.update_one(
            {"_id": conversation_id},
            {
                "$push": {"messages": message_dict},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )

        if update_result.modified_count:
            if message_dict.get('parent_id'):
                await ConversationCRUD._update_parent_child_messages(db, conversation_id, message_dict['parent_id'], message_dict['parent_version'], str(message_dict['_id']))
            return Message(**message_dict)
        return None

    @staticmethod
    async def update_message(db: AsyncIOMotorDatabase, conversation_id: ObjectId, message_id: ObjectId, update_data: MessageUpdate) -> Optional[Message]:
        conversation = await ConversationCRUD.get_conversation(db, conversation_id)
        if not conversation:
            return None

        for message in conversation.messages:
            if message.id == message_id:
                new_version = f"v{len(message.versions) + 1}"
                new_version_dict = {
                    "id": new_version,
                    "content": update_data.content,
                    "created_at": datetime.utcnow(),
                    "child_messages": {}
                }

                update_result = await db.conversations.update_one(
                    {"_id": conversation_id, "messages._id": message_id},
                    {
                        "$push": {"messages.$.versions": new_version_dict},
                        "$set": {
                            "messages.$.current_version": new_version,
                            "updated_at": datetime.utcnow()
                        }
                    }
                )

                if update_result.modified_count:
                    updated_conversation = await ConversationCRUD.get_conversation(db, conversation_id)
                    for updated_message in updated_conversation.messages:
                        if updated_message.id == message_id:
                            return updated_message
        return None

    @staticmethod
    async def _update_parent_child_messages(db: AsyncIOMotorDatabase, conversation_id: ObjectId, parent_id: ObjectId, parent_version: str, child_id: str):
        await db.conversations.update_one(
            {
                "_id": conversation_id,
                "messages._id": parent_id,
                "messages.versions.id": parent_version
            },
            {
                "$set": {
                    "messages.$[msg].versions.$[ver].child_messages": {child_id: "v1"}
                }
            },
            array_filters=[
                {"msg._id": parent_id},
                {"ver.id": parent_version}
            ]
        )

    @staticmethod
    async def _get_message(db: AsyncIOMotorDatabase, conversation_id: ObjectId, message_id: ObjectId) -> Optional[Message]:
        conversation = await ConversationCRUD.get_conversation(db, conversation_id)
        if conversation:
            for message in conversation.messages:
                if message.id == message_id:
                    return message
        return None

    @staticmethod
    async def get_all_conversations(db: AsyncIOMotorDatabase, skip: int = 0, limit: int = 100) -> List[Conversation]:
        cursor = db.conversations.find().skip(skip).limit(limit)
        conversations = await cursor.to_list(length=limit)
        return [Conversation(**conv) for conv in conversations]

    @staticmethod
    async def change_message_version(db: AsyncIOMotorDatabase, conversation_id: ObjectId, message_id: ObjectId, version_id: str) -> Optional[Conversation]:
        update_result = await db.conversations.update_one(
            {"_id": conversation_id, "messages._id": message_id},
            {
                "$set": {
                    "messages.$.current_version": version_id,
                    "updated_at": datetime.utcnow()
                }
            }
        )

        if update_result.modified_count:
            return await ConversationCRUD.get_conversation(db, conversation_id)
        return None

crud_conversation = ConversationCRUD()