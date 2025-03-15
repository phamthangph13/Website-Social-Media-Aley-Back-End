from flask import request, jsonify, make_response, render_template, Blueprint, redirect, url_for
from flask_restx import Namespace, Resource, fields
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import jwt
from bson import ObjectId
from pymongo import MongoClient
from config import Config
from utils.email import send_verification_email, send_password_reset_email
import bcrypt

# MongoDB setup
client = MongoClient(Config.MONGO_URI)
db = client.Aley
users = db.users

def register_routes(api):
    # Create namespace
    auth_ns = Namespace('api/auth', description='Authentication operations')
    
    # Models
    user_model = api.model('User', {
        'fullName': fields.String(required=True, description='User full name'),
        'dateOfBirth': fields.Date(required=True, description='User date of birth'),
        'email': fields.String(required=True, description='User email'),
        'password': fields.String(required=True, description='User password')
    })

    login_model = api.model('Login', {
        'email': fields.String(required=True, description='User email'),
        'password': fields.String(required=True, description='User password')
    })

    reset_password_model = api.model('ResetPassword', {
        'email': fields.String(required=True, description='User email')
    })

    new_password_model = api.model('NewPassword', {
        'password': fields.String(required=True, description='New password')
    })

    @auth_ns.route('/register')
    class Register(Resource):
        @auth_ns.expect(user_model)
        def post(self):
            data = request.json
            
            # Validate request data
            if not data:
                return {'message': 'No input data provided'}, 400
            
            # Check if user already exists
            if users.find_one({'email': data['email']}):
                return {'message': 'User already exists'}, 409
            
            try:
                # Generate a secure salt with bcrypt
                salt = bcrypt.gensalt()
                
                # Hash the password with the salt
                hashed_password = bcrypt.hashpw(data['password'].encode('utf-8'), salt)
                
                # Convert to string for storage
                password_hash = hashed_password.decode('utf-8')
                
                # Prepare user data
                new_user = {
                    'fullName': data['fullName'],
                    'dateOfBirth': datetime.strptime(data['dateOfBirth'], '%Y-%m-%d'),
                    'email': data['email'],
                    'password': password_hash,
                    'verified': False,
                    'createdAt': datetime.utcnow(),
                    'roles': ['user']  # Default role for new users
                }
                
                # Insert user into the database
                result = users.insert_one(new_user)
                
                # Generate verification token
                token = jwt.encode({
                    'user_id': str(result.inserted_id),
                    'exp': datetime.utcnow() + timedelta(hours=24)
                }, Config.SECRET_KEY, algorithm='HS256')
                
                # Send verification email
                send_verification_email(data['email'], token, data['fullName'])
                
                return {'message': 'User created successfully. Please verify your email.'}, 201
            
            except Exception as e:
                return {'message': str(e)}, 500

    @auth_ns.route('/login')
    class Login(Resource):
        @auth_ns.expect(login_model)
        def post(self):
            data = request.json
            
            if not data:
                return {'message': 'No input data provided'}, 400
            
            user = users.find_one({'email': data['email']})
            
            if not user:
                return {'message': 'Invalid email or password'}, 401
            
            # Check if the user has verified their email
            if not user.get('verified', False):
                return {'message': 'Please verify your email before logging in'}, 401
            
            # Check password using bcrypt
            if bcrypt.checkpw(data['password'].encode('utf-8'), user['password'].encode('utf-8')):
                # Generate token for client
                token = jwt.encode({
                    'user_id': str(user['_id']),
                    'exp': datetime.utcnow() + timedelta(days=7)
                }, Config.SECRET_KEY, algorithm='HS256')
                
                return {
                    'token': token,
                    'user': {
                        'id': str(user['_id']),
                        'fullName': user['fullName'],
                        'email': user['email'],
                        'roles': user.get('roles', ['user'])
                    }
                }, 200
            
            return {'message': 'Invalid email or password'}, 401

    @auth_ns.route('/verify/<token>')
    class VerifyEmail(Resource):
        def get(self, token):
            try:
                # Decode token
                data = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
                user_id = data['user_id']
                
                # Find user by ID
                user = users.find_one({'_id': ObjectId(user_id)})
                
                if not user:
                    return redirect(url_for('verify_result', status='failed'))
                
                # If user is already verified
                if user.get('verified', False):
                    return redirect(url_for('verify_result', status='already-verified'))
                
                # Update user's verified status
                users.update_one({'_id': ObjectId(user_id)}, {'$set': {'verified': True}})
                
                return redirect(url_for('verify_result', status='success'))
            
            except Exception as e:
                return redirect(url_for('verify_result', status='failed'))

    @auth_ns.route('/verify-result/<status>')
    class VerifyResult(Resource):
        def get(self, status):
            if status == 'success':
                return {'message': 'Email verified successfully'}, 200
            elif status == 'already-verified':
                return {'message': 'Email already verified'}, 200
            else:
                return {'message': 'Email verification failed'}, 400

    @auth_ns.route('/forgot-password')
    class ForgotPassword(Resource):
        @auth_ns.expect(reset_password_model)
        def post(self):
            data = request.json
            
            if not data or not data.get('email'):
                return {'message': 'Email is required'}, 400
            
            # Find user by email
            user = users.find_one({'email': data['email']})
            
            if not user:
                # Don't reveal that the user does not exist
                return {'message': 'If your email is registered, you will receive a password reset link'}, 200
            
            # Generate password reset token
            token = jwt.encode({
                'user_id': str(user['_id']),
                'exp': datetime.utcnow() + timedelta(hours=1)
            }, Config.SECRET_KEY, algorithm='HS256')
            
            # Send password reset email
            send_password_reset_email(user['email'], token, user['fullName'])
            
            return {'message': 'If your email is registered, you will receive a password reset link'}, 200

    @auth_ns.route('/reset-password/<token>')
    class ResetPassword(Resource):
        def get(self, token):
            try:
                # Validate token without changing the password yet
                data = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
                user_id = data['user_id']
                
                # Check if user exists
                user = users.find_one({'_id': ObjectId(user_id)})
                
                if not user:
                    return redirect(url_for('reset_result', status='invalid'))
                
                # Token is valid, but we just render the form without changing password
                # The actual password change happens in POST
                return redirect(f'/reset-password?token={token}')
            
            except jwt.ExpiredSignatureError:
                return redirect(url_for('reset_result', status='expired'))
            except Exception:
                return redirect(url_for('reset_result', status='invalid'))
        
        @auth_ns.expect(new_password_model)
        def post(self, token):
            try:
                # Validate token
                data = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
                user_id = data['user_id']
                
                # Check request data
                request_data = request.json
                if not request_data or not request_data.get('password'):
                    return {'message': 'Password is required'}, 400
                
                # Hash the new password
                salt = bcrypt.gensalt()
                hashed_password = bcrypt.hashpw(request_data['password'].encode('utf-8'), salt)
                password_hash = hashed_password.decode('utf-8')
                
                # Update user's password
                result = users.update_one(
                    {'_id': ObjectId(user_id)},
                    {'$set': {'password': password_hash}}
                )
                
                if result.modified_count == 0:
                    return redirect(url_for('reset_result', status='invalid'))
                
                return redirect(url_for('reset_result', status='success'))
            
            except jwt.ExpiredSignatureError:
                return redirect(url_for('reset_result', status='expired'))
            except Exception as e:
                return redirect(url_for('reset_result', status='invalid'))

    @auth_ns.route('/reset-result/<status>')
    class ResetResult(Resource):
        def get(self, status):
            if status == 'success':
                return {'message': 'Password reset successfully'}, 200
            elif status == 'expired':
                return {'message': 'Password reset link has expired'}, 400
            else:
                return {'message': 'Invalid password reset link'}, 400

    # Add namespace to the API
    api.add_namespace(auth_ns) 