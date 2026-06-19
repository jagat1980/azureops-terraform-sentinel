from flask import Blueprint, request

search_bp = Blueprint('search', __name__)

@search_bp.route('/api/search', methods=['GET'])
def search():
    # VULNERABLE: Reflected XSS (CWE-79)
    # User input is reflected directly in the response
    query = request.args.get('q', '')
    return f"<p>Results for: {query}</p>"
