from flask import request, jsonify
from db import db
from models.user import User
from services.auth_service import hash_password, verify_password, generate_token

class AuthController:
    @staticmethod
    def register():
        data = request.get_json() or {}
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')
        
        if not name or not email or not password:
            return jsonify({"message": "Missing required fields (name, email, password)."}), 400
            
        # Check existing user
        if User.query.filter_by(email=email).first():
            return jsonify({"message": "Email is already registered."}), 400
            
        try:
            pw_hash = hash_password(password)
            user = User(
                name=name,
                email=email,
                password_hash=pw_hash
            )
            db.session.add(user)
            db.session.commit()
            
            # Generate session token
            token = generate_token(user.id)
            return jsonify({
                "message": "User registered successfully.",
                "token": token,
                "user": user.to_dict()
            }), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({"message": f"Error registering user: {str(e)}"}), 500

    @staticmethod
    def login():
        data = request.get_json() or {}
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({"message": "Missing email or password."}), 400
            
        user = User.query.filter_by(email=email).first()
        if not user or not verify_password(password, user.password_hash):
            return jsonify({"message": "Invalid email or password."}), 401
            
        token = generate_token(user.id)
        return jsonify({
            "message": "Login successful.",
            "token": token,
            "user": user.to_dict()
        }), 200

    @staticmethod
    def get_profile(current_user):
        return jsonify(current_user.to_dict()), 200
