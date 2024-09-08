from pydantic import BaseModel, Field, validator
from typing import Optional
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

class VersionBase(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000)

class VersionCreate(VersionBase):
    message_id: PyObjectId

class VersionInDB(VersionBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    message_id: PyObjectId
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class VersionOut(VersionInDB):
    pass