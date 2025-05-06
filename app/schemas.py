from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


# Book schemas
class BookBase(BaseModel):
    title: str
    author: str
    price: float
    genre: str
    cover: str
    description: str
    year: int


class BookCreate(BookBase):
    pass


class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    price: Optional[float] = None
    genre: Optional[str] = None
    cover: Optional[str] = None
    description: Optional[str] = None
    year: Optional[int] = None


class BookResponse(BookBase):
    id: int
    rating: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# User schemas
class UserBase(BaseModel):
    username: str = Field(..., min_length=4, max_length=100)
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=36)
    confirm_password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: int

    class Config:
        from_attributes = True


# Review schemas
class ReviewCreate(BaseModel):
    rating: float = Field(..., ge=0, le=5)
    comment: Optional[str] = None


class ReviewResponse(BaseModel):
    id: int
    user_id: int
    rating: float
    comment: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
