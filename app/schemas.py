from pydantic import BaseModel, EmailStr, Field, UUID4
from typing import Optional
from datetime import datetime


# Book schemas
class BookBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    author: str = Field(..., min_length=1, max_length=200)
    price: float = Field(..., gt=0)
    genre: str = Field(..., min_length=1, max_length=100)
    cover: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    rating: float = Field(..., ge=0, le=5)
    year: int = Field(..., gt=0)


class BookCreate(BookBase):
    pass


class BookUpdate(BookBase):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    author: Optional[str] = Field(None, min_length=1, max_length=200)
    price: Optional[float] = Field(None, gt=0)
    genre: Optional[str] = Field(None, min_length=1, max_length=100)
    cover: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = Field(None, min_length=1)
    rating: Optional[float] = Field(None, ge=0, le=5)
    year: Optional[int] = Field(None, gt=0)


class BookResponse(BaseModel):
    id: UUID4
    title: str
    author: str
    price: float
    genre: str
    cover: str
    description: str
    rating: float
    year: int
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
