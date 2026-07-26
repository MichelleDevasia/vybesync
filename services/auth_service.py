import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from db import db
from models.user import User

def hash_password(password):
    return generate_password_hash(password)

def verify_password(password, pw_hash):
    return check_password_hash(pw_hash, password)

def generate_token(user_id):
    payload = {
        'exp': datetime.utcnow() + timedelta(days=7),
        'iat': datetime.utcnow(),
        'sub': str(user_id)
    }
    return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm='HS256')

def decode_token(token):
    try:
        # Decode pyjwt token
        payload = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=['HS256'])
        return int(payload['sub'])
    except jwt.ExpiredSignatureError:
        return 'Signature expired. Please log in again.'
    except jwt.InvalidTokenError:
        return 'Invalid token. Please log in again.'

# Token protection decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # Check authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(" ")[1]
        
        if not token:
            return jsonify({'message': 'Authorization token is missing!'}), 401
        
        user_id = decode_token(token)
        if isinstance(user_id, str):  # error message returned
            return jsonify({'message': user_id}), 401
            
        current_user = User.query.get(user_id)
        if not current_user:
            return jsonify({'message': 'User not found!'}), 401
            
        return f(current_user, *args, **kwargs)
    return decorated
