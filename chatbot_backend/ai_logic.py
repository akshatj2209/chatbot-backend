import asyncio
from typing import List
import google.generativeai as genai
from chatbot_backend.schema import MessageCreate, MessageUpdate
from chatbot_backend.crud import create_message, update_message, get_conversation_messages, delete_message
from bson import ObjectId
from chatbot_backend.config import settings
from chatbot_backend.models import Message

# Initialize the Gemini AI model
genai.configure(api_key=settings.GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

async def generate_ai_response(context: List[str]) -> str:
    # Generate response using Gemini AI
    response = model.generate_content(" ".join(context))
    return response.text

async def chat_with_ai(conversation_id: ObjectId, user_message: str) -> List[Message]:
    # Get existing conversation context
    context = await get_conversation_messages(conversation_id)
    context_str = " ".join([msg.content for msg in context])
    
    # Save user message
    user_msg = await create_message(MessageCreate(content=user_message), conversation_id)
    
    # Generate AI response
    ai_response = await generate_ai_response(context_str + " " + user_message)
    
    # Save AI message
    ai_msg = await create_message(MessageCreate(content=ai_response), conversation_id)
    
    return [user_msg, ai_msg]

async def edit_message_and_regenerate(message_id: ObjectId, new_content: str) -> List[Message]:
    # Update the message
    updated_message = await update_message(message_id, MessageUpdate(content=new_content))
    
    if not updated_message:
        raise ValueError("Message not found")
    
    # Get the updated conversation context
    context = await get_conversation_messages(updated_message.conversation_id)
    context_str = " ".join([msg.content for msg in context])
    
    # Regenerate AI response
    ai_response = await generate_ai_response(context_str)
    
    # Save new AI message
    ai_msg = await create_message(MessageCreate(content=ai_response), updated_message.conversation_id)
    
    return [updated_message, ai_msg]