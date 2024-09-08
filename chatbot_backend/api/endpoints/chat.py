from fastapi import APIRouter, Depends, HTTPException, Path
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import List

from chatbot_backend.api.deps import get_db
from chatbot_backend.schema import ConversationCreate, MessageCreate, MessageUpdate, ConversationOut, MessageOut
from chatbot_backend.models import Message
from chatbot_backend.crud import crud_conversation
import google.generativeai as genai
from chatbot_backend.config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

router = APIRouter()

# Helper function to validate ObjectId
def validate_object_id(id: str) -> ObjectId:
    try:
        return ObjectId(id)
    except:
        raise HTTPException(status_code=400, detail="Invalid ID format")

# Endpoints
async def generate_ai_response(conversation_history: List[str], user_message: str) -> str:
    prompt = f"Conversation history:\n{' '.join(conversation_history)}\nUser: {user_message}\nAI:"
    response = model.generate_content(prompt)
    return response.text

@router.post("/conversations/", response_model=ConversationOut)
async def create_conversation(conversation: ConversationCreate, db: AsyncIOMotorDatabase = Depends(get_db)):
    created_conversation = await crud_conversation.create_conversation(db, conversation)
    if created_conversation:
        return created_conversation
    raise HTTPException(status_code=500, detail="Failed to create conversation")

@router.post("/conversations/{conversation_id}/messages", response_model=List[MessageOut])
async def send_chat_message(
    conversation_id: str = Path(..., description="The ID of the conversation"),
    message: MessageCreate = ...,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    conv_id = validate_object_id(conversation_id)
    
    # Fetch the conversation to get history
    conversation = await crud_conversation.get_conversation(db, conv_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Prepare conversation history
    history = [msg.versions[-1].content for msg in conversation.messages[-5:]]  # Last 5 messages
    
    # Find the last AI message to set as parent for the new user message
    last_ai_message = next((msg for msg in reversed(conversation.messages) if msg.sender == "ai"), None)
    
    if last_ai_message:
        message.parent_id = last_ai_message.id
        message.parent_version = last_ai_message.current_version
    
    # Save user message
    user_message = await crud_conversation.add_message(db, conv_id, message)
    if not user_message:
        raise HTTPException(status_code=500, detail="Failed to save user message")
    
    # Generate AI response
    ai_response_content = await generate_ai_response(history, message.content)
    
    # Save AI response
    ai_message = await crud_conversation.add_message(
        db, 
        conv_id, 
        MessageCreate(content=ai_response_content, sender="ai", parent_id=str(user_message.id), parent_version=user_message.current_version)
    )
    if not ai_message:
        raise HTTPException(status_code=500, detail="Failed to save AI response")
    
    # Fetch the updated conversation
    updated_conversation = await crud_conversation.get_conversation(db, conv_id)
    if not updated_conversation:
        raise HTTPException(status_code=404, detail="Failed to retrieve updated conversation")
    
    return updated_conversation.messages

@router.put("/conversations/{conversation_id}/messages/{message_id}", response_model=List[MessageOut])
async def edit_message(
    conversation_id: str = Path(..., description="The ID of the conversation"),
    message_id: str = Path(..., description="The ID of the message to edit"),
    message_update: MessageUpdate = ...,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    conv_id = validate_object_id(conversation_id)
    msg_id = validate_object_id(message_id)
    
    # Update the message
    updated_message = await crud_conversation.update_message(db, conv_id, msg_id, message_update)
    if not updated_message:
        raise HTTPException(status_code=404, detail="Message not found or couldn't be updated")
    
    # Fetch the conversation to get updated history
    conversation = await crud_conversation.get_conversation(db, conv_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Prepare conversation history
    history = [msg.versions[-1].content for msg in conversation.messages[-5:]]  # Last 5 messages
    
    # Generate new AI response based on the edited message
    ai_response_content = await generate_ai_response(history, message_update.content)
    
    # Save new AI response
    ai_message = await crud_conversation.add_message(
        db, 
        conv_id, 
        MessageCreate(content=ai_response_content, sender="ai", parent_id=str(updated_message.id), parent_version=updated_message.current_version)
    )

    if not ai_message:
        raise HTTPException(status_code=500, detail="Failed to save new AI response")
    
    return [updated_message, ai_message]

@router.get("/conversations/{conversation_id}/messages/{message_id}/versions/{version_id}", response_model=MessageOut)
async def change_message_version(
    conversation_id: str = Path(..., description="The ID of the conversation"),
    message_id: str = Path(..., description="The ID of the message"),
    version_id: str = Path(..., description="The version ID to change to"),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    conv_id = validate_object_id(conversation_id)
    msg_id = validate_object_id(message_id)
    conversation = await crud_conversation.get_conversation(db, conv_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    for message in conversation.messages:
        if message.id == msg_id:
            for version in message.versions:
                if version.id == version_id:
                    return Message(
                        id=message.id,
                        parent_id=message.parent_id,
                        parent_version=message.parent_version,
                        sender=message.sender,
                        current_version=version_id,
                        versions=message.versions
                    )
            raise HTTPException(status_code=404, detail="Version not found")
    raise HTTPException(status_code=404, detail="Message not found")

@router.delete("/conversations/{conversation_id}/messages/{message_id}", response_model=bool)
async def delete_message(
    conversation_id: str = Path(..., description="The ID of the conversation"),
    message_id: str = Path(..., description="The ID of the message to delete"),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    conv_id = validate_object_id(conversation_id)
    msg_id = validate_object_id(message_id)
    deleted = await crud_conversation.delete_message(db, conv_id, msg_id)
    if deleted:
        return True
    raise HTTPException(status_code=404, detail="Message not found or couldn't be deleted")

@router.get("/conversations/{conversation_id}", response_model=ConversationOut)
async def get_conversation(
    conversation_id: str = Path(..., description="The ID of the conversation"),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    conv_id = validate_object_id(conversation_id)
    conversation = await crud_conversation.get_conversation(db, conv_id)
    if conversation:
        return conversation
    raise HTTPException(status_code=404, detail="Conversation not found")