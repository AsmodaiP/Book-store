import json
from pathlib import Path
from sqlalchemy.orm import Session
from db.models import Book, Genre

def migrate_books(db: Session) -> None:
    """
    Migrate books from catalog to database if they don't exist
    """
    # Check if we already have books in the database
    if db.query(Book).first():
        return

    # Read books catalog
    catalog_path = Path(__file__).parent.parent / "books_catalog.json"
    with open(catalog_path, "r", encoding="utf-8") as f:
        books_data = json.load(f)

    # Создать жанры
    genre_names = {book["genre"] for book in books_data}
    # Добавлять только те жанры, которых ещё нет в базе
    existing_genres = {g.name for g in db.query(Genre).filter(Genre.name.in_(genre_names)).all()}
    new_genres = [Genre(name=name) for name in genre_names if name not in existing_genres]
    if new_genres:
        db.add_all(new_genres)
        db.commit()
    genres_by_name = {g.name: g for g in db.query(Genre).all()}

    # Create book records
    books = [
        Book(
            title=book["title"],
            author=book["author"],
            price=book["price"],
            genre_id=genres_by_name[book["genre"]].id,
            cover=book["cover"],
            description=book["description"],
            rating=0,
            year=book["year"],
        )
        for book in books_data
    ]

    # Add all books to database
    db.add_all(books)
    db.commit() 
