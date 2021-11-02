from pymongo import MongoClient

client = MongoClient('localhost', 27017)
db = client.week00

def bike():
    bike_numbers = 10
    bikes = range(1, bike_numbers + 1)

    for bike in bikes:
        db.bikedata.insert_one({'bike_number' : bike, 'user_id' : None, 'rental' : False})
    
    print(bike)

bike()