from distutils.log import Log
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, request, jsonify, make_response, session
from flask_restful import Resource, Api
from flask_cors import CORS
import datetime
import re
import jwt
import os
import model
from functools import wraps
import pytz


app = Flask(__name__)
api = Api(app)
CORS(app)

db = SQLAlchemy(app)
basedir = os.path.dirname(os.path.abspath(__file__))
database = 'sqlite:///' + os.path.join(basedir, 'db.sqlite')
app.config['SQLALCHEMY_DATABASE_URI'] = database
# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgres://qlgprufzddqgwe:a0c7e120a85b4277822d55fb9c398c390d90a3a5b11d9384b901da691e74df97@ec2-50-19-255-190.compute-1.amazonaws.com:5432/d5hf4lbfmhur8c'
app.config["SECRET_KEY"] = "AIBNEGARA"

def LoginRequired(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        token = request.args.get('token')
        if not token:
            return make_response(jsonify(
                {
                    'status': 401,
                    'msg': "Token is required"
                }
            ), 401)
        else:
            isBlocked = model.TokenBlocklist.query.filter(
            model.TokenBlocklist.jwt==token).first()
            if(isBlocked):
                return make_response(jsonify(
                    {
                        'status': 401,
                        'msg': 'Invalid token credentials.'
                    }
                ), 401)
        try:
            jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            
        except:
            return make_response(jsonify(
                {
                    'status': 401,
                    'msg': 'Invalid token credentials.'
                }
            ), 401)
        return f(*args, **kwargs)
    return decorator


class LoginEmployeeResource(Resource):
    def post(self):
        username = request.form['username']
        password = request.form['password']

        query = model.EmployeesModel.query.filter(
            model.EmployeesModel.username==username,
            model.EmployeesModel.password==password).first()

        if(query):
            token = jwt.encode(
                {
                    'username': username,
                    'exp': datetime.datetime.utcnow() + datetime.timedelta(hours= 2)
                }, app.config["SECRET_KEY"], algorithm="HS256"
            )
            session['is_login'] = True
            session['user_id'] = query.id
            session['jwt'] = token
            return make_response(jsonify(
                {
                    'status': 200,
                    'msg': "Login Successfully",
                    'token': token
                }
            ), 200)
        else:
            return make_response(jsonify(
                {
                    'status': 401,
                    'msg': "Login Unsuccessfully",
                }
            ), 401)

class LogoutEmployeeResource(Resource):
    @LoginRequired
    def post(self):
        token = session['jwt']
        now = datetime.datetime.now(pytz.timezone('Asia/Jakarta'))
        query = model.TokenBlocklist(
            jwt = token,
            created_at = now
        )
        query.save()

        session.clear()

        return make_response(jsonify(
            {
                'status': 200,
                'msg': "Logout Successfully",
            }
        ), 200)


class AttendanceResource(Resource):
    @LoginRequired
    def get(self):
        query = model.AttendanceModel.query.all()
        attendanceData = [
            {
                'id': attendance.id,
                'user_id': attendance.user_id,
                'checkin': attendance.checkin.strftime('%d-%m-%Y %H:%M:%S') if attendance.checkin else 'NULL',
                'checkout': attendance.checkout.strftime('%d-%m-%Y %H:%M:%S') if attendance.checkout else 'NULL',
            }
            for attendance in query
        ]

        return make_response(jsonify(
            {
                'status': 200,
                'msg': 'Successfully get all attendances data',
                'attendances': attendanceData,
            }
        ), 200)
    
    @LoginRequired
    def post(self):
        type = request.form['type']
        if(type == 'checkin'):
            query = model.AttendanceModel.query.filter(
                model.AttendanceModel.checkin>=datetime.date.today(),
                model.AttendanceModel.user_id==session['user_id']).first()
            if(query):
                return make_response(jsonify(
                    {
                        'status': 400,
                        'msg': 'Already checked in today'
                    }
                ), 400)
            else:
                query = model.AttendanceModel(
                    user_id = session['user_id'],
                    checkin = datetime.datetime.now(pytz.timezone('Asia/Jakarta'))
                )
                query.save()

                return make_response(jsonify(
                    {
                        'status': 200,
                        'msg': 'Successfully added checkin data'
                    }
                ), 200)
        elif(type == 'checkout'):
            query = model.AttendanceModel.query.filter(
                model.AttendanceModel.checkin>=datetime.date.today(),
                model.AttendanceModel.user_id==session['user_id'],
                model.AttendanceModel.checkout==None).first()
            if(query):
                checkout = datetime.datetime.now(pytz.timezone('Asia/Jakarta'))

                query.checkout = checkout
                model.db.session.commit()

                return make_response(jsonify(
                    {
                        'status': 200,
                        'msg': 'Successfully added checkout data'
                    }
                ), 200)
            else:
                return make_response(jsonify(
                    {
                        'status': 400,
                        'msg': 'Please check in first'
                    }
                ), 400)
        else:
            return make_response(jsonify(
                {
                    'status': 400,
                    'msg': 'Please input type of attendance'
                }
            ), 400)

class ActivityResource(Resource):
    @LoginRequired
    def get(self):
        query = model.ActivityModel.query.all()
        activityData = [
            {
                'id': activity.id,
                'user_id': activity.user_id,
                'activity_name': activity.activity_name,
                'activity_date': activity.activity_date.strftime('%d-%m-%Y'),
                'activity_status': activity.activity_status,
            }
            for activity in query
        ]

        return make_response(jsonify(
            {
                'status': 200,
                'msg': 'Successfully get all activities data',
                'activities': activityData,
            }
        ), 200)
    
    @LoginRequired
    def post(self):
        checkIn = model.AttendanceModel.query.filter(
        model.AttendanceModel.checkin>=datetime.date.today(),
        model.AttendanceModel.user_id==session['user_id']).first()

        if(checkIn):
            user_id = session['user_id']
        
            if(request.form['activity_name'] and request.form['activity_date'] and request.form['activity_status']):
                activity_name = request.form['activity_name']
                d, m, y = request.form['activity_date'].split('-')
                activity_date = datetime.datetime(int(y), int(m), int(d))
                activity_status  = request.form['activity_status']

                query = model.ActivityModel(
                    user_id = user_id,
                    activity_name = activity_name,
                    activity_date = activity_date,
                    activity_status = activity_status
                )
                query.save()

                return make_response(jsonify(
                    {
                        'status': 200,
                        'msg': 'Successfully added activity data'
                    }
                ), 200)
            else:
                return make_response(jsonify(
                    {
                        'status': 400,
                        'msg': 'All fields are required'
                    }
                ), 400)
        else:
            return make_response(jsonify(
                {
                    'status': 401,
                    'msg': 'Please check in first'
                }
            ), 401)
        

class EmployeeResource(Resource):
    @LoginRequired
    def get(self):
        query = model.EmployeesModel.query.all()
        employeeData = [
            {
                'id': employee.id,
                'username': employee.username,
                'password': employee.password,
            }
            for employee in query
        ]

        return make_response(jsonify(
            {
                'status': 200,
                'msg': 'Successfully get all employees data',
                'employee': employeeData,
            }
        ), 200)
    
    def post(self):
        username = request.form['username']
        password = request.form['password']
        
        isAlready = model.EmployeesModel.query.filter(
            model.EmployeesModel.username == username
        ).first()
        if(not isAlready):
            query = model.EmployeesModel(
                username = username,
                password = password
                )
            query.save()

            return make_response(jsonify(
                {
                    'status': 200,
                    'msg': 'Successfully added employee data'
                }
            ), 200)
        else:
            return make_response(jsonify(
                {
                    'status': 409,
                    'msg': 'User already registered'
                }
            ), 409)

class UpdateDeleteActivityResource(Resource):
    @LoginRequired
    def put(self, id):
        checkIn = model.AttendanceModel.query.filter(
        model.AttendanceModel.checkin>=datetime.date.today(),
        model.AttendanceModel.user_id==session['user_id']).first()

        if(checkIn):
            query = model.ActivityModel.query.get(id)

            activity_name = request.form['activity_name']
            d, m, y = request.form['activity_date'].split('-')
            activity_date = datetime.datetime(int(y), int(m), int(d))
            activity_status  = request.form['activity_status']

            query.activity_name = activity_name
            query.activity_date = activity_date
            query.activity_status = activity_status
            model.db.session.commit()
            
            return make_response(jsonify(
                {
                    'status': 200,
                    'msg': "Successfully updated activity data"
                }
            ), 200)
        else:
            return make_response(jsonify(
                {
                    'status': 401,
                    'msg': 'Please check in first'
                }
            ), 401)

    @LoginRequired
    def delete(self, id):
        checkIn = model.AttendanceModel.query.filter(
        model.AttendanceModel.checkin>=datetime.date.today(),
        model.AttendanceModel.user_id==session['user_id']).first()

        if(checkIn):
            query = model.ActivityModel.query.get(id)
            
            if(query):
                model.db.session.delete(query)
                model.db.session.commit()

                return make_response(jsonify(
                    {
                        'status': 200,
                        'msg': "Successfully deleted activity data"
                    }
                ), 200)
            else:
                return make_response(jsonify(
                    {
                        'status': 404,
                        'msg': "Data not found"
                    }
                ), 404)
        else:
            return make_response(jsonify(
                {
                    'status': 401,
                    'msg': 'Please check in first'
                }
            ), 401)

    @LoginRequired
    def get(self, id):
        query = model.ActivityModel.query.get(id)
        if(query):
            activity = {
                'id': query.id,
                'user_id': query.user_id,
                'activity_name': query.activity_name,
                'activity_date': query.activity_date.strftime('%d-%m-%Y'),
                'activity_status': query.activity_status,
            }

            response = {
                'status': 200,
                'msg': "Successfully get activity data by id",
                'activity': activity
            }

        else:
            response = {
                'status': 404,
                'msg': "Data not found",
            }

        return response
        
class FilterDateActivityResource(Resource):
    @LoginRequired
    def get(self, dateFrom, dateTo):
        isValidDateFrom = re.match("\\d{2}-\\d{2}-\\d{4}", dateFrom)
        isValidDateTo = re.match("\\d{2}-\\d{2}-\\d{4}", dateTo)
        if(isValidDateFrom and isValidDateTo):
            dateFrom = datetime.datetime.strptime(dateFrom, '%d-%m-%Y').date()
            dateTo = datetime.datetime.strptime(dateTo, '%d-%m-%Y').date()

            query = model.ActivityModel.query.filter(
                model.ActivityModel.activity_date.between(dateFrom, dateTo)).all()

            return make_response(jsonify(
                {
                    'status': 200,
                    'msg': 'Successfully get all filtered activities data',
                    'activities': [
                        {
                            'id': activity.id,
                            'user_id': activity.user_id,
                            'activity_name': activity.activity_name,
                            'activity_date': activity.activity_date.strftime('%d-%m-%Y'),
                            'activity_status': activity.activity_status,
                        }
                        for activity in query],
                }
            ), 200)
        else:
            return make_response(jsonify(
                {
                    'status': 400,
                    'msg': 'Invalid date format'
                }
            ), 400)

api.add_resource(EmployeeResource, "/employee", methods=['GET', 'POST'])
api.add_resource(ActivityResource, "/activity", methods=['GET', 'POST'])
api.add_resource(UpdateDeleteActivityResource, "/activity/<id>", methods=['PUT', 'DELETE', 'GET'])
api.add_resource(FilterDateActivityResource, "/activity/<dateFrom>/<dateTo>", methods=['GET'])
api.add_resource(LoginEmployeeResource, "/login", methods=['POST'])
api.add_resource(LogoutEmployeeResource, "/logout", methods=['POST'])
api.add_resource(AttendanceResource, "/attendance", methods=['GET', 'POST'])

if __name__ == '__main__':
    app.run(debug=True)