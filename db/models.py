from enum import unique
from datetime import datetime
import uuid

from flask_login import UserMixin

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

Base = declarative_base()

class User(Base, UserMixin):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(length=80), unique=True)
    email = Column(String(length=80), unique=True)
    password_hash = Column(String(length=255))


class Genre(Base):
    __tablename__ = "genres"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    # books = relationship('Book', back_populates='genre')  # если нужно получить все книги жанра


class Book(Base):
    __tablename__ = "books"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    author = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    genre_id = Column(Integer, ForeignKey("genres.id"), nullable=False)
    genre = relationship("Genre")
    cover = Column(String, nullable=False)
    description = Column(String, nullable=False)
    rating = Column(Float, nullable=False)
    year = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True)
    book_id = Column(UUID(as_uuid=True), ForeignKey("books.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rating = Column(Float, nullable=False)
    comment = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    book = relationship("Book", backref="reviews")
    user = relationship("User", backref="reviews")
