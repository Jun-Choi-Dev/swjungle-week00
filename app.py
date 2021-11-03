from os import name
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
    'bike_number' : None, 'penalty_score' : 0})

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

# API를 여기 아래서부터 만들어주세요.


if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)