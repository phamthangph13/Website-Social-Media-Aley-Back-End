from flask import Flask, render_template, request, redirect, url_for, jsonify
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
        'http://localhost:5000'
    ]
    
    # Enable CORS with specific configuration
    CORS(app, resources={r"/*": {
        "origins": allowed_origins,  # Specific allowed origins instead of wildcard
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Accept", "X-Requested-With"],
        "supports_credentials": True
    }})
    
    # Add explicit handling for OPTIONS requests (preflight)
    @app.after_request
    def after_request(response):
        origin = request.headers.get('Origin')
        # Only add CORS headers if not already added by Flask-CORS
        if origin and origin in allowed_origins and 'Access-Control-Allow-Origin' not in response.headers:
            response.headers.add('Access-Control-Allow-Origin', origin)
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With, Accept')
            response.headers.add('Access-Control-Allow-Methods', 'GET, PUT, POST, DELETE, OPTIONS')
            response.headers.add('Access-Control-Max-Age', '86400')  # 24 hours
        return response
    
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
    
    # Add additional imports
    from flask import make_response, redirect, url_for
    
    # Add compatibility route for frontend
    @app.route('/api/feed/combined')
    def redirect_feed_combined():
        # Get all query parameters
        args = request.args.to_dict(flat=False)
        query_string = '&'.join([f"{k}={v[0]}" for k, v in args.items()])
        
        # Redirect to the correct endpoint
        target_url = f"/api/posts/feed/combined"
        if query_string:
            target_url += f"?{query_string}"
        
        # Create response with redirect status
        response = jsonify({"redirected": True})
        response.status_code = 307  # Temporary redirect, preserves method
        response.headers['Location'] = target_url
        return response
    
    # Handle OPTIONS for the compatibility route
    @app.route('/api/feed/combined', methods=['OPTIONS'])
    def options_feed_combined():
        resp = app.make_default_options_response()
        origin = request.headers.get('Origin')
        if origin and origin in allowed_origins:
            resp.headers['Access-Control-Allow-Origin'] = origin
        else:
            resp.headers['Access-Control-Allow-Origin'] = allowed_origins[0]  # Default to the first allowed origin
        resp.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Accept'
        return resp
    
    # Route cho trang xác thực email trung gian
    @app.route('/verify')
    def verify_page():
        token = request.args.get('token')
        if not token:
            return redirect(url_for('login_page'))
        return render_template('verify.html', token=token)
    
    # Route cho trang đặt lại mật khẩu trung gian
    @app.route('/reset-password')
    def reset_password_page():
        token = request.args.get('token')
        if not token:
            return redirect(url_for('login_page'))
        return render_template('reset_password.html', token=token)
    
    # Add route for login page (just as a placeholder)
    @app.route('/login')
    def login_page():
        return redirect('/')
    
    # Add route for contact page (just as a placeholder)
    @app.route('/contact')
    def contact_page():
        return redirect('/')
    
    return app

if __name__ == '__main__':
    app = create_app()
    # Get port from environment variable for Render compatibility
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True) 