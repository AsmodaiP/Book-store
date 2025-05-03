from flask import Flask
from flask_login import LoginManager
from pydantic import ValidationError
from flask import jsonify

from config import settings
from db.database import init_db, get_db
from db.migrator import migrate_books
from app.api import blueprint as api_blueprint
from db.models import User
from dotenv import load_dotenv
from config import settings


app = Flask(import_name=__name__)
app.config["SECRET_KEY"] = settings.SECRET_KEY

# Setup Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)


# Configure unauthorized handler to return 401
@login_manager.unauthorized_handler
def unauthorized():
    return "", 401


@app.errorhandler(ValidationError)
def handle_pydantic_validation_error(e):
    return jsonify({"error": "Validation error", "details": e.errors()}), 400


@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    return db.query(User).get(int(user_id))


# Initialize database
init_db()

# Run migrations
with app.app_context():
    db = get_db()
    migrate_books(db)

# Register API blueprint
app.register_blueprint(blueprint=api_blueprint, url_prefix="/api")

if __name__ == '__main__':
    app.run(port=settings.APP_PORT, debug=True)
