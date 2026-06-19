from flask import Blueprint, request

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard', methods=['GET'])
def dashboard():
    # VULNERABLE: Reflected XSS (CWE-79)
    # User input is rendered directly in the HTML response without escaping
    name = request.args.get('name', 'Guest')
    return f"<h1>Welcome {name}</h1><p>Your dashboard is loading...</p>"
