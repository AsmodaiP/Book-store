from flask_restx import Resource, fields, Namespace
from flask import request, jsonify
from app.api import api
from db.database import get_db
from db.models import Book, Genre, Review
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from app.schemas import BookCreate, BookUpdate, BookResponse, ReviewCreate, ReviewResponse
from uuid import UUID
from flask_login import login_required, current_user
from sqlalchemy import func
import json
from pydantic import ValidationError

# Create namespace
ns = Namespace("books", description="Book operations")

# Define models for Swagger documentation
book_model = api.model(
    "Book",
    {
        "id": fields.Integer(description="Book ID"),
        "title": fields.String(required=True, description="Book title"),
        "author": fields.String(required=True, description="Book author"),
        "price": fields.Float(required=True, description="Book price"),
        "genre": fields.String(required=True, description="Book genre"),
        "cover": fields.String(required=True, description="Book cover URL"),
        "description": fields.String(required=True, description="Book description"),
        "rating": fields.Float(required=True, description="Book rating"),
        "year": fields.Integer(required=True, description="Publication year"),
        "created_at": fields.DateTime(description="Creation timestamp"),
        "updated_at": fields.DateTime(description="Last update timestamp"),
    },
)

review_model = api.model(
    "ReviewCreate",
    {
        "rating": fields.Float(required=True, description="Оценка (0-5)"),
        "comment": fields.String(required=False, description="Комментарий"),
    },
)


def book_to_response(book: Book) -> dict:
    return json.loads(
        BookResponse(
            id=book.id,
            title=str(book.title),
            author=str(book.author),
            price=float(book.price),
            genre=str(book.genre.name) if book.genre else "",
            cover=str(book.cover),
            description=str(book.description),
            rating=float(book.rating) if book.rating is not None else 0.0,
            year=int(book.year),
            created_at=book.created_at,
            updated_at=book.updated_at,
        ).json()
    )


def review_to_response(review: Review) -> dict:
    return json.loads(ReviewResponse.from_orm(review).json())


@ns.route("/")
class BookList(Resource):
    @ns.doc("list_books")
    @ns.marshal_list_with(book_model)
    def get(self):
        """List all books"""
        db = get_db()
        books = db.query(Book).all()
        return [book_to_response(book) for book in books]

    @ns.doc("create_book")
    @ns.expect(book_model)
    @ns.marshal_with(book_model, code=201)
    def post(self):
        """Create a new book"""
        try:
            # Validate input data using Pydantic
            book_data = BookCreate(**api.payload)
            db = get_db()
            # Проверка на уникальность
            existing = (
                db.query(Book).filter_by(title=book_data.title, author=book_data.author, year=book_data.year).first()
            )
            if existing:
                api.abort(400, "Book with this title, author, and year already exists")
            genre = db.query(Genre).filter_by(name=book_data.genre).first()
            if not genre:
                genre = Genre(name=book_data.genre)
                db.add(genre)
                db.commit()
            book = Book(
                title=book_data.title,
                author=book_data.author,
                price=book_data.price,
                genre_id=genre.id,
                cover=book_data.cover,
                description=book_data.description,
                rating=book_data.rating,
                year=book_data.year,
            )
            db.add(book)
            db.commit()
            db.refresh(book)
            return book_to_response(book), 201
        except SQLAlchemyError as e:
            db.rollback()
            api.abort(400, str(e))


@ns.route("/<int:id>")
class BookResource(Resource):
    @ns.doc("get_book")
    @ns.marshal_with(book_model)
    def get(self, id: int):
        """Get a book by ID"""
        db = get_db()
        book = db.query(Book).filter(Book.id == id).first()
        if not book:
            api.abort(404, message=f"Book {id} not found")
        return book_to_response(book)

    @ns.doc("update_book")
    @ns.expect(book_model)
    @ns.marshal_with(book_model)
    def put(self, id: int):
        """Update a book"""
        db = get_db()
        book = db.query(Book).filter(Book.id == id).first()
        if not book:
            api.abort(404, message=f"Book {id} not found")

        data = request.json
        for key, value in data.items():
            setattr(book, key, value)

        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            api.abort(400, message="Invalid data")

        return book_to_response(book)

    @ns.doc("delete_book")
    @ns.response(204, "Book deleted")
    def delete(self, id: int):
        """Delete a book"""
        db = get_db()
        book = db.query(Book).filter(Book.id == id).first()
        if not book:
            api.abort(404, message=f"Book {id} not found")

        db.delete(book)
        db.commit()
        return "", 204


@ns.route("/top")
class TopBooks(Resource):
    @ns.doc("top_books")
    @ns.param("limit", "Number of top books to return", type=int, default=10)
    def get(self):
        """Get top books by average rating. Use ?limit=N to limit results."""
        db = get_db()
        limit = int(request.args.get("limit", 10))
        books = db.query(Book).order_by(Book.rating.desc()).limit(limit).all()
        return [book_to_response(book) for book in books]


@ns.route("/<int:book_id>/review")
class BookReview(Resource):
    @login_required
    @ns.expect(review_model)
    def post(self, book_id):
        """Add or update a review for a book (one review per user per book)."""
        db = get_db()
        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            return {"error": "Book not found"}, 404
        data = api.payload
        review_data = ReviewCreate(**data)
        # Найти существующий отзыв
        review = db.query(Review).filter_by(book_id=book.id, user_id=current_user.id).first()
        if review:
            review.rating = review_data.rating
            review.comment = review_data.comment
        else:
            review = Review(
                book_id=book.id,
                user_id=current_user.id,
                rating=review_data.rating,
                comment=review_data.comment,
            )
            db.add(review)
        db.commit()
        # Пересчитать средний рейтинг
        avg_rating = db.query(func.avg(Review.rating)).filter(Review.book_id == book.id).scalar()
        book.rating = avg_rating
        db.commit()
        return review_to_response(review), 201

    @login_required
    def delete(self, book_id):
        """Delete your review for a book and update book rating."""
        db = get_db()
        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            return {"error": "Book not found"}, 404
        review = db.query(Review).filter_by(book_id=book.id, user_id=current_user.id).first()
        if not review:
            return {"error": "Review not found"}, 404
        db.delete(review)
        db.commit()
        # Пересчитать средний рейтинг
        avg_rating = db.query(func.avg(Review.rating)).filter(Review.book_id == book.id).scalar()
        avg_rating = 0 if avg_rating is None else avg_rating
        book.rating = avg_rating
        db.commit()
        return "", 204


@ns.route("/<int:book_id>/reviews")
class BookReviews(Resource):
    def get(self, book_id):
        """Get all reviews for a book."""
        db = get_db()
        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            return {"error": "Book not found"}, 404
        reviews = db.query(Review).filter_by(book_id=book.id).order_by(Review.created_at.desc()).all()
        return [review_to_response(r) for r in reviews]
