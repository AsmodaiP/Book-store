from flask_restx import Resource, fields, Namespace
from flask import request, jsonify
from db.database import get_db
from db.models import User
from app.schemas import UserVerify
from datetime import datetime, timedelta
import random
import string
from flask_login import login_required, current_user

ns = Namespace("auth", description="Authentication operations")

# Define models for Swagger documentation
send_code_response_model = ns.model(
    "SendCodeResponse",
    {
        "message": fields.String(description="Response message"),
        "code": fields.String(description="Verification code (only for testing)"),
    },
)

verify_model = ns.model(
    "Verify",
    {
        "code": fields.String(required=True, description="Verification code"),
    },
)

verify_response_model = ns.model(
    "VerifyResponse",
    {
        "message": fields.String(description="Response message"),
    },
)


@ns.route("/send-code")
class SendVerificationCode(Resource):
    @ns.doc("send_verification_code")
    @ns.response(200, "Success", send_code_response_model)
    @ns.response(401, "Not authenticated")
    @login_required
    def post(self):
        """Send verification code to current user's phone number"""
        db = get_db()

        # Get current user's phone number
        phone = current_user.phone

        # Generate verification code
        code = "".join(random.choices(string.digits, k=6))
        expires = datetime.utcnow() + timedelta(minutes=15)  # Code valid for 15 minutes

        # Save code in database
        current_user.verification_code = code
        current_user.verification_code_expires = expires
        db.commit()

        # TODO: Here should be SMS sending with the code
        # For testing, returning code in response
        return {"message": "Verification code sent", "code": code}, 200  # Remove this in production


@ns.route("/verify")
class VerifyPhone(Resource):

    @ns.doc("verify_phone")
    @ns.expect(verify_model)
    @ns.response(200, "Success", verify_response_model)
    @ns.response(400, "Invalid verification code")
    @ns.response(401, "Not authenticated")
    @login_required
    def post(self):
        """Verify current user's phone number with code"""
        db = get_db()
        data = request.get_json()

        if not data or "code" not in data:
            return {"error": "Verification code is required"}, 400

        code = data["code"]

        if not current_user.verification_code or not current_user.verification_code_expires:
            return {"error": "No verification code was sent"}, 400

        if datetime.utcnow() > current_user.verification_code_expires:
            return {"error": "Verification code has expired"}, 400

        if current_user.verification_code != code:
            return {"error": "Invalid verification code"}, 400

        # Verify user
        current_user.is_verified = True
        current_user.verification_code = None
        current_user.verification_code_expires = None
        db.commit()

        return {"message": "Phone number verified successfully"}, 200
