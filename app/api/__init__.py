from flask import Blueprint
from flask_restx import Api

blueprint = Blueprint("api", __name__)

api = Api(
    blueprint,
    title="Book Store API",
    version="1.0",
    description="Book Store API with books and user management",
    doc="/docs",
)

# Import namespaces
from app.api.books import ns as books_ns
from app.api.users import ns as users_ns
from app.api.genres import ns as genres_ns

# Register namespaces
api.add_namespace(books_ns)
api.add_namespace(users_ns)
api.add_namespace(genres_ns)
