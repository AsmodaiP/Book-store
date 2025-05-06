from flask_restx import Resource, fields, Namespace
from flask import request
from db.database import get_db
from db.models import Genre
from sqlalchemy.exc import IntegrityError

# Create namespace
ns = Namespace("genres", description="Genre operations")

# Define models for Swagger documentation
genre_model = ns.model(
    "Genre",
    {
        "id": fields.Integer(description="Genre ID"),
        "name": fields.String(required=True, description="Genre name"),
    },
)


@ns.route("/")
class GenreList(Resource):
    @ns.doc("list_genres")
    @ns.marshal_list_with(genre_model)
    def get(self):
        """List all genres"""
        db = get_db()
        genres = db.query(Genre).all()
        return genres

    @ns.doc("create_genre")
    @ns.expect(genre_model)
    @ns.marshal_with(genre_model, code=201)
    def post(self):
        """Create a new genre"""
        db = get_db()
        try:
            genre = Genre(name=request.json["name"])
            db.add(genre)
            db.commit()
            db.refresh(genre)
            return genre, 201
        except IntegrityError:
            db.rollback()
            ns.abort(400, message="Genre with this name already exists")
        except Exception as e:
            db.rollback()
            ns.abort(400, message=str(e))


@ns.route("/<int:id>")
class GenreResource(Resource):
    @ns.doc("get_genre")
    @ns.marshal_with(genre_model)
    def get(self, id):
        """Get a genre by ID"""
        db = get_db()
        genre = db.query(Genre).filter(Genre.id == id).first()
        if not genre:
            ns.abort(404, message=f"Genre {id} not found")
        return genre

    @ns.doc("update_genre")
    @ns.expect(genre_model)
    @ns.marshal_with(genre_model)
    def put(self, id):
        """Update a genre"""
        db = get_db()
        genre = db.query(Genre).filter(Genre.id == id).first()
        if not genre:
            ns.abort(404, message=f"Genre {id} not found")

        try:
            genre.name = request.json["name"]
            db.commit()
            return genre
        except IntegrityError:
            db.rollback()
            ns.abort(400, message="Genre with this name already exists")
        except Exception as e:
            db.rollback()
            ns.abort(400, message=str(e))

    @ns.doc("delete_genre")
    @ns.response(204, "Genre deleted")
    def delete(self, id):
        """Delete a genre"""
        db = get_db()
        genre = db.query(Genre).filter(Genre.id == id).first()
        if not genre:
            ns.abort(404, message=f"Genre {id} not found")

        try:
            db.delete(genre)
            db.commit()
            return "", 204
        except Exception as e:
            db.rollback()
            ns.abort(400, message=str(e))
