from flask import request, jsonify
from flask_restx import Namespace, Resource, fields
from bson import ObjectId
from pymongo import MongoClient
from config import Config
import jwt
from functools import wraps
from datetime import datetime

# MongoDB setup
client = MongoClient(Config.MONGO_URI)
db = client.get_database()  # Use the database from MongoDB URI (Aley)
users = db.users

# JWT decorator để bảo vệ các route
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        
        if auth_header:
            # Lấy token từ header "Bearer <token>"
            if ' ' in auth_header:
                token = auth_header.split(' ')[1]
            else:
                token = auth_header
        
        if not token:
            return {'message': 'Token is missing'}, 401
        
        try:
            # Giải mã token
            payload = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=['HS256'])
            current_user_id = payload['user_id']
        except jwt.ExpiredSignatureError:
            return {'message': 'Token has expired'}, 401
        except jwt.InvalidTokenError:
            return {'message': 'Invalid token'}, 401
        
        return f(current_user_id, *args, **kwargs)
    
    return decorated

def register_routes(api):
    # Tạo namespace
    user_ns = Namespace('api/users', description='User operations')
    
    # Models
    user_profile_model = api.model('UserProfile', {
        'fullName': fields.String(description='User full name'),
        'email': fields.String(description='User email'),
        'dateOfBirth': fields.String(description='User date of birth'),
        'avatar': fields.String(description='User avatar URL'),
        'background': fields.String(description='User background image URL'),
        'verifiedTick': fields.Boolean(description='Verified status'),
        'profile-bio': fields.String(description='User bio')
    })
    
    user_update_model = api.model('UserUpdate', {
        'fullName': fields.String(description='User full name', required=False),
        'dateOfBirth': fields.String(description='User date of birth', required=False),
        'avatar': fields.String(description='User avatar URL', required=False),
        'background': fields.String(description='User background image URL', required=False),
        'profile-bio': fields.String(description='User bio', required=False)
    })
    
    # Lấy thông tin người dùng hiện tại
    @user_ns.route('/me')
    class UserMe(Resource):
        @user_ns.doc(security='jwt')
        @user_ns.marshal_with(user_profile_model)
        @token_required
        def get(current_user_id, self):
            user = users.find_one({'_id': ObjectId(current_user_id)})
            
            if not user:
                user_ns.abort(404, 'User not found')
            
            # Xóa thông tin nhạy cảm
            user.pop('password', None)
            user['_id'] = str(user['_id'])
            
            return user
    
    # Lấy thông tin người dùng theo ID
    @user_ns.route('/<user_id>')
    class UserById(Resource):
        @user_ns.marshal_with(user_profile_model)
        def get(self, user_id):
            try:
                user = users.find_one({'_id': ObjectId(user_id)})
                
                if not user:
                    user_ns.abort(404, 'User not found')
                
                # Xóa thông tin nhạy cảm
                user.pop('password', None)
                user['_id'] = str(user['_id'])
                
                return user
            except Exception as e:
                user_ns.abort(400, f'Invalid user ID: {str(e)}')
    
    # Cập nhật thông tin người dùng
    @user_ns.route('/update')
    class UpdateUser(Resource):
        @user_ns.doc(security='jwt')
        @user_ns.expect(user_update_model)
        @token_required
        def put(current_user_id, self):
            data = request.get_json()
            
            # Chỉ cho phép cập nhật các trường cụ thể
            allowed_fields = ['fullName', 'dateOfBirth', 'avatar', 'background']
            update_data = {k: v for k, v in data.items() if k in allowed_fields}
            
            if not update_data:
                return {'message': 'No valid fields to update'}, 400
            
            result = users.update_one(
                {'_id': ObjectId(current_user_id)},
                {'$set': update_data}
            )
            
            if result.modified_count:
                return {'message': 'User updated successfully'}, 200
            else:
                return {'message': 'No changes applied'}, 200
    
    # Lấy danh sách người dùng (phân trang)
    @user_ns.route('/list')
    class UserList(Resource):
        @user_ns.doc(params={
            'page': 'Page number (default: 1)',
            'limit': 'Items per page (default: 10)'
        })
        def get(self):
            page = int(request.args.get('page', 1))
            limit = int(request.args.get('limit', 10))
            skip = (page - 1) * limit
            
            users_data = list(users.find({}, {'password': 0}).skip(skip).limit(limit))
            total = users.count_documents({})
            
            return {
                'users': users_data,
                'total': total,
                'page': page,
                'limit': limit,
                'pages': (total + limit - 1) // limit
            }
    
    # Tìm kiếm người dùng
    @user_ns.route('/search')
    class SearchUsers(Resource):
        @user_ns.doc(params={
            'query': 'Search query',
            'page': 'Page number (default: 1)',
            'limit': 'Items per page (default: 10)'
        })
        def get(self):
            query = request.args.get('query', '')
            page = int(request.args.get('page', 1))
            limit = int(request.args.get('limit', 10))
            skip = (page - 1) * limit
            
            search_filter = {
                '$or': [
                    {'fullName': {'$regex': query, '$options': 'i'}},
                    {'email': {'$regex': query, '$options': 'i'}}
                ]
            }
            
            users_data = list(users.find(search_filter, {'password': 0}).skip(skip).limit(limit))
            total = users.count_documents(search_filter)
            
            return {
                'users': users_data,
                'total': total,
                'page': page,
                'limit': limit,
                'pages': (total + limit - 1) // limit
            }
    
    # Thêm namespace vào API
    api.add_namespace(user_ns) 