# fastapi_chatbot/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatMessage(BaseModel):
    message: str


@app.post("/api/chat")
async def chat(chat_message: ChatMessage):
    # TODO: Implement your chatbot logic here
    # For now, we'll just echo the message
    return {"response": f"You said: {chat_message.message}"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("chatbot_backend.main:app", host="0.0.0.0", port=8000, reload=True)
