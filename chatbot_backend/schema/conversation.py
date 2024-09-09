from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime
from bson import ObjectId

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")

# Schemas for creating new items

class MessageVersionCreate(BaseModel):
    content: str = Field(..., min_length=1)

class MessageCreate(BaseModel):
    parent_id: Optional[PyObjectId] = None
    parent_version: Optional[str] = None
    sender: str = Field(..., regex='^(user|ai)$')
    content: str = Field(..., min_length=1)

class ConversationCreate(BaseModel):
    title: str = Field(..., min_length=1)

# Schemas for responses

class MessageVersionOut(BaseModel):
    id: str
    content: str
    created_at: datetime
    child_messages: Dict[str, str] = {}

    class Config:
        orm_mode = True

class MessageOut(BaseModel):
    id: PyObjectId = Field(..., alias="_id")
    parent_id: Optional[PyObjectId] = None
    parent_version: Optional[str] = None
    sender: str
    current_version: str
    versions: List[MessageVersionOut]

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class ConversationOut(BaseModel):
    id: PyObjectId = Field(..., alias="_id")
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageOut]

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

# Schemas for updates

class MessageUpdate(BaseModel):
    content: str = Field(..., min_length=1)

class CreateResponse(BaseModel):
    message: MessageCreate
    language: str
    context: str

class UpdateResponse(BaseModel):
    message: MessageUpdate
    language: str
    context: str

class ConversationUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1)