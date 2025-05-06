from flask_restx import Api, Resource, fields
from flask import Blueprint
from db.database import session_scope
from app.models import Book
from sqlalchemy.exc import SQLAlchemyError
from flask_login import current_user, login_required
from flask_restx import abort
from db.models import User

# Create blueprint
blueprint = Blueprint("api", __name__)

# Create API
api = Api(
    blueprint,
    title="Book Store API",
    version="1.0",
    description="A simple Book Store API",
    doc="/docs",
    mask_headers=False,
)

# Create namespace
ns = api.namespace("books", description="Book operations")

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
        "year": fields.Integer(required=True, description="Book publication year"),
        "created_at": fields.DateTime(description="Creation timestamp"),
        "updated_at": fields.DateTime(description="Last update timestamp"),
    },
)

# Book creation model (without id and timestamps)
book_create_model = api.model(
    "BookCreate",
    {
        "title": fields.String(required=True, description="Book title"),
        "author": fields.String(required=True, description="Book author"),
        "price": fields.Float(required=True, description="Book price"),
        "genre": fields.String(required=True, description="Book genre"),
        "cover": fields.String(required=True, description="Book cover URL"),
        "description": fields.String(required=True, description="Book description"),
        "rating": fields.Float(required=True, description="Book rating"),
        "year": fields.Integer(required=True, description="Publication year"),
    },
)

user_model = api.model(
    "User",
    {
        "id": fields.Integer(description="User ID"),
        "username": fields.String(required=True, description="Username"),
        "email": fields.String(required=True, description="Email address"),
    },
)


@ns.route("/")
class BookList(Resource):
    @ns.doc("list_books")
    @ns.marshal_list_with(book_model)
    def get(self):
        """List all books"""
        with session_scope() as db:
            books = db.query(Book).all()
            return books

    @ns.doc("create_book")
    @ns.expect(book_create_model)
    @ns.marshal_with(book_model, code=201)
    def post(self):
        """Create a new book"""
        with session_scope() as db:
            try:
                book = Book(**api.payload)
                db.add(book)
                db.commit()
                return book, 201
            except SQLAlchemyError as e:
                db.rollback()
                api.abort(400, str(e))


@ns.route("/<int:id>")
@ns.param("id", "The book identifier")
@ns.response(404, "Book not found")
class BookResource(Resource):
    @ns.doc("get_book")
    @ns.marshal_with(book_model)
    def get(self, id):
        """Get a book by ID"""
        with session_scope() as db:
            book = db.query(Book).filter(Book.id == id).first()
            if not book:
                api.abort(404, f"Book {id} not found")
            return book

    @ns.doc("update_book")
    @ns.expect(book_create_model)
    @ns.marshal_with(book_model)
    def put(self, id):
        """Update a book"""
        with session_scope() as db:
            book = db.query(Book).filter(Book.id == id).first()
            if not book:
                api.abort(404, f"Book {id} not found")

            try:
                for key, value in api.payload.items():
                    setattr(book, key, value)
                db.commit()
                return book
            except SQLAlchemyError as e:
                db.rollback()
                api.abort(400, str(e))

    @ns.doc("delete_book")
    @ns.response(204, "Book deleted")
    def delete(self, id):
        """Delete a book"""
        with session_scope() as db:
            book = db.query(Book).filter(Book.id == id).first()
            if not book:
                api.abort(404, f"Book {id} not found")

            try:
                db.delete(book)
                db.commit()
                return "", 204
            except SQLAlchemyError as e:
                db.rollback()
                api.abort(400, str(e))


@ns.route("/profile")
class UserProfile(Resource):
    @ns.doc("get_profile")
    @ns.marshal_with(user_model)
    @ns.response(200, "Success")
    @ns.response(401, "Not authenticated")
    @login_required
    def get(self):
        """Get user profile"""
        if not current_user.is_authenticated:
            abort(401, "Unauthorized")
        with session_scope() as db:
            user = db.query(User).get(current_user.id)
            if not user:
                abort(404, "User not found")
            return {
                "id": user.id,
                "username": user.username,
                "email": user.email,
            }


@api.route("/me")
class UserResource(Resource):
    @login_required
    def get(self):
        """Get current user info"""
        with session_scope() as db:
            user = db.query(User).get(current_user.id)
            if not user:
                abort(404, "User not found")
            return {
                "id": user.id,
                "username": user.username,
                "email": user.email,
            }

    @login_required
    def put(self):
        """Update current user info"""
        with session_scope() as db:
            user = db.query(User).get(current_user.id)
            if not user:
                abort(404, "User not found")
            if "username" in api.payload:
                user.username = api.payload["username"]
            if "email" in api.payload:
                user.email = api.payload["email"]
            db.commit()
            return {
                "id": user.id,
                "username": user.username,
                "email": user.email,
            }

    @login_required
    def delete(self):
        """Delete current user"""
        with session_scope() as db:
            user = db.query(User).get(current_user.id)
            if not user:
                abort(404, "User not found")
            db.delete(user)
            db.commit()
            return "", 204
