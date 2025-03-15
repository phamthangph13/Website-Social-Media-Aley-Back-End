from flask import Flask, render_template, request, redirect, url_for, jsonify, make_response
from flask_mail import Mail
from flask_restx import Api
from flask_cors import CORS
from config import Config
import os
from datetime import datetime
from bson import ObjectId
import json

# Custom JSON encoder for MongoDB objects
class MongoJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, bytes):
            import base64
            return base64.b64encode(obj).decode('utf-8')
        return super(MongoJSONEncoder, self).default(obj)

# Custom output format for Flask-RESTX
def output_json(data, code, headers=None):
    """Makes a Flask response with a JSON encoded body"""
    from flask import make_response
    
    dumped = json.dumps(data, cls=MongoJSONEncoder)
    
    if headers:
        resp = make_response(dumped, code, headers)
    else:
        resp = make_response(dumped, code)
    
    resp.headers['Content-Type'] = 'application/json'
    return resp

def create_app():
    app = Flask(__name__, template_folder='templates')
    app.config.from_object(Config)
    
    # Define allowed origins
    allowed_origins = [
        'https://phamthangph13.github.io',
        'http://localhost:3000',
        'https://localhost:3000',
        'http://localhost:5000',
        'https://localhost:5000',
        'https://website-social-media-aley-back-end.onrender.com',
        'https://*.website-social-media-aley-back-end.onrender.com'
    ]
    
    # For development, check if we should use a more permissive CORS policy
    dev_mode = os.environ.get("DEV_MODE", "False").lower() == "true"
    if dev_mode:
        # In development mode, allow all origins for easier testing
        cors_origins = "*"
        supports_credentials = False  # Wildcard origin can't use credentials
    else:
        # In production, use the specific allowed origins
        cors_origins = allowed_origins
        supports_credentials = True
    
    # Enable CORS with specific configuration
    CORS(app, resources={r"/*": {
        "origins": cors_origins,
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization", "Accept", "X-Requested-With"],
        "supports_credentials": supports_credentials
    }})
    
    # Initialize Flask-Mail
    app.mail = Mail(app)
    
    # Create API instance with custom output format
    api = Api(
        app, 
        version='1.0',
        title='Authentication API',
        description='API for user authentication and management',
        doc='/'
    )
    
    # Set custom JSON output formatter
    api.representation('application/json')(output_json)
    
    # Import routes (after API is created to avoid circular imports)
    from auth.Authentication import register_routes as register_auth_routes
    register_auth_routes(api)
    
    # Import user fetch routes
    from UserFetch import register_routes as register_user_routes
    register_user_routes(api)
    
    # Import post routes
    from Post import register_routes as register_post_routes
    register_post_routes(api)
    
    # Import new post fetch routes
    from PostFetch import register_routes as register_post_fetch_routes
    register_post_fetch_routes(api)
    
    # Import friend routes
    from Friend import register_routes as register_friend_routes
    register_friend_routes(api)
    
    # Route cho trang xác thực email
    @app.route('/verify')
    def verify_page():
        token = request.args.get('token')
        if not token:
            return redirect('/')
        return render_template('verify.html', token=token)
    
    # Route cho trang đặt lại mật khẩu
    @app.route('/reset-password')
    def reset_password_page():
        token = request.args.get('token')
        if not token:
            return redirect('/')
        return render_template('reset_password.html', token=token)
    
    return app

if __name__ == '__main__':
    app = create_app()
    # Get port from environment variable for Render compatibility
    port = int(os.environ.get("PORT", 5000))
    
    # Check if app is running in production mode
    is_production = os.environ.get("PRODUCTION", "False").lower() == "true"
    
    # Regular run - Render will handle SSL/HTTPS in production
    app.run(host='0.0.0.0', port=port, debug=not is_production) 