from flask import Flask, flash, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename
import os, sqlite3, random, string, json

upload_folder = "static/uploads"
app = Flask(__name__)
app.secret_key = "super_secret_key_123"
app.config["UPLOAD_FOLDER"] = upload_folder
if not os.path.exists(upload_folder):
    os.makedirs(upload_folder)

def create_tables():
    conn = sqlite3.connect("users_v2.db")
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,email TEXT,  password TEXT, role TEXT
        );
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT, objectives TEXT, project_code TEXT UNIQUE,
            created_by TEXT, status TEXT DEFAULT 'Active',
            created_at TEXT, deadline TEXT, team_lead TEXT
        );
        CREATE TABLE IF NOT EXISTS project_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_code TEXT, username TEXT, role TEXT
        );
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_code TEXT, assigned_to TEXT, assigned_by TEXT,
            task_title TEXT, status TEXT DEFAULT 'Pending', file_name TEXT
        );
        CREATE TABLE IF NOT EXISTS evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_code TEXT, student_username TEXT,
            week_number INTEGER, marks INTEGER, marked_by TEXT
        );
    """)
    conn.commit()
    conn.close()

create_tables()

def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/signup", methods=["GET","POST"])
def signup():
    if request.method == "POST":
        u = request.form.get("username","").strip()
        p = request.form.get("password","").strip()
        r = request.form.get("role","").strip()
        conn = sqlite3.connect("users_v2.db")
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username,password,role) VALUES (?,?,?)",(u,p,r))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return render_template("signup.html", error="Username already exists!")
        conn.close()
        return redirect("/login")
    return render_template("signup.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form["username"].strip()
        p = request.form["password"].strip()
        r = request.form["role"].strip().lower()
        conn = sqlite3.connect("users_v2.db")
        c = conn.cursor()
        c.execute("SELECT username, role FROM users WHERE username=? AND password=? AND LOWER(role)=?",(u,p,r))
        user = c.fetchone()
        conn.close()
        if user:
            session["username"] = user[0]
            session["role"] = user[1]
            if r == "teamlead":
                return redirect(url_for("create_project"))
            else:
                return redirect(url_for("open_project"))
        return render_template("login.html", error="Invalid username, password or role")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/create_project", methods=["GET","POST"])
def create_project():
    if "username" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        name = request.form.get("project_name","").strip()
        obj  = request.form.get("objectives","").strip()
        code = generate_code()
        conn = sqlite3.connect("users_v2.db")
        c = conn.cursor()
        c.execute("INSERT INTO projects (project_name,objectives,project_code,created_by) VALUES (?,?,?,?)",
                  (name, obj, code, session["username"]))
        conn.commit()
        conn.close()
        return render_template("teamlead.html", success=True, project_code=code)
    return render_template("teamlead.html")

@app.route("/open_project", methods=["GET","POST"])
def open_project():
    if "username" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        code = request.form.get("project_code","").strip()
        conn = sqlite3.connect("users_v2.db")
        c = conn.cursor()
        # Match project code case-insensitively
        c.execute("SELECT project_name, project_code FROM projects WHERE UPPER(project_code)=UPPER(?)",(code,))
        row = c.fetchone()
        if not row:
            conn.close()
            return render_template("open_project.html", error="Invalid Project ID. Please check and try again.")
        real_code = row[1]  # use the code exactly as stored in DB
        session["project_code"] = real_code
        session["project_name"] = row[0]
        uname = session.get("username")
        role  = session.get("role")
        c.execute("SELECT 1 FROM project_members WHERE project_code=? AND username=?",(real_code, uname))
        if not c.fetchone():
            c.execute("INSERT INTO project_members (project_code,username,role) VALUES (?,?,?)",
                      (real_code, uname, role))
            conn.commit()
        conn.close()
        return redirect(url_for("project_overview", project_code=real_code))
    return render_template("open_project.html")

@app.route("/project/<project_code>")
def project_overview(project_code):
    if "username" not in session:
        return redirect(url_for("login"))
    role = session.get("role")
    conn = sqlite3.connect("users_v2.db")
    c = conn.cursor()
    c.execute("SELECT project_name, created_by, project_code, objectives FROM projects WHERE project_code=?",
              (project_code,))
    row = c.fetchone()
    if not row:
        conn.close()
        return "Project not found", 404
    c.execute("SELECT username, role FROM project_members WHERE project_code=?", (project_code,))
    members = c.fetchall()
    conn.close()
    project = {
        "project_code": row[2],
        "project_name": row[0],
        "team_lead":    row[1],
        "objectives":   row[3],
        "team_members": members
    }
    return render_template("project_overview.html", project=project, role=role, team_members=members)

@app.route("/assign_tasks/<project_code>", methods=["GET","POST"])
def assign_tasks(project_code):
    if "username" not in session:
        return redirect(url_for("login"))
    conn = sqlite3.connect("users_v2.db")
    c = conn.cursor()
    if request.method == "POST":
        if "assign_task" in request.form:
            student = request.form["username"]
            tasks   = request.form.getlist("task[]")
            for task in tasks:
                if task.strip():
                    c.execute("INSERT INTO tasks (project_code,assigned_to,assigned_by,task_title,status) VALUES (?,?,?,?,?)",
                              (project_code, student, session["username"], task.strip(), "Pending"))
            conn.commit()
        if "delete_task" in request.form:
            c.execute("DELETE FROM tasks WHERE id=?", (request.form["task_id"],))
            conn.commit()
    c.execute("""SELECT username FROM project_members
                 WHERE project_code=? AND LOWER(role) NOT IN ('teamlead','teacher','admin')""",
              (project_code,))
    students = c.fetchall()
    c.execute("SELECT assigned_to, task_title, id, status FROM tasks WHERE project_code=?", (project_code,))
    all_tasks = c.fetchall()
    conn.close()
    return render_template("assign_tasks.html", students=students, all_tasks=all_tasks, project_code=project_code)

@app.route("/student_tasks/<project_code>", methods=["GET","POST"])
def student_tasks(project_code):
    if "username" not in session:
        return redirect(url_for("login"))
    uname = session["username"]
    if request.method == "POST":
        task_id = request.form.get("task_id")
        file    = request.files.get("file")
        if file and file.filename:
            filename = secure_filename(file.filename)
            # Allow ALL file types — just save with secure name
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            conn = sqlite3.connect("users_v2.db")
            c = conn.cursor()
            c.execute("UPDATE tasks SET file_name=?, status='Completed' WHERE id=?", (filename, task_id))
            conn.commit()
            conn.close()
            flash("Task marked as complete!")
    conn = sqlite3.connect("users_v2.db")
    c = conn.cursor()
    c.execute("SELECT id, task_title, status, file_name FROM tasks WHERE assigned_to=? AND project_code=?",
              (uname, project_code))
    tasks = c.fetchall()
    conn.close()
    return render_template("student_tasks.html", tasks=tasks, username=uname)

@app.route("/view_tasks/<project_code>/<username>")
def view_tasks(project_code, username):
    conn = sqlite3.connect("users_v2.db")
    c = conn.cursor()
    c.execute("SELECT task_title, status, file_name FROM tasks WHERE project_code=? AND assigned_to=?",
              (project_code, username))
    tasks = c.fetchall()
    conn.close()
    return render_template("view_tasks.html", tasks=tasks, username=username)

# ── TRACK PROGRESS ──
AV = ['av1','av2','av3','av4','av5']

@app.route('/track_progress', methods=['GET','POST'])
def track_progress():
    code = (request.form.get("project_code") or request.args.get("project_code") or "").strip()

    conn = sqlite3.connect("users_v2.db")
    c    = conn.cursor()

    # Get project info — match exactly as stored
    c.execute("SELECT project_name, deadline FROM projects WHERE project_code=?", (code,))
    proj = c.fetchone()
    # If not found, try case-insensitive
    if not proj:
        c.execute("SELECT project_name, deadline, project_code FROM projects WHERE UPPER(project_code)=UPPER(?)", (code,))
        row = c.fetchone()
        if row:
            proj = row
            code = row[2]  # use real stored code

    project_name = proj[0] if proj else "Unknown"
    deadline     = proj[1] if proj and proj[1] else ""

    # Get students — exact code match first
    c.execute("""SELECT id, username, role FROM project_members
                 WHERE project_code=?
                 AND LOWER(role) NOT IN ('teamlead','teacher','admin')
                 ORDER BY id ASC""", (code,))
    members = c.fetchall()

    # Fallback: get all members if no students
    if not members:
        c.execute("SELECT id, username, role FROM project_members WHERE project_code=? ORDER BY id ASC", (code,))
        members = c.fetchall()

    students_list = []
    for i, m in enumerate(members):
        uid, uname, urole = m
        c.execute("SELECT COUNT(*) FROM tasks WHERE project_code=? AND assigned_to=?", (code, uname))
        assigned = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM tasks WHERE project_code=? AND assigned_to=? AND LOWER(status)='completed'",
                  (code, uname))
        done = c.fetchone()[0]

        # Load saved marks from evaluations table - get all weeks
        c.execute("SELECT week_number, marks FROM evaluations WHERE project_code=? AND student_username=? ORDER BY week_number ASC",
                  (code, uname))
        eval_rows = c.fetchall()
        marks_dict = {r[0]: r[1] for r in eval_rows}
        # Get last 2 weeks of marks for display
        weeks = sorted(marks_dict.keys())
        wk6 = marks_dict.get(weeks[0], 0) if len(weeks) > 0 else 0
        wk7 = marks_dict.get(weeks[1], 0) if len(weeks) > 1 else (marks_dict.get(weeks[0], 0) if len(weeks) > 0 else 0)

        initials = (uname[0]+uname[-1]).upper() if len(uname)>=2 else uname[:2].upper()
        students_list.append({
            "id": uname, "name": uname, "initials": initials,
            "avClass": AV[i%5], "role": urole or "student",
            "joinedAt": "", "tasksAssigned": assigned,
            "tasksCompleted": done, "tasksOverdue": 0,
            "marks": {"wk6": wk6, "wk7": wk7}
        })

    c.execute("""SELECT id, assigned_to, task_title, file_name FROM tasks
                 WHERE project_code=? AND LOWER(status)='completed'
                 ORDER BY id DESC""", (code,))
    tasks_list = []
    for idx, t in enumerate(c.fetchall()):
        tasks_list.append({
            "id": idx+1, "sid": t[1], "task": t[2],
            "date": "", "tag": "Task", "screenshot": t[3] or ""
        })

    conn.close()

    total     = sum(s["tasksAssigned"]  for s in students_list)
    completed = sum(s["tasksCompleted"] for s in students_list)
    progress  = int((completed/total)*100) if total > 0 else 0

    return render_template("track_progress.html",
        project_code  = code,
        project_name  = project_name,
        deadline      = deadline,
        session_role  = session.get("role","teamlead"),
        students_json = json.dumps(students_list),
        tasks_json    = json.dumps(tasks_list),
        progress      = progress,
        completed     = completed,
        total         = total,
    )

@app.route("/set_deadline", methods=["POST"])
def set_deadline():
    code = request.form.get("project_code","").strip()
    dl   = request.form.get("deadline","").strip()
    conn = sqlite3.connect("users_v2.db")
    c    = conn.cursor()
    c.execute("UPDATE projects SET deadline=? WHERE project_code=?", (dl, code))
    conn.commit()
    conn.close()
    return redirect(url_for("track_progress", project_code=code))

@app.route("/save_mark", methods=["POST"])
def save_mark():
    project_code     = request.form.get("project_code","").strip()
    student_username = request.form.get("student_username","").strip()
    week_number      = int(request.form.get("week_number","1"))
    marks            = int(request.form.get("marks","0"))
    marked_by        = session.get("username","teacher")
    conn = sqlite3.connect("users_v2.db")
    c    = conn.cursor()
    c.execute("SELECT id FROM evaluations WHERE project_code=? AND student_username=? AND week_number=?",
              (project_code, student_username, week_number))
    row = c.fetchone()
    if row:
        c.execute("UPDATE evaluations SET marks=?, marked_by=? WHERE id=?", (marks, marked_by, row[0]))
    else:
        c.execute("INSERT INTO evaluations (project_code,student_username,week_number,marks,marked_by) VALUES (?,?,?,?,?)",
                  (project_code, student_username, week_number, marks, marked_by))
    conn.commit()
    conn.close()
    return json.dumps({"status":"ok"})

@app.route("/admin", methods=["GET","POST"])
def admin():
    conn = sqlite3.connect("users_v2.db")
    c    = conn.cursor()
    if request.method == "POST":
        try:
            c.execute("INSERT INTO projects (project_name,project_code,deadline,status) VALUES (?,?,?,'ongoing')",
                      (request.form.get("project_name"), request.form.get("project_code"), request.form.get("deadline")))
            conn.commit()
        except: pass
    c.execute("SELECT project_name, project_code, deadline FROM projects")
    projects = c.fetchall()
    conn.close()
    return render_template("admin.html", projects=projects)

@app.route("/remove_member", methods=["POST"])
def remove_member():
    if "username" not in session or session.get("role") != "teamlead":
        return json.dumps({"status": "error", "message": "Unauthorized"})
    username     = request.form.get("username", "").strip()
    project_code = request.form.get("project_code", "").strip()
    if not username or not project_code:
        return json.dumps({"status": "error", "message": "Missing data"})
    conn = sqlite3.connect("users_v2.db")
    c    = conn.cursor()
    # Remove from project_members
    c.execute("DELETE FROM project_members WHERE project_code=? AND username=? AND LOWER(role) NOT IN ('teamlead')",
              (project_code, username))
    # Also delete their tasks in this project
    c.execute("DELETE FROM tasks WHERE project_code=? AND assigned_to=?",
              (project_code, username))
    conn.commit()
    conn.close()
    return json.dumps({"status": "ok"})

@app.route('/certificate')
def certificate():
    student = request.args.get('student', '')
    project = request.args.get('project', '')
    code    = request.args.get('code', '')
    return render_template('certificate.html',
                           student_name=student,
                           project_name=project,
                           project_code=code)

@app.route('/student')
def student():
    return render_template('student.html')

@app.route('/teacher')
def teacher():
    return render_template('teacher.html')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
