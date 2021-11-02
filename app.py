from os import name
from flask import Flask
from flask import jsonify
from flask import request

from flask_jwt_extended import create_access_token
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended import jwt_required
from flask_jwt_extended import JWTManager

from pymongo import MongoClient

app = Flask(__name__)

client = MongoClient('localhost', 27017)
db = client.week00

app.config["JWT_SECRET_KEY"] = "week00_team_6"
jwt = JWTManager(app)

@app.route("/register", methods=["POST"])
def register():
    user_id = request.json.get("user_id")
    password = request.json.get("password")
    name = request.json.get("name")

    db.userdata.insert_one({'user_id':user_id, 'password':password, 'name':name,
    'bike_number' : None, 'penalty_score' : 0})

    return jsonify({"result": "success"})


@app.route("/login", methods=["POST"])
def login():
    user_id = request.json.get("user_id", None)
    password = request.json.get("password", None)

    # userdata(db) 대조 로직 추가
    user = db.userdata.find_one({'user_id':user_id})
    if user != None:
        if user['password'] == password:
            access_token = create_access_token(identity=user_id)
            return jsonify(access_token=access_token)
        else:
            return jsonify({'result': "warning : 비밀번호가 맞지 않습니다."})
    else:
        return jsonify({'result': "warning : 회원가입이 필요합니다."})


# API를 여기 아래서부터 만들어주세요.


# 관리자: 일련번호 검색, 유저 이름과 자전거 번호 확인
@app.route("/search", methods=["GET"])
def search():
    bike_number = request.json.get("bike_number", None)
    user = db.userdata.find_one({'bike_number': bike_number})
    user_id = user["user_id"]
    name = user["name"]
    penalty_score = user["penalty_score"]


    return jsonify({"result": "success"})

# 관리자: 추가벌점 부여



if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)