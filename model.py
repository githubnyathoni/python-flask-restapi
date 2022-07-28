from app import db
import datetime

class EmployeesModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100))
    password = db.Column(db.String(100))

    def save(self):
        try:
            db.session.add(self)
            db.session.commit()
            return True
        except:
            return False

class ActivityModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("employees_model.id"))
    activity_name = db.Column(db.String(100))
    activity_date = db.Column(db.Date, default=datetime.date.today())
    activity_status = db.Column(db.Integer)

    def save(self):
        try:
            db.session.add(self)
            db.session.commit()
            return True
        except:
            return False

class AttendanceModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("employees_model.id"))
    checkin = db.Column(db.DateTime)
    checkout = db.Column(db.DateTime)

    def save(self):
        try:
            db.session.add(self)
            db.session.commit()
            return True
        except:
            return False

class TokenBlocklist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    jwt = db.Column(db.String(100), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False)

    def save(self):
        try:
            db.session.add(self)
            db.session.commit()
            return True
        except:
            return False

db.create_all()