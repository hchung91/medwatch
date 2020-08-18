from flask import Flask, jsonify, request
from flask_restful import Resource, Api
from bs4 import BeautifulSoup

import requests

app = Flask(__name__)
api = Api(app)

class FindNewAnchors(Resource):
    def get(self, target_url, since_datetime):
        has_update = FindNewAnchors.check_for_update(target_url, since_datetime)
        if has_update:
            # pull anchors from page
            headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36"}
            r = requests.get(target_url)
            soup = BeautifulSoup(r.text, 'html.parser')
            anchors = soup.find_all('a')

            return jsonify({'anchors': str(anchors)})


            # Check list of anchors to all anchors in database

            # Add new anchors to database


    @staticmethod
    def check_for_update(target_url, since_datetime):
        headers = {"If-Modified-Since": since_datetime, "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36"}
        
        r = requests.head(target_url, headers=headers)

        status_code = r.status_code

        if status_code == 200:
            return True
        elif status_code == 204:
            return False
        else:
            return False

class Home(Resource):
    def get(self):
        return {'message': 'Welcome!'}

api.add_resource(FindNewAnchors, '/updated/<path:target_url>/<string:since_datetime>')
api.add_resource(Home, '/')

if __name__ == '__main__':
    app.run(debug=True)