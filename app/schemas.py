from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
import re


# User schemas
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=80)
    email: EmailStr
    phone: str = Field(..., pattern=r"^\+?1?\d{9,15}$")  # Валидация номера телефона


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)
    confirm_password: str

    @validator("confirm_password")
    def passwords_match(cls, v, values, **kwargs):
        if "password" in values and v != values["password"]:
            raise ValueError("passwords do not match")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserVerify(BaseModel):
    phone: str = Field(..., pattern=r"^\+?1?\d{9,15}$")
    code: str = Field(..., min_length=6, max_length=6)


class UserResponse(UserBase):
    id: int
    is_verified: bool

    class Config:
        from_attributes = True


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


# Genre schemas
class GenreBase(BaseModel):
    name: str


class GenreCreate(GenreBase):
    pass


class GenreResponse(GenreBase):
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
