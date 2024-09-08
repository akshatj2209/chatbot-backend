from .message import PyObjectId
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from bson import ObjectId

class Version(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    message_id: PyObjectId
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}