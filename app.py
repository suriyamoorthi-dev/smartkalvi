from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import os
import sqlite3
import json
import re
import uuid
import requests
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import RequestEntityTooLarge
from google.cloud import storage, vision
from werkzeug.security import check_password_hash
from flask import render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash
import sqlite3
import json
from flask import Flask, render_template, request
import together
from flask_mail import Mail, Message
import time
from datetime import datetime, timedelta,date

from supabase import create_client, Client



# === Configurations ===
app = Flask(__name__)
app.secret_key = 'suriya'

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB


# Mail configuration (use your credentials)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Example for Gmail
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'suriyamoorthi474@gmail.com'  # Replace with your email
app.config['MAIL_PASSWORD'] = 'yivp kvso scqm azzo'   # App password recommended

mail = Mail(app)

# === API Keys ===

TOGETHER_API_KEY = "3041964b24957ccdabbb5678a13f8e5bcb895a98c508c1c0469dfb9ad5e0bfce"
TOGETHER_MODEL = "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free" 

DOUBT_SOLVER_API_KEY = "dbfb5267b3c4062b3f8b51a4999dfc27579a11f59bd3354378d14baa3a50e5aa"
DOUBT_SOLVER_MODEL = "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"  # Or your preferred model

# === Google Cloud Config ===
import json
from google.oauth2 import service_account

credentials = None

# Try to load from environment (for Render)
credentials_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")

if credentials_json:
    credentials_dict = json.loads(credentials_json)
    credentials = service_account.Credentials.from_service_account_info(credentials_dict)
# Fallback to local file for your laptop
elif os.path.exists(r"C:\Users\welcome\Downloads\cosmic-abbey-457305-n2-7f39e257180a.json"):
    credentials = service_account.Credentials.from_service_account_file(
        r"C:\Users\welcome\Downloads\cosmic-abbey-457305-n2-7f39e257180a.json"
    )
else:
    raise Exception("Google credentials not found. Check your Render Environment or local file path.")

GCS_BUCKET_NAME = "suriyan"
storage_client = storage.Client(credentials=credentials)
vision_client = vision.ImageAnnotatorClient(credentials=credentials)

# === Load Syllabus ===
with open('syllabus.json', 'r', encoding='utf-8') as f:
    syllabus = json.load(f)

SUPABASE_URL = "https://szfgjywjvfkeudhiobis.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN6ZmdqeXdqdmZrZXVkaGlvYmlzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTA5NDE3NzQsImV4cCI6MjA2NjUxNzc3NH0.OTO8bXjruB8kAfDlDS9CG7evruUbl6ljbswlJzbO8H0"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

QUESTIONS_URL = "https://mmhvljqdyzskxnzkrgql.supabase.co"
QUESTIONS_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1taHZsanFkeXpza3huemtyZ3FsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTEyMTAwOTcsImV4cCI6MjA2Njc4NjA5N30.gtVE8Dg4fdf37xEAAghgrMjyIpOZOTnIuOFn0qk59uM"
supabase_questions = create_client(QUESTIONS_URL, QUESTIONS_KEY)


# === Utils ===
def parse_exam_output(text):
    lines = text.split("\n")
    qna_2m, qna_5m = [], []
    current = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        lower_line = line.lower()

        # Detect the section
        if "2-mark questions" in lower_line or "2 mark questions" in lower_line:
            current = qna_2m
            continue
        elif "5-mark questions" in lower_line or "5 mark questions" in lower_line:
            current = qna_5m
            continue

        # Extract questions like "Q1: What is...?"
        if line.startswith("Q") and ":" in line and current is not None:
            question = line.split(":", 1)[1].strip()
            if question:
                current.append({"question": question})

    return qna_2m, qna_5m

TOGETHER_API_KEY = "3041964b24957ccdabbb5678a13f8e5bcb895a98c508c1c0469dfb9ad5e0bfce"
TOGETHER_MODEL = "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"
import random
import uuid

def generate_exam_qna(class_level, subject, topic, exam_mode="topic", board="state", force=False):
    import random, json, uuid, requests

    mode_settings = {"topic": (5, 3), "unit": (8, 5), "full": (12, 8)}
    total_2m, total_5m = mode_settings.get(exam_mode, (4, 2))

    db_2m, db_5m = [], []

    try:
        if not force:
            response = supabase_questions.table("questions").select("qna_2m, qna_5m").match({
                "class_level": class_level,
                "subject": subject,
                "topic": topic,
                "exam_mode": exam_mode,
                "board": board
            }).limit(1).execute()

            if response.data:
                try:
                    db_2m = json.loads(response.data[0].get('qna_2m', '[]'))
                    db_5m = json.loads(response.data[0].get('qna_5m', '[]'))
                    print(f"✅ Fetched {len(db_2m)} two-mark and {len(db_5m)} five-mark from Supabase ({board.upper()}).")
                except:
                    print("⚠️ Corrupted cached record, regenerating...")
    except Exception as e:
        print(f"⚠️ Supabase fetch error: {e}")

    # Calculate how many more needed from AI
    remaining_2m = max(total_2m - len(db_2m), 0)
    remaining_5m = max(total_5m - len(db_5m), 0)

    ai_2m, ai_5m = [], []

    if remaining_2m > 0 or remaining_5m > 0:
        print(f"⚡ Generating {remaining_2m} two-mark and {remaining_5m} five-mark questions from AI ({board.upper()})...")

        syllabus_text = "Tamil Nadu Samacheer Kalvi" if board == "state" else "CBSE"

        prompt = f"""
You are an expert {syllabus_text} question setter.

Generate {remaining_2m} two-mark questions and {remaining_5m} five-mark questions ONLY — do not provide answers.

Exam Mode: {exam_mode.title()} Wise
Class: {class_level}
Subject: {subject}
Topic/Unit/Chapter: {topic}

Strictly follow {syllabus_text} syllabus. Questions should be textbook-style, simple, real-time relatable, and suitable for practice and exams.

Format:
2-Mark Questions:
Q1: ...
Q2: ...
...
5-Mark Questions:
Q1: ...
Q2: ...
...
"""

        try:
            response = requests.post(
                "https://api.together.xyz/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {TOGETHER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": TOGETHER_MODEL,
                    "messages": [
                        {"role": "system", "content": "You are an expert in Indian school exam patterns."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.4
                },
                timeout=30
            )
            response.raise_for_status()
            content = response.json()['choices'][0]['message']['content']
            print("📝 Raw AI Output:\n", content)

            # Parse Questions
            lines = content.splitlines()
            is_2m, is_5m = False, False

            for line in lines:
                line = line.strip()
                if line.lower().startswith("2-mark questions"):
                    is_2m, is_5m = True, False
                elif line.lower().startswith("5-mark questions"):
                    is_2m, is_5m = False, True
                elif line.startswith("Q") and ":" in line:
                    question_text = line.split(":", 1)[1].strip()
                    if is_2m and len(ai_2m) < remaining_2m:
                        ai_2m.append({"question": question_text})
                    elif is_5m and len(ai_5m) < remaining_5m:
                        ai_5m.append({"question": question_text})

        except Exception as e:
            print(f"❌ AI API Error: {e}")
            print("⚠️ Continuing with available DB questions...")

    final_2m = db_2m + ai_2m
    final_5m = db_5m + ai_5m
    random.shuffle(final_2m)
    random.shuffle(final_5m)

    try:
        # Save to Supabase only if nothing existed initially and AI generated something
        if not db_2m and not db_5m and (final_2m or final_5m):
            supabase_questions.table("questions").insert({
                "id": str(uuid.uuid4()),
                "class_level": class_level,
                "subject": subject,
                "topic": topic,
                "exam_mode": exam_mode,
                "board": board,
                "qna_2m": json.dumps(final_2m),
                "qna_5m": json.dumps(final_5m)
            }).execute()
            print(f"✅ New mixed question set saved to Supabase ({board.upper()}).")
    except Exception as e:
        print(f"⚠️ Supabase save error: {e}")

    print(f"🎯 Final 2-mark: {len(final_2m)}, Final 5-mark: {len(final_5m)}")
    return final_2m, final_5m

# === Routes ===
@app.route('/')
def homepage():
    return render_template('landing.html')

@app.route('/become-a-tutor')
def become_a_tutor():
    """
    Renders the informational page for prospective tutors,
    explaining benefits and earning potential.
    """
    return render_template('tutor_info.html')


import json

with open('syllabus.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

formatted_syllabus = []

for item in data:
    topics_raw = item.get('topics', [])

    # Convert plain topic list to list of dicts with name key
    topics = [{"name": topic} for topic in topics_raw] if isinstance(topics_raw, list) else []

    formatted_syllabus.append({
        "class_level": item.get("class_level"),  # Use class_level for DB
        "subject": item.get("subject"),
        "topics": topics
    })

with open('syllabus_fixed.json', 'w', encoding='utf-8') as f:
    json.dump(formatted_syllabus, f, indent=2, ensure_ascii=False)

print("✅ syllabus_fixed.json generated with correct structure")

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/help')
def help_page():
    return render_template('help.html')

@app.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy.html')

@app.route('/events')
def events():
    return render_template('events.html')

@app.route('/pricing')
def pricing():
    return render_template('pricing.html')


@app.route('/dashboard')
def dashboard():
    if 'student_id' not in session:
        return redirect(url_for('student_login'))

    syllabus_res = supabase.table("syllabus").select("*").execute()
    teachers_res = supabase.table("teachers").select("*").eq("verified", True).execute()

    syllabus_data = syllabus_res.data if syllabus_res.data else []

    formatted_syllabus = []
    for item in syllabus_data:
        topics = item.get("topics")

        # Parse JSON string if needed
        if isinstance(topics, str):
            try:
                topics = json.loads(topics)
            except:
                topics = []

        formatted_syllabus.append({
            "class_level": item.get("class_level"),  # Match DB field
            "subject": item.get("subject"),
            "topics": topics
        })

    return render_template('index.html', syllabus=formatted_syllabus, teachers=teachers_res.data)

@app.route('/exam', methods=['POST'])
def exam():
    class_level = request.form['class']
    subject = request.form['subject']
    topic = request.form['topic']
    exam_mode = request.form.get('exam_mode', 'topic')
    board = request.form.get('board', 'state')  # Default 'state' if not provided

    qna_2m, qna_5m = [], []

    try:
        response = supabase_questions.table("questions").select("qna_2m, qna_5m").match({
            "class_level": class_level,
            "subject": subject,
            "topic": topic,
            "exam_mode": exam_mode,
            "board": board
        }).limit(1).execute()

        if response.data:
            try:
                qna_2m = json.loads(response.data[0].get('qna_2m', '[]'))
                qna_5m = json.loads(response.data[0].get('qna_5m', '[]'))
                print(f"✅ Using cached questions from Supabase ({board.upper()}).")
            except:
                qna_2m, qna_5m = [], []
    except Exception as e:
        print(f"⚠️ Supabase fetch error: {e}")

    if not qna_2m and not qna_5m:
        print(f"⚡ No cached questions for {board.upper()}. Generating new...")
        qna_2m, qna_5m = generate_exam_qna(class_level, subject, topic, exam_mode, board=board, force=True)

    total_marks = 25 if exam_mode == "topic" else 40 if exam_mode == "unit" else 100

    correct_answer_text = json.dumps({"2m": qna_2m, "5m": qna_5m}, ensure_ascii=False)

    return render_template(
        'exam.html',
        class_level=class_level,
        subject=subject,
        topic=topic,
        exam_mode=exam_mode,
        board=board,
        qna_2m=qna_2m,
        qna_5m=qna_5m,
        total_marks=total_marks,
        correct_answer_text=correct_answer_text
    )

@app.route('/upload_exam', methods=['POST'])
def upload_exam():
    if 'file' not in request.files or 'correct_answer' not in request.form:
        return jsonify({"error": "Missing required parameters."}), 400

    pdf_file = request.files['file']
    correct_answer = request.form['correct_answer']
    student_id = str(uuid.uuid4())

    pdf_filename = f"uploads/{student_id}_answer.pdf"
    ocr_output_prefix = f"ocr_results/{student_id}/"

    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    pdf_blob = bucket.blob(pdf_filename)
    pdf_blob.upload_from_file(pdf_file)

    gcs_pdf_path = f"gs://{GCS_BUCKET_NAME}/{pdf_filename}"
    gcs_output_path = f"gs://{GCS_BUCKET_NAME}/{ocr_output_prefix}"

    feature = vision.Feature(type_=vision.Feature.Type.DOCUMENT_TEXT_DETECTION)
    gcs_source = vision.GcsSource(uri=gcs_pdf_path)
    input_config = vision.InputConfig(gcs_source=gcs_source, mime_type="application/pdf")
    gcs_destination = vision.GcsDestination(uri=gcs_output_path)
    output_config = vision.OutputConfig(gcs_destination=gcs_destination)

    async_request = vision.AsyncAnnotateFileRequest(
        features=[feature],
        input_config=input_config,
        output_config=output_config
    )

    operation = vision_client.async_batch_annotate_files(requests=[async_request])
    operation.result(timeout=60)

    blobs = list(storage_client.list_blobs(GCS_BUCKET_NAME, prefix=ocr_output_prefix))
    extracted_text = ""

    import json
    import tempfile
    import os

    for ocr_blob in blobs:
        if ocr_blob.name.endswith(".json"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as temp_file:
                temp_path = temp_file.name

            ocr_blob.download_to_filename(temp_path)

            with open(temp_path, "r", encoding="utf-8") as f:
                ocr_data = json.load(f)

            os.remove(temp_path)

            for response in ocr_data.get('responses', []):
                extracted_text += response.get('fullTextAnnotation', {}).get('text', '')

    # We still use AI evaluation, but we only care about final score
    _, score = evaluate_answer_with_ai(correct_answer, extracted_text)

    # Cleanup
    pdf_blob.delete()
    for ocr_blob in blobs:
        ocr_blob.delete()

    total_marks = 25

    return render_template(
        'result.html',
        score=score,
        total_marks=total_marks
    )

import re
import requests

def evaluate_answer_with_ai(correct_answer, student_answer, exam_mode="topic", board="state"):
    total_marks = 25 if exam_mode == "topic" else 40 if exam_mode == "unit" else 100
    board_text = "Tamil Nadu Samacheer Kalvi" if board == "state" else "CBSE"

    prompt = f"""
You are an experienced {board_text} school teacher evaluating answers.

Please evaluate the student's answer strictly based on textbook standards.

Correct Answer:
{correct_answer}

Student's Answer:
{student_answer}

Provide only the final score in this format:

Score: X/{total_marks}
"""

    try:
        response = requests.post(  
            "https://api.together.xyz/v1/chat/completions",
            headers={"Authorization": f"Bearer {TOGETHER_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": TOGETHER_MODEL,
                "messages": [
                    {"role": "system", "content": "You are an experienced Indian school teacher evaluating student answers."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.4
            },
            timeout=30
        )
        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content']
        print("📝 AI Raw Evaluation:\n", content)

        score_match = re.search(r'Score:\s*(\d+)\s*/\s*(\d+)', content)
        score = int(score_match.group(1)) if score_match else 0
        return content, score

    except Exception as e:
        print(f"❌ AI Evaluation Error: {e}")
        return "AI Evaluation Failed", 0


@app.errorhandler(RequestEntityTooLarge)
def handle_large_file(e):
    return "❌ File too large.", 413

# === Super Admin Routes - Clean and Organized ===

@app.route('/school_admin/dashboard')
def school_admin_dashboard():
    if 'school_admin_id' not in session:
        return redirect(url_for('school_admin_login'))

    school_id = session['school_id']  # Assuming you store this during login

    # Fetch school details
    response = supabase.table('schools').select("*").eq('id', school_id).single().execute()
    school = response.data

    # Calculate total fee based on student counts
    total_fee = calculate_total_fee(school)

    return render_template('school_admin_dashboard.html', school=school, total_fee=total_fee)

import datetime  # Make sure this is present at the top of your file
@app.route('/school_admin/pay_now')
def school_admin_pay_now():
    if 'school_admin_id' not in session:
        return redirect(url_for('school_admin_login'))

    return render_template('school_pay_now.html')  # This should only have GForm button now

from werkzeug.security import check_password_hash

@app.route('/school_admin/login', methods=['GET', 'POST'])
def school_admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Safe query using limit(1)
        response = supabase.table('schools').select("id, admin_password").eq('admin_username', username).limit(1).execute()
        school_data = response.data

        if school_data:
            school = school_data[0]
            if check_password_hash(school['admin_password'], password):
                session['school_admin_id'] = school['id']
                session['school_id'] = school['id']
                return redirect(url_for('school_admin_dashboard'))

        return render_template('school_admin_login.html', error="❌ Invalid username or password")

    return render_template('school_admin_login.html')
@app.route('/school_admin/performance')
def school_admin_performance():
    if 'school_admin_id' not in session:
        return redirect(url_for('school_admin_login'))

    school_id = session['school_admin_id']
    selected_class = request.args.get('class', '')

    all_classes = []
    performance_data = []
    weak_students = []

    try:
        # Fetch available classes from answers (1st project)
        response = supabase.table('answers').select('class_level').eq('school_id', school_id).execute()
        if response.data:
            all_classes = list(set([row['class_level'] for row in response.data if 'class_level' in row]))
    except Exception as e:
        print(f"Error fetching classes: {e}")

    try:
        # Fetch answers for performance (1st project)
        query = supabase.table('answers').select('*').eq('school_id', school_id)
        if selected_class:
            query = query.eq('class_level', selected_class)

        data = query.execute().data

        for row in data:
            student_id = row.get('student_id', 'N/A')
            class_level = row.get('class_level', 'N/A')
            score = row.get('score', 0)
            total_marks = row.get('total_marks', 1)

            # Fetch student name from 1st project
            student_name = "N/A"
            try:
                student_response = supabase.table('students').select('name').eq('id', student_id).single().execute()
                if student_response.data and 'name' in student_response.data:
                    student_name = student_response.data['name']
            except Exception as e:
                print(f"Error fetching student name for ID {student_id}: {e}")

            percentage = round((score / total_marks) * 100, 2) if total_marks else 0

            performance_data.append((
                student_name,
                class_level,
                1,  # Exams attempted
                score,
                percentage
            ))

            if percentage < 50:
                weak_students.append((student_name, class_level, percentage))

    except Exception as e:
        print(f"Error fetching performance: {e}")

    return render_template("school_admin_performance.html",
                           performance=performance_data,
                           all_classes=all_classes,
                           selected_class=selected_class,
                           weak_students=weak_students)

from werkzeug.security import generate_password_hash, check_password_hash
from flask import flash, session, redirect, url_for, render_template, request

@app.route('/school_admin/students', methods=['GET', 'POST'])
def manage_students():
    if 'school_admin_id' not in session:
        return redirect(url_for('school_admin_login'))

    school_id = session['school_admin_id']

    if request.method == 'POST':
        name = request.form['name']
        class_level = request.form['class_level']
        username = request.form['username']
        password = generate_password_hash(request.form['password'])

        # Use .execute() safely and check if any row exists
        existing = supabase.table('students').select('id').eq('username', username).execute()

        if existing.data and len(existing.data) > 0:
            flash("⚠️ Username already exists.", "error")
        else:
            supabase.table('students').insert({
                "name": name,
                "class_level": class_level,
                "username": username,
                "password": password,
                "school_id": school_id
            }).execute()
            flash("✅ Student added successfully.", "success")

        return redirect('/school_admin/students')

    # Fetch student list safely
    response = supabase.table('students').select('id, name, class_level, username').eq('school_id', school_id).execute()
    students = response.data if response.data else []

    return render_template('manage_students.html', students=students)

# === Super Admin Login ===
@app.route('/superadmin/login', methods=['GET', 'POST'])
def superadmin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == 'admin' and password == 'admin123':  # You can change this
            session['superadmin_logged_in'] = True
            return redirect(url_for('superadmin_dashboard'))
        else:
            return "❌ Invalid credentials", 401

    return render_template('superadmin_login.html')

# === Super Admin Dashboard ===
@app.route('/superadmin/dashboard')
def superadmin_dashboard():
    if not session.get('superadmin_logged_in'):
        return redirect(url_for('superadmin_login'))

    try:
        response = supabase.table('schools').select("*").execute()
        schools = response.data  # List of dictionaries

        # Add total_fee to each school
        for school in schools:
            school['total_fee'] = calculate_total_fee(school)

    except Exception as e:
        print("Error fetching schools:", e)
        schools = []

    return render_template("superadmin_dashboard.html", schools=schools)

def update_student_counts(school_id):
    for cls in range(6, 13):
        response = supabase.table('students').select('id', count='exact')\
            .eq('school_id', school_id).eq('class', cls).execute()
        
        count = response.count if response.count is not None else 0
        
        supabase.table('schools').update({f'students_{cls}_count': count})\
            .eq('id', school_id).execute()


def calculate_total_fee(school):
    total_fee = 0
    board = school.get('board', 'TN')  # Default TN if not specified

    # Slabs for TN Board
    tn_slab_6_8 = {'upto_30': 300, 'upto_40': 500, 'above_40': 700}
    tn_slab_9_10 = {'upto_30': 500, 'upto_40': 800, 'above_40': 1000}
    tn_slab_11_12 = {'upto_30': 700, 'upto_40': 1100, 'above_40': 1500}

    # Slabs for CBSE Board (example, you can tweak)
    cbse_slab_6_8 = {'upto_30': 500, 'upto_40': 700, 'above_40': 900}
    cbse_slab_9_10 = {'upto_30': 700, 'upto_40': 1000, 'above_40': 1300}
    cbse_slab_11_12 = {'upto_30': 1000, 'upto_40': 1500, 'above_40': 2000}

    for cls in range(6, 13):
        count = school.get(f'students_{cls}_count', 0)

        if 6 <= cls <= 8:
            slab = tn_slab_6_8 if board == 'TN' else cbse_slab_6_8
        elif 9 <= cls <= 10:
            slab = tn_slab_9_10 if board == 'TN' else cbse_slab_9_10
        elif 11 <= cls <= 12:
            slab = tn_slab_11_12 if board == 'TN' else cbse_slab_11_12

        if count > 0:
            if count <= 30:
                total_fee += slab['upto_30']
            elif count <= 40:
                total_fee += slab['upto_40']
            else:
                total_fee += slab['above_40']

    return total_fee

@app.route('/superadmin/payments')
def superadmin_payments():
    response = supabase.table('schools').select('*').order('payment_status', desc=False).execute()
    schools = response.data
    return render_template('superadmin_payments.html', schools=schools)

@app.route('/superadmin/mark_paid/<school_id>')
def mark_payment_received(school_id):
    today = datetime.date.today()
    next_due_date = (today + datetime.timedelta(days=30)).strftime('%Y-%m-%d')

    supabase.table('schools').update({
        'payment_status': 'active',
        'next_due_date': next_due_date,
        'payment_marked_on': today.strftime('%Y-%m-%d')  # optional
    }).eq('id', school_id).execute()

    return redirect(url_for('superadmin_payments'))


@app.route('/superadmin/get_admin_password/<int:school_id>')
def get_admin_password(school_id):
    if not session.get('superadmin_logged_in'):
        return "Unauthorized", 403

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT admin_password FROM schools WHERE id=?", (school_id,))
    row = c.fetchone()
    conn.close()

    if row:
        return row[0]  # This is hashed password unless you store plain
    return "Not found", 404

# === Add New School ===
@app.route('/superadmin/add_school', methods=['GET', 'POST'])
def superadmin_add_school():
    if not session.get('superadmin_logged_in'):
        return redirect(url_for('superadmin_login'))

    if request.method == 'POST':
        name = request.form['school_name']
        username = request.form['admin_username']
        password = generate_password_hash(request.form['admin_password'])

        try:
            supabase.table('schools').insert({
                "name": name,
                "admin_username": username,
                "admin_password": password,
                "payment_status": "inactive",  # Default values
                "next_due_date": None
            }).execute()

            flash("✅ School added successfully", "success")
        except Exception as e:
            print(e)
            flash("❌ Failed to add school", "error")

        return redirect(url_for('superadmin_dashboard'))

    return render_template("superadmin_add_school.html")

from werkzeug.security import generate_password_hash

@app.route('/superadmin/reset_admin_password/<int:school_id>', methods=['GET', 'POST'])
def superadmin_reset_admin_password(school_id):
    if not session.get('superadmin_logged_in'):
        return redirect(url_for('superadmin_login'))

    if request.method == 'POST':
        new_password = request.form['new_password']
        hashed_password = generate_password_hash(new_password)

        try:
            supabase.table('schools').update({"admin_password": hashed_password}).eq('id', school_id).execute()
            flash("✅ Password updated successfully", "success")
        except Exception as e:
            print(e)
            flash("❌ Failed to update password", "error")

        return redirect(url_for('superadmin_dashboard'))

    return render_template("superadmin_reset_admin_password.html", school_id=school_id)



@app.route('/superadmin/delete_school/<int:school_id>')
def superadmin_delete_school(school_id):
    if not session.get('superadmin_logged_in'):
        return redirect(url_for('superadmin_login'))

    try:
        supabase.table('schools').delete().eq('id', school_id).execute()
        flash("✅ School deleted", "success")
    except Exception as e:
        print(e)
        flash("❌ Failed to delete school", "error")

    return redirect(url_for('superadmin_dashboard'))

# === School Performance Summary ===
@app.route('/superadmin/school_performance')
def superadmin_school_performance():
    if not session.get('superadmin_logged_in'):
        return redirect(url_for('superadmin_login'))

    # Ideally, use Supabase Postgres function for this aggregation
    response = supabase.rpc('school_performance_summary').execute()

    schools = []
    if response.data:
        for row in response.data:
            schools.append((
                row['school_name'],
                row['school_id'],
                row['total_exams'],
                row['total_score'],
                round(row['avg_score'] or 0, 2)
            ))

    return render_template("superadmin_school_performance.html", schools=schools)

# === Regenerate Questions (AI or Manual) ===
@app.route('/superadmin/regenerate', methods=['GET', 'POST'])
def superadmin_regenerate():
    if not session.get('superadmin_logged_in'):
        return redirect(url_for('superadmin_login'))

    qna_2m = "[]"
    qna_5m = "[]"
    class_level = ""
    subject = ""
    topic = ""
    exam_mode = "topic"
    count_2m = 0
    count_5m = 0

    if request.method == "POST":
        class_level = request.form.get("class", "")
        subject = request.form.get("subject", "")
        topic = request.form.get("topic", "")
        exam_mode = request.form.get("exam_mode", "topic")

        try:
            qna_2m = request.form.get("qna_2m", "[]")
            qna_5m = request.form.get("qna_5m", "[]")
            two_mark_list = json.loads(qna_2m)
            five_mark_list = json.loads(qna_5m)
            count_2m = len(two_mark_list)
            count_5m = len(five_mark_list)
        except:
            flash("⚠️ Invalid JSON format", "error")
            return redirect(url_for("superadmin_regenerate"))

        try:
            # Delete existing question set
            supabase_questions.table("questions").delete().match({
                "class_level": class_level,
                "subject": subject,
                "topic": topic,
                "exam_mode": exam_mode
            }).execute()

            # Insert new question set
            supabase_questions.table("questions").insert({
                "id": str(uuid.uuid4()),
                "class_level": class_level,
                "subject": subject,
                "topic": topic,
                "exam_mode": exam_mode,
                "qna_2m": qna_2m,
                "qna_5m": qna_5m
            }).execute()

            flash(f"✅ Manual questions saved. {count_2m} two-mark and {count_5m} five-mark questions stored.", "success")

        except Exception as e:
            flash(f"⚠️ Supabase error: {str(e)}", "error")
            return redirect(url_for("superadmin_regenerate"))

    return render_template(
        "superadmin_regenerate.html",
        qna_2m=qna_2m,
        qna_5m=qna_5m,
        class_level=class_level,
        subject=subject,
        topic=topic,
        exam_mode=exam_mode,
        count_2m=count_2m,
        count_5m=count_5m
    )
@app.route('/superadmin/manage_questions')
def superadmin_manage_questions():
    if not session.get('superadmin_logged_in'):
        return redirect(url_for('superadmin_login'))

    response = supabase_questions.table('questions').select('*').order('class_level').execute()
    questions = response.data if response.data else []

    return render_template("superadmin_manage_questions.html", questions=questions)

@app.route('/superadmin/delete_question/<string:question_id>')
def superadmin_delete_question(question_id):
    if not session.get('superadmin_logged_in'):
        return redirect(url_for('superadmin_login'))

    supabase_questions.table("questions").delete().eq("id", question_id).execute()

    flash("✅ Question deleted successfully", "success")
    return redirect(url_for('superadmin_manage_questions'))
@app.route('/student_login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        response = supabase.table('students').select('*').eq('username', username).limit(1).execute()

        if not response.data:
            return "❌ Invalid username or password", 401

        student = response.data[0]

        # School check
        school_response = supabase.table('schools').select('*').eq('id', student['school_id']).limit(1).execute()
        if not school_response.data:
            return "❌ School info not found", 500

        school = school_response.data[0]
        today = datetime.date.today()

        if school.get('payment_status') != 'active':
            return "❌ Access Denied. Your school has not paid."

        if school.get('next_due_date') and today > datetime.datetime.strptime(school['next_due_date'], '%Y-%m-%d').date():
            return "❌ School subscription expired.", 403

        # Password match
        if check_password_hash(student['password'], password):
            session['student_id'] = student['id']
            session['student_name'] = student['name']
            session['student_class'] = student['class_level']
            session['school_name'] = school['name']
            return redirect(url_for('dashboard'))

        return "❌ Invalid credentials", 401

    return render_template('student_login.html')


# Your Together AI details
DOUBT_SOLVER_API_KEY = "dbfb5267b3c4062b3f8b51a4999dfc27579a11f59bd3354378d14baa3a50e5aa"
DOUBT_SOLVER_MODEL = "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"

# Initialize Together AI
together.api_key = DOUBT_SOLVER_API_KEY



@app.route("/doubt_solver", methods=["GET", "POST"])
def doubt_solver():
    answer = None
    question = ""

    if request.method == "POST":
        question = request.form.get("question", "").strip()
        
        if question:
            prompt = (
    f"You are a friendly teacher helping an Indian school student (CBSE or Tamil Nadu board, class 6–12). "
    f"Explain the answer in simple English only. Don't reply in Hindi. "
    f"Use Tamil-English mix only if needed, but no Hindi. "
    f"Break it step-by-step. Use real-life examples like school, autos, mobile recharge, etc. "
    f"If it's math or science, give easy tips or memory tricks.\n\n"
    f"📘 Question: {question}\n\n"
    f"👨‍🏫 Answer (in simple English):"
)


            
            headers = {
                "Authorization": f"Bearer {DOUBT_SOLVER_API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": DOUBT_SOLVER_MODEL,
                "prompt": prompt,
                "max_tokens": 150,
                "temperature": 0.7
            }
            
            try:
                response = requests.post(
                    "https://api.together.xyz/v1/completions",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    answer = data.get("choices", [{}])[0].get("text", "").strip()
                else:
                    answer = "⚠️ Sorry, AI service is temporarily unavailable."
            except Exception as e:
                answer = f"⚠️ Error: {str(e)}"

    return render_template("doubt_solver.html", question=question, answer=answer)


from supabase import create_client, Client

SUPABASE_URL = "https://szfgjywjvfkeudhiobis.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN6ZmdqeXdqdmZrZXVkaGlvYmlzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTA5NDE3NzQsImV4cCI6MjA2NjUxNzc3NH0.OTO8bXjruB8kAfDlDS9CG7evruUbl6ljbswlJzbO8H0"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.route('/teacher/login', methods=['GET', 'POST'])
def teacher_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # ✅ Safe fetch with .limit(1)
        res = supabase.table("teachers").select("*")\
            .eq("username", username)\
            .eq("password", password)\
            .eq("verified", True)\
            .limit(1)\
            .execute()
        teacher_data = res.data

        if teacher_data:
            teacher = teacher_data[0]
            session['teacher_logged_in'] = True
            session['teacher_id'] = teacher['id']
            return redirect(url_for('teacher_dashboard'))
        else:
            return render_template('teacher_login.html', error="Invalid credentials or not approved yet.")

    return render_template('teacher_login.html')

@app.route('/find_tutors')
def find_tutors():
    subject_filter = request.args.get('subject', '')  # Get subject from query params
    
    query = supabase.table("teachers").select("*").eq("verified", True)
    
    if subject_filter:
        query = query.eq("subject", subject_filter)

    # Sort by rating descending (highest rated teachers first)
    query = query.order("rating", desc=True)

    teachers_res = query.execute()
    teachers = teachers_res.data if teachers_res.data else []

    # Attach monthly fee for each teacher
    for teacher in teachers:
        plan_res = supabase.table("teacher_monthly_plans").select("*").eq("teacher_id", teacher["id"]).execute()
        plans = plan_res.data if plans else []
        teacher["monthly_fee"] = plans[0]["price"] if plans else None

    return render_template("find_tutors.html", teachers=teachers, selected_subject=subject_filter)

@app.route('/teacher/dashboard')
def teacher_dashboard():
    if 'teacher_id' not in session:
        return redirect(url_for('teacher_login'))

    teacher_id = session['teacher_id']

    # ✅ Safe fetch teacher
    teacher_res = supabase.table("teachers").select("*").eq("id", teacher_id).limit(1).execute()
    teacher_data = teacher_res.data

    if not teacher_data:
        session.pop('teacher_id', None)
        return redirect(url_for('teacher_login'))

    teacher = teacher_data[0]

    # Fetch slots
    slots_res = supabase.table("available_slots").select("*").eq("teacher_id", teacher_id).execute()
    slots = slots_res.data

    # Fetch materials
    materials_res = supabase.table("teacher_materials").select("*").eq("teacher_id", teacher_id).execute()
    materials = materials_res.data

    # Fetch monthly plan
    plan_res = supabase.table("teacher_monthly_plans").select("*").eq("teacher_id", teacher_id).execute()
    plans = plan_res.data if plan_res.data else []
    price = plans[0]['price'] if plans else 0

    # Commission split based on rating
    rating = teacher['rating'] or 0
    if rating >= 4.5:
        teacher_percentage = 70
    elif rating >= 4.0:
        teacher_percentage = 60
    else:
        teacher_percentage = 50

    your_percentage = 100 - teacher_percentage

    teacher_earning = round((price * teacher_percentage) / 100, 2)
    your_earning = round((price * your_percentage) / 100, 2)

    # Fetch total paid students from subscriptions
    paid_res = supabase.table("subscriptions").select("id").eq("teacher_id", teacher_id).eq("status", "paid").execute()
    total_students = len(paid_res.data) if paid_res.data else 0

    total_monthly_earning = round(teacher_earning * total_students, 2)

    return render_template('teacher_dashboard.html',
                           teacher=teacher,
                           slots=slots,
                           materials=materials,
                           price=price,
                           teacher_earning=teacher_earning,
                           your_earning=your_earning,
                           teacher_percentage=teacher_percentage,
                           your_percentage=your_percentage,
                           total_students=total_students,
                           total_monthly_earning=total_monthly_earning)

@app.route('/teachers')
def list_teachers():
    category = request.args.get('category')

    # Step 1: Fetch verified teachers (with or without category)
    if category:
        response = supabase.table("teachers").select("id, name, subject, image_url, bio, rating, verified, category")\
            .eq("category", category)\
            .eq("verified", True)\
            .execute()
    else:
        response = supabase.table("teachers").select("id, name, subject, image_url, bio, rating, verified, category")\
            .eq("verified", True)\
            .execute()

    teachers_data = response.data

    # Step 2: Fetch all active monthly plans
    plans_res = supabase.table("teacher_monthly_plans").select("*").eq("active", True).execute()
    plans = plans_res.data if plans_res.data else []

    # Step 3: Create teacher_id -> plan map
    plan_map = {str(plan["teacher_id"]): plan for plan in plans}

    # Step 4: Inject fee into each teacher
    for teacher in teachers_data:
        tid = str(teacher["id"])
        teacher["monthly_fee"] = plan_map.get(tid, {}).get("price")

    return render_template('teachers.html', teachers=teachers_data, selected_category=category)

@app.route('/teacher/profile/<int:teacher_id>')
def teacher_profile(teacher_id):
    teacher_res = supabase.table("teachers").select("*").eq("id", teacher_id).single().execute()
    teacher = teacher_res.data
    if not teacher:
        return "Teacher not found", 404

    # Monthly Plan
    plan_res = supabase.table("teacher_monthly_plans").select("*").eq("teacher_id", teacher_id).eq("active", True).limit(1).execute()
    plans = plan_res.data
    monthly_plan = plans[0] if plans else None

    # Slots
    slots_res = supabase.table("available_slots").select("*").eq("teacher_id", teacher_id).execute()
    slots = slots_res.data if slots_res.data else []

    # Materials
    materials_res = supabase.table("teacher_materials").select("*").eq("teacher_id", teacher_id).execute()
    materials = materials_res.data if materials_res.data else []

    # Reviews
    reviews_res = supabase.table("reviews").select("*").eq("teacher_id", teacher_id).execute()
    reviews = reviews_res.data if reviews_res.data else []

    # ✅ Subscription check (corrected to use student_id)
    student_id = session.get("student_id")
    is_active_subscriber = False

    if student_id:
        sub_res = supabase.table("subscriptions")\
            .select("*")\
            .eq("teacher_id", teacher_id)\
            .eq("student_id", student_id)\
            .eq("status", "paid")\
            .execute()

        from datetime import datetime
        today = datetime.today().date()
        for sub in sub_res.data:
            end_date = datetime.strptime(sub["end_date"], "%Y-%m-%d").date()
            if end_date >= today:
                is_active_subscriber = True
                break

    return render_template("teacher_profile.html", 
        teacher=teacher, 
        slots=slots, 
        materials=materials, 
        reviews=reviews, 
        monthly_plan=monthly_plan,
        is_active_subscriber=is_active_subscriber
    )
@app.route('/book-slot/<int:slot_id>', methods=['GET', 'POST'])
def book_slot(slot_id):
    slot_res = supabase.table("available_slots").select("*").eq("id", slot_id).single().execute()
    slot_data = slot_res.data
    if not slot_data:
        return "Slot not found", 404

    teacher_res = supabase.table("teachers").select("*").eq("id", slot_data["teacher_id"]).single().execute()
    teacher_data = teacher_res.data

    # Count bookings
    bookings_res = supabase.table("bookings").select("id").eq("slot_id", slot_id).execute()
    total_booked = len(bookings_res.data)
    seat_limit = 30

    if total_booked >= seat_limit:
        return "Sorry, this slot is fully booked.", 400

    if request.method == 'POST':
        student_name = request.form['student_name']
        student_id = session.get("student_id")
        if not student_id:
            return redirect(url_for('student_login'))

        # ✅ Check subscription with student_id
        sub_res = supabase.table("subscriptions") \
            .select("*") \
            .eq("student_id", student_id) \
            .eq("teacher_id", slot_data["teacher_id"]) \
            .eq("status", "paid") \
            .execute()

        if not sub_res.data:
            flash("Please subscribe to this teacher before booking a slot.")
            return redirect(url_for('subscribe_teacher', teacher_id=slot_data["teacher_id"]))

        meet_link = teacher_data.get("meet_link", "")

        # ✅ Insert booking with student_id
        supabase.table("bookings").insert({
            "student_name": student_name,
            "student_id": student_id,
            "teacher_id": slot_data["teacher_id"],
            "slot_id": slot_id,
            "payment_status": "paid",
            "meeting_link": meet_link
        }).execute()

        # Mark full if needed
        if total_booked + 1 >= seat_limit:
            supabase.table("available_slots").update({"is_booked": True}).eq("id", slot_id).execute()

        # Send mail (optional)
        msg = Message(
            subject="Booking Confirmed!",
            sender=app.config['MAIL_USERNAME'],
            recipients=[session.get("student_email", "test@example.com")]  # fallback email
        )
        msg.body = f"""
Hi {student_name},

Your slot with {teacher_data['name']} for {teacher_data['subject']} is confirmed!

🗓️ Date: {slot_data['date']}
⏰ Time: {slot_data['start_time']} - {slot_data['end_time']}
📍 Meeting Link: {meet_link if meet_link else 'Will be shared later'}

Regards,
Online Tuition Team
"""
        mail.send(msg)

        return redirect(url_for('booking_success', meet_link=meet_link))

    return render_template(
        'book_slot.html',
        slot=slot_data,
        teacher=teacher_data,
        total_booked=total_booked,
        seat_limit=seat_limit
    )

@app.route('/booking-success')
def booking_success():
    meet_link = request.args.get('meet_link', '')
    return render_template('booking_success.html', meet_link=meet_link)


@app.route('/teacher_register', methods=['GET', 'POST'])
def teacher_register():
    if request.method == 'POST':
        name = request.form['name']
        subject = request.form['subject']
        experience = request.form['experience']
        school = request.form['school']
        email = request.form['email']
        reason = request.form['reason']
        category = request.form['category']  # NEW FIELD

        # Insert teacher data into Supabase with category
        supabase.table("teachers").insert({
            "name": name,
            "subject": subject,
            "experience": experience,
            "school": school,
            "email": email,
            "reason": reason,
            "category": category,
            "verified": False
        }).execute()

        return "Registration submitted! Wait for admin verification."
    
    return render_template('teacher_register.html')


# === Teacher Login Required ===

# === Edit Teacher Profile ===
@app.route('/teacher/edit-profile', methods=['GET', 'POST'])
def teacher_edit_profile():
    if 'teacher_id' not in session:
        return redirect(url_for('teacher_login'))

    teacher_id = session['teacher_id']

    if request.method == 'POST':
        image_url = request.form['image_url']
        bio = request.form['bio']
        experience = request.form['experience']
        rating = request.form['rating']

        supabase.table("teachers").update({
            "image_url": image_url,
            "bio": bio,
            "experience": experience,
            "rating": rating
        }).eq("id", teacher_id).execute()

        return redirect(url_for('teacher_dashboard'))

    teacher_res = supabase.table("teachers").select("*").eq("id", teacher_id).single().execute()
    teacher = teacher_res.data

    return render_template('edit_teacher_profile.html', teacher=teacher)


# === Add Available Slot ===
@app.route('/teacher/add-slot', methods=['GET', 'POST'], endpoint='teacher_add_slot')
def add_slot():

    teacher_id = session.get('teacher_id')
    if not teacher_id:
        return redirect(url_for('teacher_login'))

    if request.method == 'POST':
        date = request.form['date']
        start_time = request.form['start_time']
        end_time = request.form['end_time']

        supabase.table("available_slots").insert({
            "teacher_id": teacher_id,
            "date": date,
            "start_time": start_time,
            "end_time": end_time
        }).execute()

        return redirect(url_for('teacher_dashboard'))

    return render_template('add_slot.html', teacher_id=teacher_id)

@app.route('/teacher/delete-slot/<int:slot_id>', methods=['POST'])
def delete_slot(slot_id):
    teacher_id = session.get('teacher_id')
    if not teacher_id:
        return redirect(url_for('teacher_login'))

    supabase.table("available_slots").delete().eq("id", slot_id).eq("teacher_id", teacher_id).execute()

    return redirect(url_for('teacher_dashboard'))

@app.route('/teacher/edit-slot/<int:slot_id>', methods=['GET', 'POST'])
def edit_slot(slot_id):
    teacher_id = session.get('teacher_id')
    if not teacher_id:
        return redirect(url_for('teacher_login'))

    # Get the slot details
    slot_res = supabase.table("available_slots").select("*").eq("id", slot_id).eq("teacher_id", teacher_id).execute()
    slot_data = slot_res.data

    if not slot_data:
        return redirect(url_for('teacher_dashboard'))

    slot = slot_data[0]

    if request.method == 'POST':
        date = request.form['date']
        start_time = request.form['start_time']
        end_time = request.form['end_time']

        supabase.table("available_slots").update({
            "date": date,
            "start_time": start_time,
            "end_time": end_time
        }).eq("id", slot_id).execute()

        return redirect(url_for('teacher_dashboard'))

    return render_template('edit_slot.html', slot=slot)



# === Upload Study Material ===
@app.route('/teacher/add-material', methods=['GET', 'POST'])
def teacher_add_material():
    if 'teacher_id' not in session:
        return redirect(url_for('teacher_login'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        file_url = request.form['file_url']

        supabase.table("teacher_materials").insert({
            "teacher_id": session['teacher_id'],
            "title": title,
            "description": description,
            "file_url": file_url
        }).execute()

        return redirect(url_for('teacher_dashboard'))

    return render_template('add_material.html')

@app.route('/teacher/edit-material/<int:material_id>', methods=['GET', 'POST'])
def edit_material(material_id):
    teacher_id = session.get('teacher_id')
    if not teacher_id:
        return redirect(url_for('teacher_login'))

    # Fetch material details
    material_res = supabase.table("teacher_materials").select("*").eq("id", material_id).eq("teacher_id", teacher_id).execute()
    material_data = material_res.data

    if not material_data:
        return redirect(url_for('teacher_dashboard'))

    material = material_data[0]

    if request.method == 'POST':
        title = request.form['title']

        supabase.table("teacher_materials").update({
            "title": title
        }).eq("id", material_id).execute()

        return redirect(url_for('teacher_dashboard'))

    return render_template('edit_material.html', material=material)

@app.route('/teacher/delete-material/<int:material_id>', methods=['POST'])
def delete_material(material_id):
    teacher_id = session.get('teacher_id')
    if not teacher_id:
        return redirect(url_for('teacher_login'))

    supabase.table("teacher_materials").delete().eq("id", material_id).eq("teacher_id", teacher_id).execute()

    return redirect(url_for('teacher_dashboard'))

@app.route('/admin/teachers')
def admin_teachers():
    if not session.get('superadmin_logged_in'):
        return redirect(url_for('superadmin_login'))
    
    response = supabase.table("teachers").select("*").execute()
    teachers_data = response.data

    plans_res = supabase.table("teacher_monthly_plans").select("*").execute()
    plans = plans_res.data if plans_res.data else []

    # 🔥 FIXED: Convert teacher_id to string before mapping
    plan_map = {str(plan['teacher_id']): plan for plan in plans}

    return render_template('admin_teachers.html', teachers=teachers_data, plan_map=plan_map)

@app.route('/admin/teacher/set_login/<int:teacher_id>', methods=['POST'])
def set_teacher_login(teacher_id):
    if not session.get('superadmin_logged_in'):
        return redirect(url_for('superadmin_login'))

    username = request.form['username'].strip()
    password = request.form['password'].strip()

    supabase.table("teachers").update({
        "username": username,
        "password": password,
        "verified": True
    }).eq("id", teacher_id).execute()

    teacher_res = supabase.table("teachers").select("*").eq("id", teacher_id).single().execute()
    teacher = teacher_res.data

    if teacher:
        try:
            msg = Message(
                subject="Your Teacher Account Login Details",
                sender=app.config['MAIL_USERNAME'],
                recipients=[teacher["email"]]
            )
            msg.body = f"""
Hi {teacher['name']},

Your teacher account has been approved and your login details are as follows:

🔐 Username: {username}  
🔑 Password: {password}  

You can log in here: https://smartkalvi.onrender.com/teacher/login

Please log in to your account and start using the platform.
We encourage you to log in and start exploring the platform. If you face any issues or need assistance, feel free to contact our support team.

Thank you for being part of SmartKalvi.

Best regards,  
SmartKalvi Team
"""
            mail.send(msg)
        except Exception as e:
            print(f"Email sending failed: {e}")

    return redirect(url_for('admin_teachers'))


@app.route('/admin/teacher/plan/<int:teacher_id>', methods=['GET', 'POST'])
def set_monthly_plan(teacher_id):
    if not session.get('superadmin_logged_in'):
        return redirect(url_for('superadmin_login'))

    if request.method == 'POST':
        price = request.form['price']
        description = request.form['description']

        # Check if existing plan available
        existing_plan_res = supabase.table("teacher_monthly_plans").select("*").eq("teacher_id", teacher_id).limit(1).execute()
        existing_plan = existing_plan_res.data[0] if existing_plan_res.data else None

        if existing_plan:
            supabase.table("teacher_monthly_plans").update({
                "price": price,
                "description": description,
                "active": True
            }).eq("teacher_id", teacher_id).execute()
        else:
            supabase.table("teacher_monthly_plans").insert({
                "teacher_id": teacher_id,
                "price": price,
                "description": description,
                "active": True
            }).execute()

        return redirect(url_for('admin_teachers'))

    # Get teacher details
    teacher_res = supabase.table("teachers").select("*").eq("id", teacher_id).limit(1).execute()
    teacher = teacher_res.data[0] if teacher_res.data else None

    if not teacher:
        return "Teacher not found", 404

    # Get plan details if exists
    plan_res = supabase.table("teacher_monthly_plans").select("*").eq("teacher_id", teacher_id).limit(1).execute()
    plan = plan_res.data[0] if plan_res.data else None

    return render_template('set_monthly_plan.html', teacher=teacher, plan=plan)


@app.route('/admin/materials')
def admin_materials():
    if not session.get('superadmin_logged_in'):
        return redirect(url_for('superadmin_login'))

    materials_res = supabase.table("teacher_materials").select("*").execute()
    materials_data = materials_res.data

    return render_template('admin_materials.html', materials=materials_data)

@app.route('/admin/bookings')
def admin_bookings():
    if not session.get('superadmin_logged_in'):
        return redirect(url_for('superadmin_login'))

    bookings_res = supabase.table("bookings").select("*").order("created_at", desc=True).execute()

    bookings_data = bookings_res.data

    # Slots
    slot_ids = list({b["slot_id"] for b in bookings_data})
    slots_map = {}
    if slot_ids:
        slots_res = supabase.table("slots").select("*").in_("id", slot_ids).execute()
        slots_map = {s["id"]: s for s in slots_res.data}

    # Teachers
    teacher_ids = list({b["teacher_id"] for b in bookings_data})
    teachers_map = {}
    if teacher_ids:
        teachers_res = supabase.table("teachers").select("*").in_("id", teacher_ids).execute()
        teachers_map = {t["id"]: t for t in teachers_res.data}

    # Students
    student_ids = list({b["student_id"] for b in bookings_data if "student_id" in b})
    students_map = {}
    if student_ids:
        students_res = supabase.table("students").select("*").in_("id", student_ids).execute()
        students_map = {s["id"]: s for s in students_res.data}

    # ✅ Subscriptions
    subs_map = {}
    if student_ids:
        subs_res = supabase.table("subscriptions").select("*").in_("student_id", student_ids).execute()
        for sub in subs_res.data:
            key = (sub["student_id"], sub["teacher_id"])
            subs_map[key] = sub

    print("🔎 Subscriptions Loaded:", subs_map.keys())

    # Attach all info
    for b in bookings_data:
        slot = slots_map.get(b["slot_id"], {})
        teacher = teachers_map.get(b["teacher_id"], {})
        student = students_map.get(b.get("student_id"), {})

        b["slot_time"] = f"{slot.get('date', '')} {slot.get('start_time', '')} - {slot.get('end_time', '')}"
        b["teacher_name"] = teacher.get("name", "Unknown")
        b["subject"] = teacher.get("subject", "Unknown")
        b["student_name"] = student.get("name", "Unknown")
        b["student_email"] = student.get("email", "Unknown")

        sub_key = (b.get("student_id"), b.get("teacher_id"))
        subscription = subs_map.get(sub_key)
        b["subscription_status"] = subscription["status"] if subscription else "❌ Not Subscribed"

        print("📦 Booking ID:", b["id"], "| Sub Key:", sub_key, "| Sub Status:", b["subscription_status"])

    return render_template('admin_bookings.html', bookings=bookings_data)

@app.route('/admin/payments')
def admin_payments():
    if not session.get('superadmin_logged_in'):
        return redirect(url_for('superadmin_login'))

    # Fetch subscriptions with teacher name
    query = """
    SELECT ss.id, ss.student_email, ss.amount, ss.start_date, ss.end_date, 
           t.name AS teacher_name, t.subject 
    FROM student_subscriptions ss
    JOIN teachers t ON ss.teacher_id = t.id
    ORDER BY ss.start_date DESC
    """
    res = supabase.rpc('execute_sql', {'sql': query}).execute()
    payments = res.data if res.data else []

    return render_template('admin_payments.html', payments=payments, current_date=date.today().isoformat())

@app.route('/teacher/bookings')
def teacher_bookings():
    teacher_id = session.get('teacher_id')
    if not teacher_id:
        return redirect(url_for('teacher_login'))

    # Step 1: Get teacher's slots
    slots_res = supabase.table("available_slots").select("*").eq("teacher_id", teacher_id).execute()
    slots = slots_res.data

    slot_map = {slot['id']: slot for slot in slots}

    # Step 2: Get bookings for those slots
    bookings = []
    if slot_map:
        slot_ids = list(slot_map.keys())
        bookings_res = supabase.table("bookings").select("*").in_("slot_id", slot_ids).execute()
        raw_bookings = bookings_res.data

        # Step 3: Attach slot time & booked_at
        for booking in raw_bookings:
            slot = slot_map.get(booking["slot_id"])
            slot_time = f"{slot['date']} {slot['start_time']} - {slot['end_time']}" if slot else "N/A"

            bookings.append({
                "id": booking["id"],
                "student_name": booking["student_name"],
                "student_email": booking["student_email"],
                "slot_time": slot_time,
                "created_at": booking.get("created_at", "N/A")
            })

    return render_template('teacher_bookings.html', bookings=bookings)

@app.route('/review/<int:teacher_id>', methods=['GET', 'POST'])
def review_teacher(teacher_id):
    # Fetch teacher for display
    teacher_res = supabase.table("teachers").select("*").eq("id", teacher_id).single().execute()
    teacher_data = teacher_res.data

    if not teacher_data:
        return "Teacher not found", 404

    if request.method == 'POST':
        student_name = request.form['student_name']
        rating = int(request.form['rating'])
        comment = request.form['comment']

        # Insert review
        supabase.table("reviews").insert({
            "teacher_id": teacher_id,
            "student_name": student_name,
            "rating": rating,
            "comment": comment
        }).execute()

        # Recalculate average rating
        reviews_res = supabase.table("reviews").select("rating").eq("teacher_id", teacher_id).execute()
        reviews = reviews_res.data

        total_reviews = len(reviews)
        total_rating = sum([r['rating'] for r in reviews])
        average_rating = round(total_rating / total_reviews, 2)

        # Update teacher record
        supabase.table("teachers").update({
            "rating": average_rating,
            "total_reviews": total_reviews
        }).eq("id", teacher_id).execute()

        return redirect(url_for('teacher_profile', teacher_id=teacher_id))

    return render_template('review_form.html', teacher=teacher_data)
import datetime
from datetime import timedelta

@app.route('/subscribe/<int:teacher_id>', methods=['GET', 'POST'])
def subscribe_teacher(teacher_id):
    student_id = session.get('student_id')
    if not student_id:
        return redirect(url_for('student_login'))

    teacher_res = supabase.table("teachers").select("*").eq("id", teacher_id).single().execute()
    teacher_data = teacher_res.data
    if not teacher_data:
        return "Teacher not found", 404

    plan_res = supabase.table("teacher_monthly_plans").select("*").eq("teacher_id", teacher_id).eq("active", True).limit(1).execute()
    plan = plan_res.data[0] if plan_res.data else None

    if not plan:
        return "No active plan for this teacher", 400

    if request.method == 'POST':
        payment_ref_id = request.form['payment_ref_id']
        now = datetime.datetime.now()

        supabase.table("subscriptions").insert({
            "student_id": student_id,
            "teacher_id": teacher_id,
            "amount": plan["price"],
            "status": "pending",
            "payment_ref_id": payment_ref_id,
            "start_date": now.strftime("%Y-%m-%d"),
            "end_date": (now + timedelta(days=30)).strftime("%Y-%m-%d")
        }).execute()

        flash("✅ Subscription submitted for approval.")
        return redirect(url_for('booking_success.html'))

    teacher_data["monthly_fee"] = plan["price"]
    return render_template('subscribe_plan.html', teacher=teacher_data)

@app.route('/admin/subscriptions')
def admin_subscriptions():
    if not session.get('superadmin_logged_in'):
        return redirect(url_for('superadmin_login'))

    subs_res = supabase.table("subscriptions").select("*").order("created_at", desc=True).execute()
    subscriptions = subs_res.data

    # Map student & teacher info
    student_ids = {sub["student_id"] for sub in subscriptions if sub.get("student_id")}
    teacher_ids = {sub["teacher_id"] for sub in subscriptions}

    students_map = {}
    if student_ids:
        res = supabase.table("students").select("id,name").in_("id", list(student_ids)).execute()

        students_map = {s["id"]: s for s in res.data}

    teachers_map = {}
    if teacher_ids:
        res = supabase.table("teachers").select("id,name,subject").in_("id", list(teacher_ids)).execute()
        teachers_map = {t["id"]: t for t in res.data}

    # Attach info
    for sub in subscriptions:
        sub["student"] = students_map.get(sub["student_id"], {})
        sub["teacher"] = teachers_map.get(sub["teacher_id"], {})

    return render_template("admin_subscriptions.html", subscriptions=subscriptions)

@app.route('/admin/update-subscription/<string:sub_id>', methods=['POST'])
def update_subscription_status(sub_id):
    if not session.get('superadmin_logged_in'):
        return redirect(url_for('superadmin_login'))

    action = request.form.get('action')
    if action == "approve":
        status = "paid"
    elif action == "reject":
        status = "rejected"
    else:
        status = "pending"

    supabase.table("subscriptions").update({"status": status}).eq("id", sub_id).execute()
    flash(f"Subscription marked as {status.upper()}")
    return redirect(url_for('admin_subscriptions'))

@app.route('/teacher/request_withdrawal', methods=['GET', 'POST'])
def request_withdrawal():
    if 'teacher_id' not in session:
        return redirect(url_for('teacher_login'))

    teacher_id = session['teacher_id']

    if request.method == 'POST':
        remarks = request.form.get('remarks', '')

        supabase.table("withdrawal_requests").insert({
            "teacher_id": teacher_id,
            "status": "pending",
            "remarks": remarks,
            "created_at": datetime.now().isoformat()
        }).execute()

        return redirect(url_for('dashboard'))

    # If GET request, show form
    teacher_res = supabase.table("teachers").select("*").eq("id", teacher_id).single().execute()
    teacher_data = teacher_res.data

    return render_template('request_withdrawal.html', teacher=teacher_data)


# === Run App ===

import os

import os

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
