from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import firebase_admin
from firebase_admin import credentials, auth
import pyrebase
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this to a strong secret key

# Initialize Firebase Admin SDK
current_dir = os.path.dirname(os.path.abspath(__file__))
cred_path = os.path.join(current_dir, "serviceAccountKey.json")

if not os.path.exists(cred_path):
    print(f"ERROR: File not found at {cred_path}")
    print(f"Current directory contents: {os.listdir(current_dir)}")
    raise FileNotFoundError(f"Service account key not found at {cred_path}")

cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred)

# Firebase configuration for Pyrebase
config = {
    "apiKey": "AIzaSyDSDEeU0Z6WlJbtXtCLgFu7BTj635PjyzM",
    "authDomain": "intrusionsystem-b0338.firebaseapp.com",
    "databaseURL": "https://intrusionsystem-b0338-default-rtdb.firebaseio.com",
    "projectId": "intrusionsystem-b0338",
    "storageBucket": "intrusionsystem-b0338.firebasestorage.app",
    "messagingSenderId": "8171798210",
    "appId": "1:8171798210:web:8f261805bae416d8e1055b"
}

# Initialize Pyrebase
firebase = pyrebase.initialize_app(config)
auth_firebase = firebase.auth()
db = firebase.database()



@app.route('/testdb')
def testdb():
    try:
        result = db.child("/").get()
        return jsonify({
            "success": True,
            "data": result.val(),
            "status": "Database connection working"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "status": "Database connection failed"
        })


@app.route('/')
def home():
    if 'user' in session:
        return redirect(url_for('main'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']
    
    try:
        user = auth_firebase.sign_in_with_email_and_password(email, password)
        session['user'] = email
        return redirect(url_for('main'))
    except Exception as e:
        print(f"Login error: {str(e)}")
        return render_template('login.html', message="Invalid credentials")

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        try:
            # Create user with Firebase Authentication
            user = auth_firebase.create_user_with_email_and_password(email, password)
            
            # Log the user in after signup
            session['user'] = email
            return redirect(url_for('main'))
        except Exception as e:
            print(f"Signup error: {str(e)}")
            return render_template('signup.html', message=str(e))
    
    return render_template('signup.html')

@app.route('/main')
def main():
    if 'user' not in session:
        return redirect(url_for('home'))
    
    try:
        # Get initial data from Firebase
        data = db.child("/").get().val() or {"motion": False, "choice": False}
        return render_template('main.html', 
                            motion=str(data.get('motion', False)).lower(),
                            choice=str(data.get('choice', False)).lower(),
                            user=session['user'])
    except Exception as e:
        print(f"Database error: {str(e)}")
        return render_template('main.html', 
                            motion="false",
                            choice="false",
                            user=session['user'],
                            error=str(e))



@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)