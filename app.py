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

import requests
import fitz  # or use pdfplumber if PyMuPDF fails
from flask import request, render_template, session, redirect, url_for
import together

together.api_key = "3041964b24957ccdabbb5678a13f8e5bcb895a98c508c1c0469dfb9ad5e0bfce"


# === Google Cloud Config ===
import json
from google.oauth2 import service_account

credentials = None

# Try to load from environment (for Render)
import os
import json
from google.oauth2 import service_account
from google.cloud import storage, vision

credentials_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")

if credentials_json:
    credentials_dict = json.loads(credentials_json)
    
    # 🔥 Fix newline issue in private key
    if "private_key" in credentials_dict:
        credentials_dict["private_key"] = credentials_dict["private_key"].replace("\\n", "\n")

    credentials = service_account.Credentials.from_service_account_info(credentials_dict)

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

    student_id = session['student_id']

    # ✅ 1. Get student data
    student_res = supabase.table("students").select("*, classes(*)").eq("id", student_id).single().execute()

    student = student_res.data if student_res.data else {}

    # ✅ 2. Get student coins
    coin_response = supabase.table('student_coins').select("total_coins").eq("student_id", student_id).limit(1).execute()
    coin_data = coin_response.data[0] if coin_response.data else None
    total_coins = coin_data['total_coins'] if coin_data else 0

    # ✅ 3. Get syllabus
    syllabus_res = supabase.table("syllabus").select("*").execute()
    syllabus_data = syllabus_res.data if syllabus_res.data else []

    formatted_syllabus = []
    for item in syllabus_data:
        topics = item.get("topics")
        if isinstance(topics, str):
            try:
                topics = json.loads(topics)
            except:
                topics = []
        formatted_syllabus.append({
            "class_level": item.get("class_level"),
            "subject": item.get("subject"),
            "topics": topics
        })

    # ✅ 4. Get verified teachers
    teachers_res = supabase.table("teachers").select("*").eq("verified", True).execute()
    teachers_list = teachers_res.data if teachers_res.data else []

    # Map teacher_id to teacher details
    teacher_map = {str(t['id']): t for t in teachers_list}

    # ✅ 5. Get booked teachers
    booking_res = supabase.table("bookings").select("*").eq("student_id", student_id).limit(5).execute()
    booked_rows = booking_res.data if booking_res.data else []

    booked_teachers = []
    for booking in booked_rows:
        teacher_id = str(booking.get("teacher_id"))
        teacher = teacher_map.get(teacher_id)
        if teacher:
            booked_teachers.append({
                "booking": booking,
                "teacher": teacher
            })

    # ✅ Final render (removed posts and badges)
    return render_template(
        'index.html',
        student=student,
        total_coins=total_coins,
        syllabus=formatted_syllabus,
        teachers=teachers_list,
        booked_teachers=booked_teachers
    )

# === Super Admin Routes - Clean and Organized ===

@app.route('/school_admin/dashboard')
def school_admin_dashboard():
    if 'school_admin_id' not in session:
        return redirect(url_for('school_admin_login'))

    school_id = session['school_id']

    # Fetch school details
    school_resp = supabase.table('schools').select("*").eq('id', school_id).single().execute()
    school = school_resp.data

    # Fetch teachers of this school
    teachers_resp = supabase.table('school_teachers').select("*").eq('school_id', school_id).execute()
    teachers = teachers_resp.data

    total_fee = calculate_total_fee(school)

    return render_template('school_admin_dashboard.html',
                           school=school,
                           teachers=teachers,
                           total_fee=total_fee)


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
                session['role'] = 'school_admin'
                return redirect(url_for('school_admin_dashboard'))

        return render_template('school_admin_login.html', error="❌ Invalid username or password")

    return render_template('school_admin_login.html')
from collections import defaultdict

@app.route('/school_admin/performance')
def school_admin_performance():
    if 'school_admin_id' not in session:
        return redirect(url_for('school_admin_login'))

    school_id = session['school_admin_id']
    selected_class = request.args.get('class', '')

    all_classes = []
    performance_by_subject = defaultdict(lambda: {
        'total_score': 0,
        'total_marks': 0,
        'students': 0
    })

    try:
        # Fetch all class levels
        response = supabase.table('answers').select('class_level').eq('school_id', school_id).execute()
        if response.data:
            all_classes = list(set([row['class_level'] for row in response.data if 'class_level' in row]))

        # Fetch data
        query = supabase.table('answers').select('*').eq('school_id', school_id)
        if selected_class:
            query = query.eq('class_level', selected_class)
        data = query.execute().data

        for row in data:
            subject = row.get('subject', 'Unknown')
            class_level = row.get('class_level', 'N/A')
            score = row.get('score', 0)
            total = row.get('total_marks', 1)

            key = (subject, class_level)
            performance_by_subject[key]['total_score'] += score
            performance_by_subject[key]['total_marks'] += total
            performance_by_subject[key]['students'] += 1

        final_subject_data = []
        for (subject, class_level), stats in performance_by_subject.items():
            total_score = stats['total_score']
            total_marks = stats['total_marks']
            students = stats['students']
            avg_percentage = round((total_score / total_marks) * 100, 2) if total_marks else 0

            final_subject_data.append((
                subject,
                class_level,
                students,
                round(total_score / students, 2),
                avg_percentage
            ))

    except Exception as e:
        print("Error:", e)
        final_subject_data = []

    return render_template("school_admin_performance_subjectwise.html",
                           subject_data=final_subject_data,
                           all_classes=all_classes,
                           selected_class=selected_class)


from werkzeug.security import generate_password_hash, check_password_hash
from flask import flash, session, redirect, url_for, render_template, request

@app.route('/school_admin/add_teacher', methods=['GET', 'POST'])
def add_teacher():
    if 'school_admin_id' not in session:
        return redirect(url_for('school_admin_login'))

    if request.method == 'POST':
        # Handle form submission
        school_id = session['school_id']
        name = request.form['name']
        username = request.form['username']  # ✅ ADD THIS
        subject = request.form['subject']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']

        # Insert into Supabase
        supabase.table('school_teachers').insert({
            "school_id": school_id,
            "name": name,
            "username": username,       # ✅ Important field
            "email": email,
            "phone": phone,
            "subject": subject,
            "password": password
        }).execute()

        return redirect(url_for('school_admin_dashboard'))

    # Render the teacher add form
    return render_template('add_teacher.html')

@app.route('/school_teacher/login', methods=['GET', 'POST'])
def school_teacher_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        result = supabase.table('school_teachers').select("*").eq('username', username).single().execute()
        teacher = result.data

        if teacher and teacher['password'] == password:
            session['school_teacher_id'] = teacher['id']
            return redirect(url_for('school_teacher_dashboard'))
        else:
            return render_template('school_teacher_login.html', error="Invalid username or password.")

    return render_template('school_teacher_login.html')

@app.route('/school_teacher/dashboard')
def school_teacher_dashboard():
    if 'school_teacher_id' not in session:
        return redirect(url_for('school_teacher_login'))

    school_teacher_id = session['school_teacher_id']

    # Get teacher details
    teacher_result = supabase.table("school_teachers").select("*").eq("id", school_teacher_id).execute()
    teacher = teacher_result.data[0] if teacher_result.data else None
    print("DEBUG - Teacher:", teacher)

    subject = teacher['subject'] if teacher else "N/A"

    # Check school ID and fetch school
    school_name = "N/A"
    if teacher and teacher.get('school_id'):
        school_id = teacher['school_id']
        print("DEBUG - School ID from teacher:", school_id)

        school_result = supabase.table("schools").select("name").eq("id", school_id).execute()
        print("DEBUG - School Query Result:", school_result.data)

        if school_result.data:
            school_name = school_result.data[0]['name']

    # Class logic as before
    assigned_class = "Not Assigned"
    mapping_result = supabase.table("class_teacher_mappings") \
        .select("class_id") \
        .eq("teacher_id", school_teacher_id) \
        .execute()

    if mapping_result.data:
        class_id = mapping_result.data[0]['class_id']
        class_result = supabase.table("classes").select("class_name").eq("id", class_id).execute()
        if class_result.data:
            assigned_class = class_result.data[0]['class_name']

    return render_template("school_teacher_dashboard.html", teacher=teacher, school_name=school_name, subject=subject, assigned_class=assigned_class)

@app.route('/school_admin/teachers')
def school_list_teachers():
    if 'school_admin_id' not in session:
        return redirect(url_for('school_admin_login'))

    school_id = session['school_id']
    response = supabase.table('school_teachers').select("*").eq("school_id", school_id).execute()
    teachers = response.data

    return render_template('school_list_teachers.html', teachers=teachers)

@app.route('/school_admin/edit_teacher/<string:teacher_id>', methods=['GET', 'POST'])
def edit_teacher(teacher_id):
    if 'school_admin_id' not in session:
        return redirect(url_for('school_admin_login'))

    # GET method: load teacher info
    if request.method == 'GET':
        response = supabase.table('school_teachers').select("*").eq('id', teacher_id).single().execute()
        teacher = response.data
        return render_template('edit_teacher.html', teacher=teacher)

    # POST method: update the teacher info
    name = request.form['name']
    subject = request.form['subject']
    assigned_class = request.form['assigned_class']
    rating = float(request.form['rating'])

    supabase.table('school_teachers').update({
        "name": name,
        "subject": subject,
        "assigned_class": assigned_class,
        "rating": rating
    }).eq('id', teacher_id).execute()

    return redirect(url_for('school_list_teachers'))

@app.route('/school_teacher/logout')
def school_teacher_logout():
    session.pop('school_teacher_id', None)
    return redirect(url_for('school_teacher_login'))

@app.route('/teacher/logout')
def teacher_logout():
    session.pop('tutor_teacher_id', None)
    return redirect(url_for('teacher_login'))


import os
import gdown
import fitz  # PyMuPDF
from flask import request, render_template, session, redirect, url_for
import together
together.api_key = "3041964b24957ccdabbb5678a13f8e5bcb895a98c508c1c0469dfb9ad5e0bfce"
import os
import gdown
import fitz  # PyMuPDF
from flask import request, render_template, session, redirect, url_for
import together

def get_or_extract_chapter_text(board, class_name, subject, chapter, gdrive_id):
    from supabase import create_client
    import gdown
    import fitz  # PyMuPDF
    import os

    # ✅ Step 0: Ensure supabase client is ready
    # (Assuming `supabase` is globally initialized)

    # ✅ Step 1: Check Supabase for existing chapter content
    try:
        res = supabase.table("chapter_contents").select("*")\
            .eq("board", board)\
            .eq("class", int(class_name))\
            .eq("subject", subject)\
            .eq("chapter", chapter)\
            .execute()

        if res.data and len(res.data) > 0:
            print("📦 Fetched chapter from Supabase cache")
            return res.data[0]['content']
    except Exception as e:
        print("❌ Supabase fetch error:", str(e))

    # ✅ Step 2: Get page range from Supabase
    try:
        page_info = supabase.table("chapter_ranges").select("*")\
            .eq("board", board)\
            .eq("class", int(class_name))\
            .eq("subject", subject)\
            .eq("chapter", chapter)\
            .single()\
            .execute()

        start_page = page_info.data['start_page']
        end_page = page_info.data['end_page']
        print(f"📄 Pages to extract: {start_page} - {end_page}")
    except Exception as e:
        print("⚠️ Chapter page range not found in Supabase:", str(e))
        return "⚠️ Chapter page range not found in Supabase."

    # ✅ Step 3: Download the PDF from Google Drive
    local_pdf = "temp_chapter.pdf"
    try:
        gdown.download(f"https://drive.google.com/uc?id={gdrive_id}", local_pdf, quiet=False)
    except Exception as e:
        print("❌ PDF download failed:", str(e))
        return "❌ Failed to download textbook PDF."

    # ✅ Step 4: Extract specific pages
    try:
        doc = fitz.open(local_pdf)
        extracted_text = ""
        for i in range(start_page - 1, end_page):
            extracted_text += doc[i].get_text()
        doc.close()
        os.remove(local_pdf)  # clean up
    except Exception as e:
        print("❌ PDF extraction error:", str(e))
        return "❌ Failed to extract pages from PDF."

    chapter_text = extracted_text.strip()

    # ✅ Step 5: Save to Supabase for caching
    try:
        supabase.table("chapter_contents").insert({
            "board": board,
            "class": int(class_name),
            "subject": subject,
            "chapter": chapter,
            "content": chapter_text
        }).execute()
        print("✅ Chapter content saved to Supabase")
    except Exception as e:
        print("⚠️ Failed to insert chapter content into Supabase:", str(e))

    return chapter_text

@app.route('/school_teacher/create_question_set', methods=['GET', 'POST'])
def create_question_set():
    if 'school_teacher_id' not in session:
        return redirect(url_for('school_teacher_login'))

    def safe_int(value):
        try:
            return int(value)
        except (ValueError, TypeError):
            return 0

    if request.method == 'POST':
        board = request.form['board']
        class_name = request.form['class']
        subject = request.form['subject']
        chapter = request.form['chapter']
        difficulty = request.form['difficulty']

        total_marks = safe_int(request.form.get('total_marks'))
        choose_count = safe_int(request.form.get('choose_count'))
        fillups_count = safe_int(request.form.get('fillups_count'))
        match_count = safe_int(request.form.get('match_count'))
        count_2m = safe_int(request.form.get('2m_count'))
        count_5m = safe_int(request.form.get('5m_count'))
        count_10m = safe_int(request.form.get('10m_count'))

        grammar = 'grammar' in request.form
        extras = []
        if 'map' in request.form: extras.append("map-based")
        if 'diagram' in request.form: extras.append("diagram-based")
        if 'graph' in request.form: extras.append("graph-based")

        if total_marks == 0:
            return render_template('create_question_set.html', questions=["⚠️ Please enter a valid number for Total Marks."])

        print("🎯 INPUTS →", board, class_name, subject, chapter)

        # Get book PDF info
        book_result = supabase.table("book_files").select("*") \
            .ilike("board", board) \
                .eq("class", int(class_name)) \
                    .ilike("subject", subject).execute()


        if not book_result.data:
            return render_template('create_question_set.html', questions=["⚠️ Book PDF not found in Supabase."])

        gdrive_id = book_result.data[0].get("gdrive_id")

        # Get chapter page range
        chapter_result = supabase.table("chapter_ranges").select("*") \
            .eq("class", int(class_name)) \
                .ilike("subject", subject) \
                    .ilike("chapter", chapter).execute()

        if not chapter_result.data:
            return render_template('create_question_set.html', questions=["⚠️ Chapter page range not found in Supabase."])

        start_page = chapter_result.data[0].get("start_page")
        end_page = chapter_result.data[0].get("end_page")

        if not gdrive_id or not start_page or not end_page:
            return render_template('create_question_set.html', questions=["⚠️ Missing book or chapter page info."])

        # Extract text from PDF
        chapter_text = get_or_extract_chapter_text(board, class_name, subject, chapter, gdrive_id, )

        def trim_chapter_text(text, max_tokens=4000):
            return text[:max_tokens] + "\n\n[...trimmed for length...]" if len(text) > max_tokens else text

        chapter_text = trim_chapter_text(chapter_text)

        # Build section prompts
        section_prompt = ""
        if choose_count > 0:
            section_prompt += f"- Section A: Choose the Correct Answer (1 mark each) — {choose_count} questions\n"
        if fillups_count > 0:
            section_prompt += f"- Section B: Fill in the Blanks (1 mark each) — {fillups_count} questions\n"
        if match_count > 0:
            section_prompt += f"- Section C: Match the Following (1 mark each) — {match_count} questions\n"
        if count_2m > 0:
            section_prompt += f"- Section D: 2 Mark Questions — {count_2m} questions\n"
        if count_5m > 0:
            section_prompt += f"- Section E: 5 Mark Questions — {count_5m} questions\n"
        if count_10m > 0:
            section_prompt += f"- Section F: 10 Mark Essay Questions — {count_10m} questions\n"
        if grammar and subject.lower() == "english":
            section_prompt += "- Include grammar-based questions\n"
        if extras:
            section_prompt += f"- Include at least one {' / '.join(extras)} question.\n"

        full_board_name = "Central Board of Secondary Education" if board.lower() == "cbse" else "Tamil Nadu State Board"

        prompt = f"""
You are an expert question paper setter for the {full_board_name} ({board} syllabus) in India.

🎯 Create a *{difficulty.title()} Level* Model Question Paper with the following structure:

-------------------------------------
Class: {class_name}
Subject: {subject}
Chapter: {chapter}
Board: {full_board_name.upper()}
Total Marks: {total_marks}
Time: 2½ Hours
-------------------------------------

📘 Use the following official chapter content for question generation:
\"\"\"{chapter_text}\"\"\"

{section_prompt}

📝 Guidelines:
- Only output the question paper. Do NOT include any answers, hints, or explanations.
- Format questions in numbered order under each section heading.
- Indicate marks at the end of each question, e.g., [2 marks].
- Ensure clean formatting like a final printed exam paper.
"""

        try:
            response = together.Complete.create(
                model="meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
                prompt=prompt,
                max_tokens=800,
                temperature=0.7
            )

            full_text = response['choices'][0]['text'].strip()

            def extract_section(title):
                if title in full_text:
                    parts = full_text.split(title)
                    return parts[1].split("Section", 1)[0].strip() if len(parts) > 1 else ""
                return ""

            question_json = {
                "choose": extract_section("Section A: Choose"),
                "fillups": extract_section("Section B: Fill"),
                "match": extract_section("Section C: Match"),
                "2m": extract_section("Section D: 2 Mark"),
                "5m": extract_section("Section E: 5 Mark"),
                "10m": extract_section("Section F: 10 Mark"),
                "grammar": extract_section("grammar"),
                "map": extract_section("map"),
                "diagram": extract_section("diagram"),
                "graph": extract_section("graph")
            }

            # ✅ Save to Supabase
            save_result = supabase.table("question_sets").insert({
                "school_teacher_id": session['school_teacher_id'],
                "board": board,
                "class_number": safe_int(class_name),
                "subject": subject,
                "chapter": chapter,
                "difficulty": difficulty,
                "total_marks": total_marks,
                "question_types": [],  # Manual split, so empty
                "questions": full_text,
                "question_json": question_json
            }).execute()

            print("✅ Inserted Question Set:", save_result.data)
            return render_template('create_question_set.html', questions=full_text.splitlines())

        except Exception as e:
            print("❌ AI Generation Error:", str(e))
            return render_template('create_question_set.html', questions=[f"⚠️ AI error: {str(e)}"])

    return render_template('create_question_set.html')


@app.route('/school_teacher/question_sets')
def my_question_sets():
    print("🚀 Route /school_teacher/question_sets was called")

    if 'school_teacher_id' not in session:
        print("❌ session['school_teacher_id'] missing")
        return redirect(url_for('school_teacher_login'))

    teacher_id = str(session['school_teacher_id'])
    print("✅ Session ID:", teacher_id)

    result = supabase.table("question_sets") \
        .select("*") \
        .eq("school_teacher_id", teacher_id) \
        .order("created_at", desc=True) \
        .execute()

    question_sets = result.data
    print("✅ Question Sets from DB:", question_sets)

    return render_template('school_teacher_question_sets.html', sets=question_sets)

from flask import make_response
from fpdf import FPDF  # install: pip install fpdf

# 📥 Route to download question set as PDF
@app.route('/school_teacher/question_sets/<set_id>/download')
def download_question_set_pdf(set_id):
    if 'school_teacher_id' not in session:
        return redirect(url_for('school_teacher_login'))

    # Fetch the question set
    res = supabase.table("question_sets").select("*").eq("id", set_id).single().execute()
    qset = res.data

    if not qset or str(qset.get("school_teacher_id")) != str(session['school_teacher_id']):
        return "Unauthorized", 403

    # Generate PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt=f"{qset['subject']} - {qset['chapter']}", ln=True, align='C')
    pdf.ln(10)
    for line in qset['questions'].split('\n'):
        pdf.multi_cell(0, 10, txt=line)

    response = make_response(pdf.output(dest='S').encode('latin1'))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=question_set_{set_id}.pdf'
    return response

# 🗑️ Route to delete question set
@app.route('/school_teacher/question_sets/<set_id>/delete', methods=['POST'])
def delete_question_set(set_id):
    if 'school_teacher_id' not in session:
        return redirect(url_for('school_teacher_login'))

    # Check ownership before deleting
    res = supabase.table("question_sets").select("school_teacher_id").eq("id", set_id).single().execute()
    owner_id = res.data.get("school_teacher_id") if res.data else None

    if not owner_id or str(owner_id) != str(session['school_teacher_id']):
        return "Unauthorized", 403

    supabase.table("question_sets").delete().eq("id", set_id).execute()
    return redirect(url_for('my_question_sets'))

@app.route("/school_admin/assign_class", methods=["GET", "POST"])
def assign_class():
    if request.method == "POST":
        school_id = session.get("school_id")
        teacher_id = request.form.get("teacher_id")
        class_id = request.form.get("class_id")  # Changed from class_name

        if not (school_id and teacher_id and class_id):
            return "Missing data", 400

        supabase.table("class_teacher_mappings").insert({
            "school_id": school_id,
            "teacher_id": teacher_id,
            "class_id": class_id  # changed here
        }).execute()

        return redirect(url_for("view_class_teachers"))

    
    # Show teacher and class list
    teachers = supabase.table("school_teachers").select("*").eq("school_id", session.get("school_id")).execute().data
    classes = supabase.table("classes").select("id, class_name").eq("school_id", session.get("school_id")).execute().data
    return render_template("class_teacher_mapping.html", teachers=teachers, classes=classes)

@app.route("/school_admin/add_class", methods=["GET", "POST"])
def add_class():
    if request.method == "POST":
        class_name = request.form.get("class_name")
        class_level = request.form.get("class_level")
        school_id = session.get("school_id")

        if not (class_name and class_level and school_id):
            return "Missing data", 400

        supabase.table("classes").insert({
            "class_name": class_name,
            "class_level": class_level,
            "school_id": school_id
        }).execute()

        return redirect(url_for("add_class"))

    classes = supabase.table("classes").select("*").eq("school_id", session.get("school_id")).execute().data
    return render_template("add_class.html", classes=classes)


@app.route("/school_admin/view_class_teachers")
def view_class_teachers():
    class_teachers = supabase.table("class_teacher_mappings") \
        .select("id, classes(class_name), school_teachers(name)") \
        .execute().data
    return render_template("view_class_teachers.html", mappings=class_teachers)

@app.route('/teacher/edit_profile', methods=['GET', 'POST'])
def edit_teacher_profile():
    if 'school_teacher_id' not in session:
        return redirect(url_for('school_teacher_login'))

    teacher_id = session['school_teacher_id']

    # Fetch existing teacher details
    teacher = supabase.table('school_teachers').select("*").eq("id", teacher_id).single().execute().data

    if request.method == 'POST':
        name = request.form.get('name')
        subject = request.form.get('subject')
        profile_pic_url = request.form.get('profile_pic')  # Save image URL here

        # Update teacher profile
        update_response = supabase.table('school_teachers').update({
            'name': name,
            'subject': subject,
            'profile_pic': profile_pic_url
        }).eq("id", teacher_id).execute()

        return redirect(url_for('school_teacher_dashboard'))

    return render_template("editt_teacher_profile.html", teacher=teacher)

@app.route('/teacher/performance')
def teacher_performance():
    if 'school_teacher_id' not in session:
        return redirect(url_for('school_teacher_login'))

    teacher_id = session['school_teacher_id']
    subject = session.get('subject', '')  # ✅ Must set this during login
    selected_class = request.args.get('class', '')

    all_classes = []
    performance_data = []
    weak_students = []

    try:
        # Fetch classes where this teacher's subject was answered
        class_resp = supabase.table('answers').select('class_level').eq('subject', subject).execute()
        if class_resp.data:
            all_classes = list(set([row['class_level'] for row in class_resp.data if 'class_level' in row]))
    except Exception as e:
        print(f"Error fetching teacher classes: {e}")

    try:
        # Fetch answers filtered by teacher subject and optional class
        query = supabase.table('answers').select('*').eq('subject', subject)

        if selected_class:
            query = query.eq('class_level', selected_class)

        answers = query.execute().data

        for row in answers:
            student_id = row.get('student_id', 'N/A')
            class_level = row.get('class_level', 'N/A')
            score = row.get('score', 0)
            total_marks = row.get('total_marks', 1)

            # Fetch student name
            student_name = "N/A"
            try:
                student_response = supabase.table('students').select('name').eq('id', student_id).single().execute()
                if student_response.data and 'name' in student_response.data:
                    student_name = student_response.data['name']
            except Exception as e:
                print(f"Error fetching student name: {e}")

            percentage = round((score / total_marks) * 100, 2) if total_marks else 0

            performance_data.append((
                student_name,
                class_level,
                1,  # exams attempted
                score,
                percentage
            ))

            if percentage < 50:
                weak_students.append((student_name, class_level, percentage))

    except Exception as e:
        print(f"Error fetching teacher performance: {e}")

    return render_template("teacher_performance.html",
                           performance=performance_data,
                           all_classes=all_classes,
                           selected_class=selected_class,
                           weak_students=weak_students)

@app.route('/teacher/rating')
def teacher_rating():
    return "Teacher rating page coming soon"

@app.route('/school_admin/students', methods=['GET', 'POST'])
def manage_students():
    if 'school_admin_id' not in session:
        return redirect(url_for('school_admin_login'))

    school_id = session['school_admin_id']

    if request.method == 'POST':
        name = request.form['name']
        class_id = request.form['class_id']
        username = request.form['username']
        raw_password = request.form['password']
        password_hash = generate_password_hash(raw_password)

        # Check if username already exists
        existing = supabase.table('students').select('id').eq('username', username).execute()
        if existing.data and len(existing.data) > 0:
            flash("⚠️ Username already exists.", "error")
        else:
            supabase.table('students').insert({
                "name": name,
                "class_id": class_id,
                "username": username,
                "password": raw_password,          # optional: for internal use
                "password_hash": password_hash,    # secure login
                "school_id": school_id
            }).execute()
            flash("✅ Student added successfully.", "success")

        return redirect('/school_admin/students')

    # ✅ Fetch students with joined class info
    students = supabase.table('students').select(
        'id, name, username, class_id, classes(class_name, class_level)'
    ).eq('school_id', school_id).execute().data

    # ✅ Fetch only this school's classes
    classes = supabase.table('classes').select("id, class_name, class_level").eq("school_id", school_id).execute().data

    return render_template('manage_students.html', students=students, classes=classes)

@app.route('/school_teacher/view_students')
def view_students_by_class_teacher():
    if 'school_teacher_id' not in session:
        return redirect('/school_teacher/login')

    teacher_id = session['school_teacher_id']

    # ✅ Get teacher data
    teacher_result = supabase.table("school_teachers").select("*").eq("id", teacher_id).single().execute()
    teacher = teacher_result.data

    if not teacher:
        return "Teacher not found", 404

    school_id = teacher.get("school_id")

    # ✅ Get assigned class_id from class_teacher_mappings table
    mapping_result = supabase.table("class_teacher_mappings") \
        .select("class_id, class_level") \
        .eq("teacher_id", teacher_id) \
        .eq("school_id", school_id) \
        .single() \
        .execute()

    if not mapping_result.data:
        return "No class mapping found for this teacher", 404

    class_id = mapping_result.data["class_id"]
    class_level = mapping_result.data["class_level"]

    # ✅ Fetch students using UUID class_id and school_id
    students_result = supabase.table("students") \
        .select("*") \
        .eq("class_id", class_id) \
        .eq("school_id", school_id) \
        .execute()
    students_data = students_result.data

    # ✅ Fetch coin totals for all students
    coin_result = supabase.table("student_coins").select("*").execute()
    coin_data = coin_result.data
    coin_map = {item['student_id']: item['total_coins'] for item in coin_data}

    # ✅ Merge coin totals into student list
    for s in students_data:
        s['total_coins'] = coin_map.get(s['id'], 0)

    # ✅ Render the view with coin-enriched students
    return render_template(
        "school_teacher/view_students.html",
        students=students_data,
        class_name=class_level  # instead of assigned_class
    )

@app.route('/school_teacher/leave_requests')
def school_teacher_leave_requests():
    if 'school_teacher_id' not in session:
        return redirect(url_for('school_teacher_login'))

    teacher_id = session['school_teacher_id']

    # Step 1: Get class assigned to this teacher
    mapping = supabase.table("class_teacher_mappings") \
        .select("class_id") \
        .eq("teacher_id", teacher_id) \
        .single().execute().data

    if not mapping:
        return "No class assigned to this teacher.", 403

    class_id = mapping['class_id']

    # Step 2: Get students in that class
    students = supabase.table("students").select("id").eq("class_id", class_id).execute().data
    student_ids = [s["id"] for s in students]

    # Step 3: Get leave requests
    if student_ids:
        leave_requests = supabase.table("leave_requests") \
            .select("*") \
            .in_("requester_id", student_ids) \
            .eq("role", "student") \
            .order("created_at", desc=True) \
            .execute().data
    else:
        leave_requests = []

    return render_template("school_teacher_leave_requests.html", leave_requests=leave_requests)

@app.route('/school_teacher/leave_requests')
def view_leave_requests():
    if 'school_teacher_id' not in session:
        return redirect(url_for('school_teacher_login'))

    teacher_id = session['school_teacher_id']

    # ✅ Step 1: Get class ID from class_teacher_mappings
    mapping = supabase.table("class_teacher_mappings") \
        .select("class_id") \
        .eq("school_teacher_id", teacher_id) \
        .single().execute().data

    if not mapping:
        return "No class assigned to this teacher.", 403

    class_id = mapping['class_id']

    # ✅ Step 2: Get students in that class
    students = supabase.table("students").select("id").eq("class_id", class_id).execute().data
    student_ids = [s["id"] for s in students]

    # ✅ Step 3: Get leave requests by those students
    if student_ids:
        leave_requests = supabase.table("leave_requests") \
            .select("*") \
            .in_("requester_id", student_ids) \
            .eq("role", "student") \
            .order("created_at", desc=True) \
            .execute().data
    else:
        leave_requests = []

    return render_template("teacher_leave_requests.html", leave_requests=leave_requests)

@app.route('/class_teacher/update_leave/<leave_id>', methods=['POST'])
def update_leave_status(leave_id):
    if 'school_teacher_id' not in session:
        return redirect(url_for('school_teacher_login'))

    status = request.form['status']
    remarks = request.form.get('remarks', '')

    supabase.table("leave_requests").update({
        'status': status,
        'remarks': remarks
    }).eq("id", leave_id).execute()

    return redirect(url_for('class_teacher_leave_requests'))

@app.route('/school_teacher/give_reward', methods=['POST'])
def give_reward():
    if 'school_teacher_id' not in session:
        return redirect(url_for('school_teacher_login'))

    teacher_id = session['school_teacher_id']
    teacher = supabase.table('school_teachers').select("*").eq('id', teacher_id).single().execute().data
    assigned_class = teacher['assigned_class']
    school_id = teacher['school_id']

    student_id = request.form['student_id']
    coins = int(request.form['coins'])
    reason = request.form['reason']

    # Step 1: Insert coin reward
    supabase.table('coin_rewards').insert({
        'student_id': student_id,
        'teacher_id': teacher_id,
        'amount': coins,
        'reason': reason
    }).execute()

    # Step 2: Update or Insert student total coins
    existing = supabase.table('student_coins').select("*").eq('student_id', student_id).execute().data

    if existing:
        current = existing[0]['total_coins']
        new_total = current + coins

        supabase.table('student_coins').update({
            'total_coins': new_total
        }).eq('student_id', student_id).execute()
    else:
        supabase.table('student_coins').insert({
            'student_id': student_id,
            'total_coins': coins
        }).execute()

    # ✅ After reward, redirect back to view_students
    return redirect(url_for('view_students_by_class_teacher'))

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

@app.route('/student_login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        # Step 1: Find student by username
        response = supabase.table('students').select('*').eq('username', username).limit(1).execute()
        student_data = response.data

        if not student_data or len(student_data) == 0:
            return render_template('student_login.html', error="❌ Invalid username or password")

        student = student_data[0]

        # Step 2: Check school exists
        school_response = supabase.table('schools').select('*').eq('id', student.get('school_id')).limit(1).execute()
        school_data = school_response.data

        if not school_data or len(school_data) == 0:
            return render_template('student_login.html', error="❌ School info not found")

        school = school_data[0]
        today = datetime.date.today()

        # Step 3: Validate school payment
        if school.get('payment_status') != 'active':
            return render_template('student_login.html', error="❌ Access Denied. School has not paid.")

        if school.get('next_due_date'):
            try:
                due_date = datetime.datetime.strptime(school['next_due_date'], '%Y-%m-%d').date()
                if today > due_date:
                    return render_template('student_login.html', error="❌ School subscription expired.")
            except ValueError:
                return render_template('student_login.html', error="❌ Invalid school due date format.")

        # Step 4: Match plain-text password (no hashing)
        if student.get('password') == password:
            session['student_id'] = student['id']
            session['school_id'] = student['school_id']
            session['student_name'] = student.get('name', 'Student')
            session['student_class'] = student.get('class_level', 'N/A')
            session['school_name'] = school.get('name', 'Your School')
            session['role'] = 'student'
            return redirect(url_for('dashboard'))

        return render_template('student_login.html', error="❌ Invalid credentials")

    return render_template('student_login.html')

@app.route('/student/submit_leave', methods=['GET', 'POST'])
def student_submit_leave():
    if 'student_id' not in session:
        return redirect(url_for('student_login'))

    student_id = session['student_id']

    # Fetch student data
    response = supabase.table("students").select("*").eq("id", student_id).single().execute()
    student_data = response.data

    # Safety checks
    if not student_data:
        return "❌ Student record not found in database.", 404
    if not student_data.get("class_id"):
        return "❌ Your class is not assigned. Contact your school to update it.", 400
    if not student_data.get("school_id"):
        return "❌ Your school is not assigned. Contact your school to update it.", 400

    class_id = student_data['class_id']
    school_id = student_data['school_id']

    if request.method == 'POST':
        from_date = request.form.get('from_date')
        to_date = request.form.get('to_date')
        reason = request.form.get('reason')

        # Basic validation
        if not from_date or not to_date or not reason:
            return "❌ All fields are required.", 400

        leave_data = {
            'student_id': student_id,
            'class_id': class_id,
            'school_id': school_id,
            'from_date': from_date,
            'to_date': to_date,
            'reason': reason,
            'status': 'pending'
        }

        supabase.table("leave_requests").insert(leave_data).execute()
        return redirect(url_for('student_dashboard'))

    return render_template('student/submit_leave.html', student=student_data)

@app.route('/student/leave_status')
def student_leave_status():
    if 'student_id' not in session:
        return redirect('/student/login')

    student_id = session['student_id']

    leaves = supabase.table("leave_requests")\
        .select("*")\
        .eq("student_id", student_id)\
        .order("submitted_at", desc=True)\
        .execute()

    return render_template("student_leave_status.html", leaves=leaves.data)

@app.route('/redeem', methods=['GET', 'POST'])
def redeem_coins():
    if 'student_id' not in session:
        return redirect(url_for('student_login'))

    student_id = session['student_id']
    
    # Get current total coins
    coin_response = supabase.table('student_coins').select("total_coins").eq("student_id", student_id).limit(1).execute()
    coin_data = coin_response.data[0] if coin_response.data else None
    total_coins = coin_data['total_coins'] if coin_data else 0
    message = None

    if request.method == 'POST':
        try:
            amount = int(request.form.get('amount'))
        except (ValueError, TypeError):
            amount = 0

        if amount <= 0:
            message = "Please enter a valid number of coins."
        elif amount > total_coins:
            message = "You do not have enough coins."
        else:
            # Deduct coins
            new_total = total_coins - amount
            supabase.table('student_coins').update({"total_coins": new_total}).eq("student_id", student_id).execute()
            message = f"You have successfully redeemed {amount} coins!"

            # Optional: log the redemption (e.g., in a `redemptions` table)

            total_coins = new_total  # Update for re-rendering

    return render_template('redeem.html', total_coins=total_coins, message=message)

# This shows the edit profile page (GET)
@app.route('/edit_student_profile', methods=['GET'])
def show_edit_student_profile():
    if 'student_id' not in session:
        return redirect(url_for('student_login'))

    student_id = session['student_id']

    # Get the current student data
    student = supabase.table('students').select("*").eq("id", student_id).single().execute().data

    return render_template('edit_student_profile.html', student=student)

@app.route('/edit_student_profile', methods=['POST'])
def edit_student_profile():
    if 'student_id' not in session:
        return redirect(url_for('student_login'))

    student_id = session['student_id']
    new_image_url = request.form.get('image_url', '').strip()

    # Update profile picture in Supabase
    try:
        supabase.table("students").update({"profile_pic": new_image_url}).eq("id", student_id).execute()
        flash("Profile picture updated successfully!", "success")
    except Exception as e:
        flash("Failed to update profile picture.", "error")
        print("Error updating profile:", e)

    return redirect(url_for('dashboard'))

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

from flask import render_template, request
import requests

@app.route("/chalkboard_notes", methods=["GET", "POST"])
def chalkboard_notes():
    notes = None
    topic = ""
    subject = ""
    class_value = ""
    chalkboard_notes = ""
    explanation_notes = ""

    if request.method == "POST":
        topic = request.form.get("topic", "").strip()
        subject = request.form.get("subject", "").strip()
        class_value = request.form.get("class", "").strip()

        if topic and subject and class_value:
            prompt = f"""
You are a helpful teacher preparing chalkboard notes for Tamil Nadu or CBSE board.

- Topic: {topic}
- Class: {class_value}
- Subject: {subject}

Write the explanation like it should be written on a classroom blackboard:
- Bullet points or small sentences
- Use simple English (Tamil-English if useful)
- Include key formulas/definitions
- Add 1 solved example (if applicable)
- Keep it clean and board-friendly.

✏️ Chalkboard Notes:

---

Now, help the teacher explain this topic better to weak students.

🧠 Better Explanation Guide:
- Use a simplified explanation in Tamil-English
- Add a real-life example
- Mention a common misunderstanding and how to correct it
"""

            headers = {
                "Authorization": f"Bearer {DOUBT_SOLVER_API_KEY}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": DOUBT_SOLVER_MODEL,
                "prompt": prompt,
                "max_tokens": 300,
                "temperature": 0.6
            }

            try:
                response = requests.post(
                    "https://api.together.xyz/v1/completions",
                    headers=headers,
                    json=payload
                )
                if response.status_code == 200:
                    data = response.json()
                    notes = data.get("choices", [{}])[0].get("text", "").strip()
                else:
                    notes = "⚠️ AI is currently unavailable. Please try again."
            except Exception as e:
                notes = f"⚠️ Error: {str(e)}"

        # Split into chalkboard and explanation notes
        if notes and "---" in notes:
            chalkboard_notes, explanation_notes = notes.split("---", 1)
        else:
            chalkboard_notes = notes
            explanation_notes = ""

    return render_template(
        "chalkboard_notes.html",
        notes=notes,
        topic=topic,
        subject=subject,
        class_value=class_value,
        chalkboard_notes=chalkboard_notes.strip() if chalkboard_notes else "",
        explanation_notes=explanation_notes.strip() if explanation_notes else ""
    )

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
    slot_id = request.args.get('slot_id')
    teacher_id = request.args.get('teacher_id')
    payment_id = request.args.get('payment_id')

    slot_data = None
    teacher_data = None

    if slot_id:
        slot_resp = supabase.table("available_slots").select("*").eq("id", slot_id).single().execute()
        slot_data = slot_resp.data if slot_resp.data else None

    if teacher_id:
        teacher_resp = supabase.table("teachers").select("*").eq("id", teacher_id).single().execute()
        teacher_data = teacher_resp.data if teacher_resp.data else None

    return render_template(
        'booking_success.html',
        meet_link=meet_link,
        slot=slot_data,
        teacher=teacher_data,
        payment_id=payment_id
    )


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
        image_url = request.form.get('image_url', '').strip()
        bio = request.form.get('bio', '').strip()
        experience = request.form.get('experience', '').strip()

        supabase.table("teachers").update({
            "image_url": image_url,
            "bio": bio,
            "experience": experience
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

You can log in here: https://testifyy.online/school_teacher/login

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

    # 🔹 Fetch all bookings
    bookings_res = supabase.table("bookings").select("*").order("created_at", desc=True).execute()
    bookings_data = bookings_res.data

    # 🔹 Fetch only teachers used in bookings
    teacher_ids = list({b["teacher_id"] for b in bookings_data if b.get("teacher_id")})
    teachers_map = {}
    if teacher_ids:
        teachers_res = supabase.table("teachers").select("id, name, subject").in_("id", teacher_ids).execute()
        teachers_map = {t["id"]: t for t in teachers_res.data}

    # 🔹 Attach only teacher info
    for b in bookings_data:
        teacher = teachers_map.get(b.get("teacher_id"), {})
        b["teacher_name"] = teacher.get("name", "Unknown")
        b["subject"] = teacher.get("subject", "Unknown")
        b["booked_at"] = b.get("created_at", "")[:16]  # optional datetime display

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
        student_name = request.form.get('student_name', '').strip()
        rating_str = request.form.get('rating', '').strip()
        comment = request.form.get('comment', '').strip()

        # Validate rating
        if not rating_str.isdigit():
            return render_template('review_form.html', teacher=teacher_data, error="❌ Please select a valid rating.")

        rating = int(rating_str)

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
        total_rating = sum([r.get('rating', 0) for r in reviews])
        average_rating = round(total_rating / total_reviews, 2) if total_reviews > 0 else 0.0

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
        return redirect(url_for('booking_success'))

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

from flask import Flask, render_template, request
from supabase_client import supabase  # your Supabase client setup

@app.route("/smartlab")
def smartlab():
    selected_class = request.args.get('class', '').strip()
    selected_subject = request.args.get('subject', '').strip()
    search_query = request.args.get('q', '').lower().strip()

    query = supabase.table("smartlab_experiments").select("*")

    if selected_class:
        query = query.eq("class", selected_class)
    if selected_subject:
        query = query.eq("subject", selected_subject)

    response = query.execute()
    data = response.data or []

    if search_query:
        data = [d for d in data if search_query in d['title'].lower()]

    return render_template("smartlab.html", experiments=data)

@app.route('/health')
def health():
    return "OK"
