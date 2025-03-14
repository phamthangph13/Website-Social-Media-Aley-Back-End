from flask import Flask, render_template, request, redirect, url_for
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
    
    # Enable CORS
    CORS(app)
    
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
    
    # Add additional imports
    from flask import make_response, redirect, url_for
    
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
    app.run(debug=True) 