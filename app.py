import json
from datetime import datetime
from pathlib import Path

from flask import (
    Flask,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

app = Flask(__name__)
app.secret_key = "squatcheck-hw10-dev-key"

DATA_DIR = Path(__file__).parent / "data"


def load_json(name):
    with open(DATA_DIR / name, "r") as f:
        return json.load(f)


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def ensure_state():
    session.setdefault("start_time", None)
    session.setdefault("lesson_visits", {})
    session.setdefault("answers", {})


@app.after_request
def log_state(response):
    print(
        f"[{request.method} {request.path}] session="
        f"{dict(session)}",
        flush=True,
    )
    return response


@app.route("/")
def home():
    session.clear()
    ensure_state()
    return render_template("home.html")


@app.route("/start", methods=["POST"])
def start():
    ensure_state()
    session["start_time"] = now_iso()
    session.modified = True
    return redirect(url_for("learn", n=1))


@app.route("/learn/<int:n>")
def learn(n):
    ensure_state()
    lessons = load_json("lessons.json")["lessons"]
    if n < 1 or n > len(lessons):
        abort(404)
    lesson = lessons[n - 1]
    session["lesson_visits"][str(n)] = now_iso()
    session.modified = True
    return render_template(
        "learn.html", lesson=lesson, total_lessons=len(lessons)
    )


@app.route("/quiz/<int:n>")
def quiz(n):
    ensure_state()
    questions = load_json("quiz.json")["questions"]
    if n < 1 or n > len(questions):
        abort(404)
    q = questions[n - 1]
    safe_q = {k: v for k, v in q.items() if k not in ("correct", "explanation")}
    if q["type"] == "true_false_multi":
        safe_q["statements"] = [
            {"text": s["text"]} for s in q.get("statements", [])
        ]
    return render_template(
        "quiz.html", question=safe_q, total_questions=len(questions)
    )


def check_answer(question, submitted):
    qtype = question["type"]
    if qtype == "multi_select":
        return set(submitted or []) == set(question["correct"])
    if qtype == "single_select":
        return submitted == question["correct"]
    if qtype == "true_false_multi":
        expected = [s["correct"] for s in question["statements"]]
        return list(submitted or []) == expected
    return False


@app.route("/submit-answer", methods=["POST"])
def submit_answer():
    ensure_state()
    payload = request.get_json(silent=True) or {}
    qid = payload.get("question_id")
    answer = payload.get("answer")
    if qid is None:
        return jsonify({"error": "missing question_id"}), 400

    questions = load_json("quiz.json")["questions"]
    question = next((q for q in questions if q["id"] == qid), None)
    if question is None:
        return jsonify({"error": "unknown question"}), 404

    is_correct = check_answer(question, answer)
    session["answers"][str(qid)] = {"answer": answer, "correct": is_correct}
    session.modified = True

    if qid < len(questions):
        next_url = url_for("quiz", n=qid + 1)
    else:
        next_url = url_for("result")
    return jsonify({"correct": is_correct, "next_url": next_url})


@app.route("/result")
def result():
    ensure_state()
    questions = load_json("quiz.json")["questions"]
    answers = session.get("answers", {})
    breakdown = []
    score = 0
    for q in questions:
        entry = answers.get(str(q["id"]), {})
        correct = bool(entry.get("correct"))
        if correct:
            score += 1
        breakdown.append(
            {"id": q["id"], "prompt": q["prompt"], "correct": correct}
        )
    return render_template(
        "result.html", score=score, total=len(questions), breakdown=breakdown
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
