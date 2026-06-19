from flask import Flask
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.search import search_bp
from middleware.security_headers import apply_security_headers

app = Flask(__name__)

# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(search_bp)

# Apply Security Headers (Currently Vulnerable)
apply_security_headers(app)

@app.route('/')
def index():
    return "AzureOps Test Harness Vulnerable App is Running."

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
