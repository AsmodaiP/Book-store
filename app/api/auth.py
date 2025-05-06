from flask_restx import Resource, fields, Namespace
from flask import request, jsonify
from db.database import get_db
from db.models import User
from app.schemas import UserVerify
from datetime import datetime, timedelta
import random
import string

ns = Namespace("auth", description="Authentication operations")

# Define models for Swagger documentation
verify_model = ns.model(
    "Verify",
    {
        "phone": fields.String(required=True, description="Phone number"),
        "code": fields.String(required=True, description="Verification code"),
    },
)


@ns.route("/send-code")
class SendVerificationCode(Resource):
    @ns.doc("send_verification_code")
    def post(self):
        """Send verification code to phone number"""
        db = get_db()
        phone = request.json.get("phone")

        # Проверяем, существует ли пользователь с таким номером
        user = db.query(User).filter(User.phone == phone).first()
        if not user:
            return jsonify({"error": "User with this phone number not found"}), 404

        # Генерируем код подтверждения
        code = "".join(random.choices(string.digits, k=6))
        expires = datetime.utcnow() + timedelta(minutes=15)  # Код действителен 15 минут

        # Сохраняем код в базе
        user.verification_code = code
        user.verification_code_expires = expires
        db.commit()

        # TODO: Здесь должна быть отправка SMS с кодом
        # Для тестирования возвращаем код в ответе
        return jsonify({"message": "Verification code sent", "code": code}), 200


@ns.route("/verify")
class VerifyPhone(Resource):
    @ns.doc("verify_phone")
    @ns.expect(verify_model)
    def post(self):
        """Verify phone number with code"""
        db = get_db()
        data = UserVerify(**request.json)

        user = db.query(User).filter(User.phone == data.phone).first()
        if not user:
            return jsonify({"error": "User with this phone number not found"}), 404

        if not user.verification_code or not user.verification_code_expires:
            return jsonify({"error": "No verification code was sent"}), 400

        if datetime.utcnow() > user.verification_code_expires:
            return jsonify({"error": "Verification code has expired"}), 400

        if user.verification_code != data.code:
            return jsonify({"error": "Invalid verification code"}), 400

        # Подтверждаем пользователя
        user.is_verified = True
        user.verification_code = None
        user.verification_code_expires = None
        db.commit()

        return jsonify({"message": "Phone number verified successfully"}), 200
