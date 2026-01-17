from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route("/news")
def news():
    data = {
        "articles": [
            {
                "title": "সোনালী ব্যাংকে অফিসার নিয়োগ বিজ্ঞপ্তি",
                "url": "https://www.sonalibank.com.bd",
                "category": "jobs",
                "source": "সোনালী ব্যাংক"
            },
            {
                "title": "এইচএসসি পরীক্ষার নতুন রুটিন প্রকাশ",
                "url": "http://www.educationboard.gov.bd",
                "category": "education",
                "source": "শিক্ষা বোর্ড"
            }
        ]
    }
    return jsonify(data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
