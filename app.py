from flask import Flask
from flask import jsonify
from flask import request
from flask import redirect
from flask import url_for
from flask import render_template
from flask import make_response


from flask_jwt_extended import create_access_token
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended import jwt_required
from flask_jwt_extended import JWTManager
from flask_jwt_extended import get_raw_jwt
from flask_jwt_extended import set_access_cookies

from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient

app = Flask(__name__)

client = MongoClient('localhost', 27017)
db = client.week00

app.config["JWT_SECRET_KEY"] = "week00_team_6"
app.config['JWT_BLACKLIST_ENABLED'] = True
app.config['JWT_BLACKLIST_TOKEN_CHECKS'] = ['access']
app.config['JWT_TOKEN_LOCATION'] = ['cookies']
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

@jwt.user_claims_loader
def add_claims_to_access_token(identity):
    user_id = request.form["user_id"]
    user = db.userdata.find_one({'user_id':user_id})
    return {
        "authority": user['authority']
    }

@app.route("/register", methods=["POST"])
def register():
    user_id = request.json.get("user_id")
    encrypted_password = generate_password_hash(request.json.get("password"), method='sha256')
    name = request.json.get("name")

    db.userdata.insert_one({'user_id':user_id, 'password':encrypted_password, 'name':name,
    'bike_number' : None, 'penalty_score' : 0, 'rental' : False, 'authority': 'normal'})

    return redirect(url_for('home'))

@app.route("/")
def home():
    return render_template('index.html')


@app.route("/login", methods=["POST"])
def login():
    user_id = request.form["user_id"]
    password = request.form["password"]
    user = db.userdata.find_one({'user_id':user_id})
    if user != None:
        if check_password_hash(user['password'], password):
            access_token = create_access_token(identity=user_id)
            if user['authority'] == 'normal':
                resp = make_response(redirect('userpage', 302))
            else:
                resp = make_response(redirect('adminpage', 302))            
            set_access_cookies(resp, access_token)
            return resp
        else:
            return jsonify({'result': "warning : 비밀번호가 맞지 않습니다."})
    else:
        return jsonify({'result': "warning : 회원가입이 필요합니다."})

@app.route("/user", methods=["GET"])
@jwt_required
def userpage():
    return render_template('user.html')

@app.route("/admin", methods=["GET"])
@jwt_required
def adminpage():
    return render_template('admin.html')


@app.route("/logout", methods=["POST"])
@jwt_required
def logout():
    jti = get_raw_jwt()['jti']
    db.blacklist.insert_one({'jti':jti})
    return redirect(url_for('home'))


# user 기본 GET
@app.route("/user")
def user():
    user_id = get_jwt_identity()

    user = db.userdata.find_one({'user_id': user_id}) # 사용자에 대한 데이터
    bike_list = list(db.bikedata.find({}, {'_id':False})) # 바이크 리스트 만들어 숨겨놓기

    return render_template("user.html", user = user, bikes = bike_list)


# POST : 자전거 신규등록
@app.route('/new_bike', methods=['POST'])
def new_bike():
    # 1. 클라이언트로부터 데이터를 받기
    user_id_receive = request.form['user_id']  # 클라이언트로부터 id 받는 부분
    want_bike = int(request.form['want_bike'])

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

    db.bikedata.update({'bike_number': want_bike}, 
    {'$set': {'rental': True,'user_id': user_id_receive}})

    return jsonify({'result': 'success'})

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
    bike_number = user["bike_number"]
    penalty_score = user["penalty_score"]
    # return render_template('admin.html', user_id= , name=, penalty=)
    return jsonify({"result": "success", 
        "content": [user_id, bike_number, penalty_score]})

# 관리자: 요청시 벌점추가 (+1점으로 해놓음)
# 혹여 자전거번호가 문자형이면 숫자형으로 변환
@app.route("/penalty", methods=["POST"])
def penalty():
    bike_number = request.form["bike_number"]
    num = int(bike_number)

    user = db.userdata.find_one({'bike_number': num}, {'_id':False})
    user_id = user['user_id']
    penalty = user['penalty_score']
    new_penalty = int(penalty) + 1

    result = [user_id, bike_number, new_penalty]

    db.userdata.update_one({"bike_number" : num}, 
        {'$set':{'penalty_score':new_penalty}})

    return jsonify({"result": "success", "content": result})

# 관리자: 요청시 벌점초기화 (0점으로 해놓음)
@app.route("/initPenalty", methods=["POST"])
def initPenalty():
    bike_number = request.form["bike_number"]
    num = int(bike_number)
    user = db.userdata.find_one({'bike_number': num}, {'_id':False})
    user_id = user['user_id']
    penalty = user['penalty_score']
    init_penalty = penalty*0
    result = [user_id, bike_number, init_penalty]
    
    db.userdata.update_one({"bike_number" : num}, 
        {'$set':{'penalty_score': 0 }})

    return jsonify({"result": "success", "content": result})

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)