from flask import Flask
from flask import jsonify
from flask import request

from flask_jwt_extended import create_access_token
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended import jwt_required
from flask_jwt_extended import JWTManager
from flask_jwt_extended import get_raw_jwt

from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient

app = Flask(__name__)

client = MongoClient('localhost', 27017)
db = client.week00

app.config["JWT_SECRET_KEY"] = "week00_team_6"
app.config['JWT_BLACKLIST_ENABLED'] = True
app.config['JWT_BLACKLIST_TOKEN_CHECKS'] = ['access']
jwt = JWTManager(app)

@jwt.token_in_blacklist_loader
def check_if_token_in_blacklist(decrypted_token):
    found_jti = db.blacklist.find_one({'jti':decrypted_token['jti']})
    if found_jti is None:
        return False
    else:
        return True

@jwt.revoked_token_loader
def revoked_token_callback():
    return jsonify({
        'description': 'The token has been revoked,',
        'error': 'token_revoked'
    })

@app.route("/register", methods=["POST"])
def register():
    user_id = request.json.get("user_id")
    encrypted_password = generate_password_hash(request.json.get("password"), method='sha256')
    name = request.json.get("name")

    db.userdata.insert_one({'user_id':user_id, 'password':encrypted_password, 'name':name,
    'bike_number' : None, 'penalty_score' : 0, 'rental' : False})

    return jsonify({"result": "success"})


@app.route("/login", methods=["POST"])
def login():
    user_id = request.json.get("user_id", None)
    password = request.json.get("password", None)

    # userdata(db) 대조 로직 추가
    user = db.userdata.find_one({'user_id':user_id})
    if user != None:
        if check_password_hash(user['password'], password):
            access_token = create_access_token(identity=user_id)
            return jsonify(access_token=access_token)
        else:
            return jsonify({'result': "warning : 비밀번호가 맞지 않습니다."})
    else:
        return jsonify({'result': "warning : 회원가입이 필요합니다."})


@app.route("/logout", methods=["POST"])
@jwt_required
def logout():
    jti = get_raw_jwt()['jti']
    db.blacklist.insert_one({'jti':jti})
    return {'message': 'Successfully logged out.'}


# user
# POST : 자전거 신규등록
@app.route('/new_bike', methods=['POST'])
def new_bike():
    # 1. 클라이언트로부터 데이터를 받기
    user_id_receive = request.json.get('user_id')  # 클라이언트로부터 id 받는 부분
    want_bike = int(request.json.get('want_bike'))

    user = db.userdata.find_one({'user_id': user_id_receive}) 
    bike = db.bikedata.find_one({'bike_number': want_bike}) 

    print(user['rental'])
    print(bike['rental'])

    # id : 유저의 바이크 대여 여부 확인
    if user['rental'] is True:
        return jsonify({'result': 'warning : 이미 바이크를 빌렸습니다.'})

    # bike의 대여 여부 확인
    if bike['rental'] is True:
        return jsonify({'result': 'warning : 이미 빌린 바이크입니다.'})

    db.userdata.update({'user_id': user_id_receive}, 
    {'$set': {'rental': True, 'bike_number': want_bike}})
    #db.userdata.update_one({'user_id': user_id_receive}, {'$set': {'rental': True}})

    db.bikedata.update({'bike_number': want_bike}, 
    {'$set': {'rental': True,'user_id': user_id_receive}})
    #db.bikedata.update_one({'bike_number': want_bike}, {'$set': {'rental': True}})

    return jsonify({'result': 'success'})

# POST : 로그아웃???

# GET : 유저 화면(일련번호, 벌점 현황)

# 유저화면 > 유저id받아서, 자전거번호 유무, 벌점현황
# 자전거 소유하지 않으면 자전거번호에 문자열 "없음" 포함된 유저리스트 뿌림
@app.route("/user", methods=["GET"])
def user():
    user_id = request.args.get("user_id")
    user = db.userdata.find_one({'user_id': user_id})
    bike_number = user["bike_number"]
    penalty_score = user["penalty_score"]

    return jsonify({"result": "success",
        "content": [user_id, bike_number, penalty_score]})


# 관리자: 자전거번호 받아서, 유저 아이디, 이름, 패널티점수 확인
# 혹여 자전거번호가 문자형이면 숫자형으로 변환
@app.route("/search", methods=["GET"])
def search():
    bike_number = request.args.get("bike_number")
    if bike_number == None:
        return jsonify({"result": "번호를 입력해주세요."})
    
    num = int(bike_number)
    bike_in_db = db.bikedata.find_one({'bike_number' : num})
    if bike_in_db == None:
        return jsonify({"result": "존재하지 않는 자전거입니다."})

    user = db.userdata.find_one({'bike_number': num})
    if user == None:
        return jsonify({"result": "사용자에게 대여되지 않은 자전거입니다."})

    user_id = user["user_id"]
    name = user["name"]
    penalty_score = user["penalty_score"]

    return jsonify({"result": "success", 
        "content": [user_id, name, penalty_score]})

# 관리자: 요청시 벌점추가 (+1점으로 해놓음)
# 혹여 자전거번호가 문자형이면 숫자형으로 변환
@app.route("/penalty", methods=["POST"])
def penalty():
    bike_number = request.json.get("bike_number", None)
    num = int(bike_number)
    user = db.userdata.find_one({'bike_number': num})
    penalty = user["penalty_score"]
    new_penalty = int(penalty) + 1
    db.userdata.update_one({"bike_number" : num}, 
        {'$set':{'penalty_score':new_penalty}})

    return jsonify({"result": "success"})

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)