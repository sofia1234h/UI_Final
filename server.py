from flask import Flask, render_template, request, jsonify


app = Flask(__name__)


data = {
    "lessons": {
        "1": {"id": 1, "title": "Heel Rise", "content": "Look for the heels lifting...", "media": "heel_video.mp4"},
        "2": {"id": 2, "title": "Forward Lean", "content": "Watch the torso angle...", "media": "lean_video.mp4"},
    },
    "quizzes": {
        "1": {"id": 1, "question": "Are the heels lifting?", "options": ["Yes", "No"], "answer": "Yes"},
        "2": {"id": 2, "question": "Is the lean excessive?", "options": ["Yes", "No"], "answer": "No"},
    }
}

user_responses = {
    "learning_clicks": [],
    "quiz_answers": {}
}

# ROUTE 1
# Home page
@app.route('/')
def index():
    return render_template("index.html")

# ROUTE 2 
@app.route('/quiz/<id>')
def quiz(id):
    question = data["quizzes"].get(id)
    return render_template('quiz.html', question=question)
