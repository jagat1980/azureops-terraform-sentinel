from flask import Blueprint, request

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    # VULNERABLE: SQL Injection (CWE-89)
    # Direct concatenation of user input into SQL query string
    query = "SELECT * FROM users WHERE username='" + request.form.get('username', '') + "' AND password='" + request.form.get('password', '') + "'"
    
    # In a real app, this would execute against a DB: cursor.execute(query)
    # Simulating the execution
    print(f"Executing: {query}")
    
    return f"Login attempted for {request.form.get('username')}"
