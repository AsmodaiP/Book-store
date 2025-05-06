from flask_restx import Resource, fields, Namespace
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app.api import api
from db.database import get_db
from db.models import User
from app.schemas import UserCreate, UserLogin, UserResponse
from sqlalchemy.exc import SQLAlchemyError
from flask import request

# Create namespace
ns = Namespace("users", description="User operations")

# API models
user_model = ns.model(
    "User",
    {
        "username": fields.String(required=True, description="Username"),
        "email": fields.String(required=True, description="Email address"),
        "phone": fields.String(required=True, description="Phone number"),
        "password": fields.String(required=True, description="Password"),
        "confirm_password": fields.String(required=True, description="Confirm password"),
    },
)

user_response_model = ns.model(
    "UserResponse",
    {
        "id": fields.Integer(description="User ID"),
        "username": fields.String(description="Username"),
        "email": fields.String(description="Email address"),
        "phone": fields.String(description="Phone number"),
        "is_verified": fields.Boolean(description="Phone verification status"),
    },
)

registration_model = api.model(
    "Registration",
    {
        "username": fields.String(required=True, min_length=4, max_length=100, description="Username"),
        "email": fields.String(required=True, description="Email address"),
        "password": fields.String(required=True, min_length=8, max_length=36, description="Password"),
        "confirm_password": fields.String(required=True, description="Confirm password"),
    },
)

login_model = api.model(
    "Login",
    {
        "email": fields.String(required=True, description="Email address"),
        "password": fields.String(required=True, description="Password"),
    },
)


@ns.route("")
class UserList(Resource):
    @ns.doc("list_users")
    @ns.marshal_list_with(user_response_model)
    def get(self):
        """List all users"""
        db = get_db()
        users = db.query(User).all()
        return users

    @ns.doc("create_user")
    @ns.expect(user_model)
    @ns.marshal_with(user_response_model, code=201)
    def post(self):
        """Create a new user"""
        db = get_db()
        data = UserCreate(**request.json)

        # Проверяем, существует ли пользователь с таким email
        if db.query(User).filter(User.email == data.email).first():
            ns.abort(400, message="Email already registered")

        # Проверяем, существует ли пользователь с таким username
        if db.query(User).filter(User.username == data.username).first():
            ns.abort(400, message="Username already taken")

        # Проверяем, существует ли пользователь с таким номером телефона
        if db.query(User).filter(User.phone == data.phone).first():
            ns.abort(400, message="Phone number already registered")

        # Создаем нового пользователя
        user = User(
            username=data.username,
            email=data.email,
            phone=data.phone,
            password_hash=generate_password_hash(data.password),
            is_verified=False,  # По умолчанию телефон не подтвержден
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        return user, 201


@ns.route("/<int:id>")
@ns.param("id", "The user identifier")
class UserResource(Resource):
    @ns.doc("get_user")
    @ns.marshal_with(user_response_model)
    def get(self, id):
        """Get a user by ID"""
        db = get_db()
        user = db.query(User).filter(User.id == id).first()
        if not user:
            ns.abort(404, message="User not found")
        return user


@ns.route("/register")
class UserRegister(Resource):
    @ns.doc("register_user")
    @ns.expect(registration_model)
    @ns.response(201, "User successfully registered")
    @ns.response(400, "Validation error")
    def post(self):
        """Register a new user"""
        db = get_db()
        try:
            # Validate input data using Pydantic
            user_data = UserCreate(**api.payload)

            if user_data.password != user_data.confirm_password:
                return {"error": "Passwords do not match"}, 400

            # Check existing email
            if db.query(User).filter_by(email=user_data.email).first():
                return {"error": "User with this email already exists"}, 400

            # Check existing username
            if db.query(User).filter_by(username=user_data.username).first():
                return {"error": "User with this username already exists"}, 400

            user = User(
                username=user_data.username,
                email=user_data.email,
                phone=user_data.phone,
                password_hash=generate_password_hash(user_data.password),
                is_verified=False,  # По умолчанию телефон не подтвержден
            )
            db.add(user)
            db.commit()
            return {"message": "User registered successfully"}, 201
        except SQLAlchemyError as e:
            db.rollback()
            return {"error": str(e)}, 400
        except Exception as e:
            return {"error": str(e)}, 400


@ns.route("/login")
class UserLoginResource(Resource):
    @ns.doc("login_user")
    @ns.expect(login_model)
    @ns.response(200, "Login successful")
    @ns.response(401, "Invalid credentials")
    def post(self):
        """Login user"""
        db = get_db()
        try:
            # Validate input data using Pydantic
            login_data = UserLogin(**api.payload)

            user = db.query(User).filter_by(email=login_data.email).first()
            if user and check_password_hash(user.password_hash, login_data.password):
                login_user(user)
                return {"message": "Login successful"}, 200
            return {"error": "Invalid email or password"}, 401
        except Exception as e:
            return {"error": str(e)}, 400


@ns.route("/logout")
class UserLogout(Resource):
    @ns.doc("logout_user")
    @ns.response(200, "Logout successful")
    @ns.response(401, "Not authenticated")
    @login_required
    def post(self):
        """Logout user"""
        logout_user()
        return {"message": "Logout successful"}, 200


@ns.route("/profile")
class UserProfile(Resource):
    @ns.doc("get_profile")
    @ns.response(200, "Success")
    @ns.response(401, "Not authenticated")
    @login_required
    def get(self):
        """Get user profile"""
        return UserResponse.from_orm(current_user).dict()
