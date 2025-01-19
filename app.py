from flask import Flask, render_template, Response, request, redirect, session, jsonify
import cv2
import numpy as np
import os
import json
import secrets
import hashlib
from datetime import datetime


app = Flask(__name__, 
            static_url_path='/static')
app.secret_key = secrets.token_hex(16)

# Create config folder and required JSON files
def init_config():
    try:
        # Create config folder
        if not os.path.exists('config'):
            os.makedirs('config')
        
        # Create reference_codes.json
        if not os.path.exists('config/reference_codes.json'):
            initial_codes = {
                "123456789": {
                    "max_uses": 10,
                    "current_uses": 0
                }
            }
            with open('config/reference_codes.json', 'w') as f:
                json.dump(initial_codes, f, indent=4)
        
        # Create browser_sessions.json
        if not os.path.exists('config/browser_sessions.json'):
            with open('config/browser_sessions.json', 'w') as f:
                json.dump({}, f, indent=4)
    except Exception as e:
        print(f"Config creation error: {e}")

# Create config when application starts
init_config()

)


@app.before_request
def check_auth():
    # for debug
    print(f"Accessing endpoint: {request.endpoint}")
    print(f"Session auth status: {session.get('authenticated')}")
    print(f"Browser session status: {check_browser_session()}")

  
    if request.endpoint == 'login' or request.endpoint == 'static':
        return None
    
    
    if request.endpoint is None:
        return redirect('/login')
        
    # authentication control
    if not session.get('authenticated', False):
        # Browser session control
        if not check_browser_session():
            return redirect('/login')
        else:
            
            session['authenticated'] = True

# Initialize the face detection classifier
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
smile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_smile.xml')

def calculate_distance(face_width, known_width=16.0):
    focal_length = 600
    distance = (known_width * focal_length) / face_width
    return round(distance, 1)

def get_browser_fingerprint():
    try:
        user_agent = request.headers.get('User-Agent', '')
        ip = request.remote_addr
        fingerprint = f"{user_agent}{ip}"
        return hashlib.md5(fingerprint.encode()).hexdigest()
    except Exception as e:
        print(f"Fingerprint error: {e}")
        return None

def save_browser_session(code):
    try:
        fingerprint = get_browser_fingerprint()
        if not fingerprint:
            return False
            
        sessions_file = 'config/browser_sessions.json'
        
        
        if os.path.exists(sessions_file):
            with open(sessions_file, 'r') as f:
                sessions = json.load(f)
        else:
            sessions = {}
        
        
        sessions[fingerprint] = {
            "code": code,
            "last_login": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user_agent": request.headers.get('User-Agent', '')
        }
        
       
        with open(sessions_file, 'w') as f:
            json.dump(sessions, f, indent=4)
            
        return True
    except Exception as e:
        print(f"Session error: {e}")
        return False

def check_browser_session():
    try:
        fingerprint = get_browser_fingerprint()
        if not fingerprint:
            return False
            
        if not os.path.exists('config/browser_sessions.json'):
            return False
            
        with open('config/browser_sessions.json', 'r') as f:
            sessions = json.load(f)
            
        if fingerprint in sessions:
            code = sessions[fingerprint]['code']
            
            with open('config/reference_codes.json', 'r') as f:
                codes_data = json.load(f)
                
            if code in codes_data and codes_data[code]['current_uses'] <= codes_data[code]['max_uses']:
                return True
        return False
    except Exception as e:
        print(f"Session control error: {e}")
        return False

@app.route('/')
def index():
    if 'authenticated' in session or check_browser_session():
        session['authenticated'] = True
        return render_template('index.html')
    return redirect('/login')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames_face_only(), 
                    mimetype='multipart/x-mixed-replace; boundary=frame')
                    
@app.route('/face-detection')
def face_detection():
    return render_template('face_detection.html')

@app.route('/body-detection')
def body_detection():
    return render_template('body_detection.html')

@app.route('/eye-detection')
def eye_detection():
    return render_template('eye_detection.html')

@app.route('/eye_video_feed')
def eye_video_feed():
    return Response(generate_frames_eye_detection(), 
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/update_sensitivity')
def update_sensitivity():
    sensitivity = float(request.args.get('value', 1.1))
    # Update the face detection parameters
    return {'status': 'success'}

@app.route('/toggle_distance')
def toggle_distance():
    show_distance = request.args.get('show', 'true') == 'true'
    # Update the distance display setting
    return {'status': 'success'}

@app.route('/emotion_video_feed')
def emotion_video_feed():
    return Response(generate_frames_with_emotions(), 
                    mimetype='multipart/x-mixed-replace; boundary=frame')  

@app.route('/emotion-detection')
def emotion_detection():
    return render_template('emotion_detection.html')



def generate_frames_face_only():
    camera = cv2.VideoCapture(0)
    
    # Camera access check
    if not camera.isOpened():
        print("Could not access camera")
        return
        
    try:
        while True:
            success, frame = camera.read()
            if not success:
                print("Could not get camera frame")
                break
                
        
            frame = cv2.flip(frame, 1)
            
            
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Face
            faces = face_cascade.detectMultiScale(gray, 1.3, 5)
            
            # Face detectid
            for (x, y, w, h) in faces:
                # Face frame
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                
                # Face selected
                roi_gray = gray[y:y+h, x:x+w]
                roi_color = frame[y:y+h, x:x+w]
                
                # Eye 
                eyes = eye_cascade.detectMultiScale(roi_gray)
                for (ex, ey, ew, eh) in eyes:
                    cv2.rectangle(roi_color, (ex, ey), (ex+ew, ey+eh), (255, 0, 0), 2)
                
                # Distance
                distance = calculate_distance(w)
                cv2.putText(frame, f'Distance: {distance}cm', (x, y-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # Frame'i JPEG formatına çevir
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    
    finally:
        camera.release()

def check_reference_code(code):
    try:
        if not os.path.exists('config/reference_codes.json'):
            return False
            
        with open('config/reference_codes.json', 'r') as f:
            codes_data = json.load(f)
            
        if code in codes_data:
            if codes_data[code]['current_uses'] < codes_data[code]['max_uses']:
                codes_data[code]['current_uses'] += 1
                with open('config/reference_codes.json', 'w') as f:
                    json.dump(codes_data, f, indent=4)
                return True
        return False
    except Exception as e:
        print(f"Code error: {e}")
        return False

@app.route('/login', methods=['GET', 'POST'])
def login():
    try:
        if check_browser_session():
            session['authenticated'] = True
            return redirect('/')
            
        if request.method == 'POST':
            reference_code = request.form.get('reference_code')
            if check_reference_code(reference_code):
                session['authenticated'] = True
                save_browser_session(reference_code)
                return redirect('/')
            else:
                error_message = 'Invalid reference code!'
                if os.path.exists('config/reference_codes.json'):
                    with open('config/reference_codes.json', 'r') as f:
                        codes_data = json.load(f)
                    if reference_code in codes_data:
                        if codes_data[reference_code]['current_uses'] >= codes_data[reference_code]['max_uses']:
                            error_message = 'This code has reached its maximum usage limit!'
                
                return render_template('login.html', error=error_message)
                
        return render_template('login.html')
    except Exception as e:
        print(f"Login error: {e}")
        return render_template('login.html', error='System error occurred!')

