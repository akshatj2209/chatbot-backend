from fastapi import APIRouter, HTTPException, Body
from typing import List
from chatbot_backend.schema import ConversationCreate, ConversationOut, MessageOut, MessageCreate, MessageUpdate
from chatbot_backend.crud import (
    create_conversation, 
    get_conversation_messages_with_versions, 
    get_message_with_versions, 
    create_message, 
    update_message, 
    delete_message
)
from chatbot_backend.ai_logic import generate_ai_response
from bson import ObjectId
from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorClient
from chatbot_backend.api.deps import get_db

router = APIRouter()

@router.post("/chat/conversations", response_model=ConversationOut)
async def api_create_conversation(conversation: ConversationCreate, db: AsyncIOMotorClient = Depends(get_db)):
    return await create_conversation(db, conversation)

@router.post("/chat/conversations/{conversation_id}/chat", response_model=List[MessageOut])
async def api_chat_with_ai(conversation_id: str, user_message: MessageCreate, db: AsyncIOMotorClient = Depends(get_db)):
    try:
        # Save user message
        user_msg = await create_message(db, user_message, ObjectId(conversation_id))
        
        # Get conversation context
        context = await get_conversation_messages_with_versions(db, ObjectId(conversation_id))
        context_str = " ".join([msg.versions[-1].content for msg in context])
        
        # Generate AI response
        ai_response = await generate_ai_response(context_str + " " + user_message.content)
        
        # Save AI message
        ai_msg = await create_message(db, MessageCreate(content=ai_response), ObjectId(conversation_id))
        
        return [
            await get_message_with_versions(user_msg.id), 
            await get_message_with_versions(ai_msg.id)
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/messages/{message_id}", response_model=List[MessageOut])
async def api_edit_message_and_regenerate(message_id: str, message_update: MessageUpdate):
    try:
        # Update the message
        updated_message, new_version = await update_message(ObjectId(message_id), message_update)
        if not updated_message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        # Get updated conversation context
        context = await get_conversation_messages_with_versions(updated_message.conversation_id)
        context_str = " ".join([msg.versions[-1].content for msg in context])
        
        # Regenerate AI response
        ai_response = await generate_ai_response(context_str)
        
        # Save new AI message
        ai_msg = await create_message(MessageCreate(content=ai_response), updated_message.conversation_id)
        
        return [
            await get_message_with_versions(updated_message.id), 
            await get_message_with_versions(ai_msg.id)
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageOut])
async def api_get_conversation_messages(conversation_id: str):
    try:
        return await get_conversation_messages_with_versions(ObjectId(conversation_id))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/messages/{message_id}", response_model=dict)
async def api_delete_message(message_id: str):
    deleted = await delete_message(ObjectId(message_id))
    if not deleted:
        raise HTTPException(status_code=404, detail="Message not found")
    return {"status": "success", "message": "Message deleted"}
