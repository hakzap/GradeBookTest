from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask import Flask, redirect, render_template, request, url_for
from flask_login import login_user, LoginManager, UserMixin, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from mysql import connector

app = Flask(__name__)
app.config["DEBUG"] = True

# in order to connect to the database:
SQLALCHEMY_DATABASE_URI = "mysql+mysqlconnector://{username}:{password}@{hostname}/{databasename}".format(
    username="hakdan",
    password="database",
    hostname="hakdan.mysql.pythonanywhere-services.com",
    databasename="hakdan$Gradebook",
)
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_POOL_RECYCLE"] = 299
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

"""
Next, we need to add a model. A model is a Python class that specifies the stuff that we want to store in the database;
SQLAlchemy handles all of the complexities of loading stuff from and storing stuff in MySQL; the price is that we have to specify in detail exactly what we want.
Here’s the class definition for our model
"""
@login_manager.user_loader
def load_user(entered_name):
    return User.query.filter_by(user_name=entered_name).first()


# Routes
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template("main_page.html")
    if not current_user.is_authenticated:
        return redirect(url_for("index"))
    return redirect(url_for("index"))


@app.route("/login/", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login_page.html", error=False)

    user = load_user(request.form["username"])
    if user is None:
        return render_template("login_page.html", error=True)

    if not user.check_password(request.form["password"]):
        return render_template("login_page.html", error=True)

    login_user(user)
    return redirect(url_for("index"))


@app.route("/create/", methods=["GET", "POST"])
def create():
    if request.method == "GET":
        return render_template("create_login.html", error=False)

    if current_user.is_authenticated:
        return render_template("create_login.html", current_user_error=True)

    user = load_user(request.form["username"])
    if user:
        return render_template("create_login.html", duplicate_user_error=True)

    if request.form.get("password") != request.form.get("password_confirm"):
        return render_template("create_login.html", password_error=True)

    new_user = User()
    new_user.user_name = request.form["username"]
    new_user.password_hash = generate_password_hash(request.form["password"])
    db.session.add(new_user)
    db.session.commit()

    login_user(new_user)
    return render_template("create_login.html", account_success=True)


@app.route("/logout/")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/students/", methods=["GET"])
@login_required
def student():
    if request.method == "GET":
        # Subquery to get aggregate grade for students, assuming equal weighting.
        student_return_inner = db.session.query(
            Student.student_ID,
            (db.func.round((db.func.sum(Grade.grade)/db.func.count(Grade.grade)),3)).label(
             "agg_grade")).select_from(Student).join(Grade).group_by(Student.student_ID).subquery()

        student_return = db.session.query(
            Student.student_ID,
            Student.first_name,
            Student.last_name,
            Student.major,
            Student.email_address,
            student_return_inner.c.agg_grade).select_from(Student).join(student_return_inner,
                student_return_inner.c.student_ID == Student.student_ID, isouter=True).order_by(Student.first_name)

        return render_template("students.html", student_display=student_return)
    else:
        return redirect(url_for("index"))


@app.route("/assignments/", methods=["GET"])
@login_required
def assignment():
    if request.method == "GET":
        return render_template("assignments.html", assignment_display=Assignment.query.all())
    else:
        return redirect(url_for("index"))


@app.route("/create_student/", methods=["GET", "POST"])
@login_required
def create_student():
    if request.method == "GET":
        return render_template("create_student.html")

    new_student = Student()
    new_student.first_name = request.form["first_name"]
    new_student.last_name = request.form["last_name"]
    new_student.email_address = request.form["email_address"]
    new_student.major = request.form["major"]
    db.session.add(new_student)
    db.session.commit()

    return render_template("create_student.html", create_success=True)


@app.route("/edit_student/", methods=["GET", "POST"])
@app.route("/edit_student/<int:edit_ID>", methods=["GET", "POST"])
@login_required
def edit_student(edit_ID=None):
    if request.method == "GET":
        if edit_ID is not None:
            student_return = db.session.query(
                Student.student_ID,
                Student.first_name,
                Student.last_name,
                Student.email_address,
                Student.major).select_from(Student).filter(Student.student_ID == edit_ID).first()

            return render_template("edit_student.html", student_display=student_return)
        else:
            return render_template("edit_student.html", student_display="")

    ed_student = Student.query.filter_by(student_ID=edit_ID).first()
    if ed_student is None:
        return render_template("edit_student.html", edit_fail=True)

    ed_student.first_name = request.form["first_name"]
    ed_student.last_name = request.form["last_name"]
    ed_student.email_address = request.form["email_address"]
    ed_student.major = request.form["major"]
    db.session.add(ed_student)
    db.session.commit()

    return render_template("edit_student.html", edit_success=True)


@app.route("/delete_student/", methods=["GET", "POST"])
@app.route("/delete_student/<delete_ID>", methods=["GET", "POST"])
@login_required
def delete_student(delete_ID=None):
    if request.method == "GET":
        if delete_ID is not None:
            student_return = db.session.query(
                Student.student_ID,
                Student.first_name,
                Student.last_name,
                Student.email_address,
                Student.major).select_from(
                Student).filter(Student.student_ID == delete_ID).first()

            return render_template("delete_student.html", student_display=student_return)
        else:
            return render_template("delete_student.html", student_display="")

    del_student = Student.query.filter_by(student_ID=delete_ID).first()
    if del_student is None:
        return render_template("delete_student.html", delete_fail=True)
    db.session.delete(del_student)
    db.session.commit()

    return render_template("delete_student.html", delete_success=True)


@app.route("/assignment_grades/", methods=["GET"])
@app.route("/assignment_grades/<assign_get_ID>", methods=["GET"])
@login_required
def assignment_grades(assign_get_ID= None):
    if request.method == "GET":
        grade_return_inner = db.session.query(Student.student_ID, Grade.grade, Assignment.assignment_ID,
            Assignment.assignment_name).select_from(Student).join(Grade).\
            join(Assignment).filter_by(assignment_ID=assign_get_ID).subquery()

        assign_get = db.session.query(
            Assignment.assignment_ID,
            Assignment.assignment_name
            ).select_from(Assignment).filter(Assignment.assignment_ID == assign_get_ID).first()

        grade_return = db.session.query(
            grade_return_inner.c.assignment_ID,
            grade_return_inner.c.assignment_name,
            grade_return_inner.c.grade,
            Student.student_ID,
            Student.first_name,
            Student.last_name
            ).select_from(Student).join(grade_return_inner, grade_return_inner.c.student_ID ==
                Student.student_ID, isouter=True).order_by(Student.first_name)

        return render_template("assignment_grades.html", grade_display=grade_return, grade_assignment=assign_get)
    else:
        return redirect(url_for("index"))


@app.route("/create_assignment/", methods=["GET", "POST"])
@login_required
def create_assignment():
    if request.method == "GET":
        return render_template("create_assignment.html")

    new_assignment = Assignment()
    new_assignment.assignment_name = request.form["assignment_name"]
    db.session.add(new_assignment)
    db.session.commit()

    return render_template("create_assignment.html", create_success=True)


@app.route("/edit_assignment/", methods=["GET", "POST"])
@app.route("/edit_assignment/<int:edit_ID>", methods=["GET", "POST"])
@login_required
def edit_assignment(edit_ID=None):
    if request.method == "GET":
        if edit_ID is not None:
            assignment_return = db.session.query(
                Assignment.assignment_ID,
                Assignment.assignment_name
                ).select_from(Assignment).filter(Assignment.assignment_ID == edit_ID).first()

            return render_template("edit_assignment.html", assignment_display=assignment_return)
        else:
            return render_template("edit_assignment.html", assignment_display="")

    ed_assignment = Assignment.query.filter_by(assignment_ID=edit_ID).first()
    if ed_assignment is None:
        return render_template("edit_assignment.html", edit_fail=True)

    ed_assignment.assignment_name = request.form["assignment_name"]
    db.session.add(ed_assignment)
    db.session.commit()

    return render_template("edit_assignment.html", edit_success=True)


@app.route("/delete_assignment/", methods=["GET", "POST"])
@app.route("/delete_assignment/<delete_ID>", methods=["GET", "POST"])
@login_required
def delete_assignment(delete_ID=None):
    if request.method == "GET":
        if delete_ID is not None:
            assignment_return = db.session.query(
                Assignment.assignment_ID,
                Assignment.assignment_name).select_from(
                Assignment).filter(Assignment.assignment_ID == delete_ID).first()

            return render_template("delete_assignment.html", assignment_display=assignment_return)
        else:
            return render_template("delete_assignment.html", assignment_display="")

    del_assignment = Assignment.query.filter_by(assignment_ID=delete_ID).first()
    if del_assignment is None:
        return render_template("delete_assignment.html", delete_fail=True)
    db.session.delete(del_assignment)
    db.session.commit()

    return render_template("delete_assignment.html", delete_success=True)


@app.route("/student_grades/", methods=["GET"])
@app.route("/student_grades/<student_get_ID>", methods=["GET"])
@login_required
def student_grades(student_get_ID= None):
    if request.method == "GET":
        grade_return = db.session.query(
            Assignment.assignment_ID,
            Assignment.assignment_name,
            Grade.student_ID,
            Grade.grade,
            Student.first_name,
            Student.last_name
            ).select_from(Assignment).join(Grade).join(Student).filter(Student.student_ID == student_get_ID)

        student_get = db.session.query(
                Student.student_ID,
                Student.first_name,
                Student.last_name,
                Student.major,
                Student.email_address
                ).select_from(Student).filter(Student.student_ID == student_get_ID).first()

        return render_template("student_grades.html", grade_display=grade_return, student_display=student_get)
    else:
        return redirect(url_for("index"))


@app.route("/create_grade/", methods=["GET"])
@app.route("/create_grade/<assign_get_ID>/<student_get_ID>/", methods=["GET", "POST"])
def create_grade(assign_get_ID=None, student_get_ID=None):
    if request.method == "GET":
        if assign_get_ID is not None and student_get_ID is not None:
            assign_return = db.session.query(
                Assignment.assignment_ID,
                Assignment.assignment_name,
                ).select_from(Assignment).filter(Assignment.assignment_ID == assign_get_ID).first()

            student_return = db.session.query(
                Student.student_ID,
                Student.first_name,
                Student.last_name
                ).select_from(Student).filter(Student.student_ID == student_get_ID).first()

            return render_template("create_grade.html", assignment_display=assign_return,
                                   student_display=student_return)
        else:
            return render_template("create_grade.html", assignment_display="", student_display="", no_ID_error=True)

    new_grade = Grade()
    new_grade.grade = request.form["grade"]
    new_grade.assignment_ID = assign_get_ID
    new_grade.student_ID = student_get_ID
    db.session.add(new_grade)
    db.session.commit()
    # Can't get this to go back to create_grade without weirdly dropping a URL parameter.
    # Can't get this to go back to assignment_grades without the assignment ID, which was giving a routing error
    return redirect(url_for("assignment"))


@app.route("/edit_grade/<assign_get_ID>/<student_get_ID>/", methods=["GET", "POST"])
def edit_grade(assign_get_ID=None, student_get_ID=None):
    if request.method == "GET":
        if assign_get_ID is not None and student_get_ID is not None:
            grade_return = db.session.query(
                Assignment.assignment_ID,
                Assignment.assignment_name,
                Grade.grade,
                Student.student_ID,
                Student.first_name,
                Student.last_name
                ).select_from(Assignment).filter(Assignment.assignment_ID == assign_get_ID,
                                                 Grade.student_ID == student_get_ID,
                                                 Grade.student_ID == Student.student_ID,
                                                 Grade.assignment_ID == Assignment.assignment_ID).first()

            return render_template("edit_grade.html", grade_display=grade_return)
        else:
            return render_template("edit_grade.html", grade_display="", no_ID_error=True)

    ed_grade = Grade.query.filter_by(assignment_ID=assign_get_ID, student_ID=student_get_ID).first()
    if ed_grade is None:
        return render_template("edit_grade.html", edit_fail=True)

    ed_grade.grade = request.form["grade"]
    db.session.add(ed_grade)
    db.session.commit()

    # Can't get this to go back to edit_grade without weirdly dropping a URL parameter.
    # Can't get this to go back to assignment_grades without the assignment ID, which was giving a routing error
    return redirect(url_for("assignment"))


@app.route("/delete_grade/", methods=["GET", "POST"])
@app.route("/delete_grade/<assign_get_ID>/<student_get_ID>/", methods=["GET", "POST"])
@login_required
def delete_grade(assign_get_ID=None, student_get_ID=None):
    if request.method == "GET":
        if assign_get_ID is not None and student_get_ID is not None:
            grade_return = db.session.query(
                Assignment.assignment_ID,
                Assignment.assignment_name,
                Grade.grade,
                Student.student_ID,
                Student.first_name,
                Student.last_name
                ).select_from(Assignment).filter(Assignment.assignment_ID == assign_get_ID,
                                                 Student.student_ID == student_get_ID).first()

            return render_template("delete_grade.html", grade_display=grade_return)
        else:
            return render_template("delete_grade.html", grade_display="", no_ID_error=True)

    del_grade = Grade.query.filter_by(assignment_ID=assign_get_ID, student_ID=student_get_ID).first()
    if del_grade is None:
        return render_template("delete_assignment.html", delete_fail=True)
    db.session.delete(del_grade)
    db.session.commit()

    return render_template("delete_grade.html", delete_success=True)


# Models
class User(UserMixin, db.Model):
    __tablename__ = "user"
    user_id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(128))
    password_hash = db.Column(db.String(128))

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return self.user_name


class Student(db.Model):
    __tablename__ = "student"
    student_ID = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(45))
    last_name = db.Column(db.String(45))
    email_address = db.Column(db.String(45))
    major = db.Column(db.String(45))


class Assignment(db.Model):
    __tablename__ = "assignment"
    assignment_ID = db.Column(db.Integer, primary_key=True)
    assignment_name = db.Column(db.String(128))


class Grade(db.Model):
    __tablename__ = "grade"
    # grade_ID = db.Column(db.Integer, primary_key=True) Artificial primary key, not currently used.
    assignment_ID = db.Column(db.Integer, db.ForeignKey(Assignment.assignment_ID), primary_key=True)
    student_ID = db.Column(db.Integer, db.ForeignKey(Student.student_ID), primary_key=True)
    grade = db.Column(db.Float)
    assignment_grade_constraint = db.relationship("Assignment", foreign_keys=assignment_ID)
    student_grade_constraint = db.relationship("Student", foreign_keys=student_ID)
