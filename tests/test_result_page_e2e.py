#!/usr/bin/env python3
"""
End-to-end test for the result page functionality.
Tests the full happy path and edge cases.
"""

import sys
sys.path.insert(0, '/Users/jolie/Desktop/Group proj/UI_Final')

from app import app


def run_tests():
    """Run all result page tests and print pass/fail for each check."""
    app.config['TESTING'] = True
    results = []

    with app.test_client() as client:
        # Enable sessions
        client.get('/')  # Initialize session

        # ========================================
        # TEST 1: Full happy path with mixed answers
        # ========================================
        print("\n" + "=" * 60)
        print("TEST 1: Full happy path with one wrong answer")
        print("=" * 60)

        # Step 1: POST /start
        resp = client.post('/start', follow_redirects=False)
        check1 = resp.status_code == 302 and '/learn/1' in resp.location
        results.append(("POST /start redirects to /learn/1", check1))
        print(f"{'PASS' if check1 else 'FAIL'}: POST /start redirects to /learn/1")
        if not check1:
            print(f"  Expected: 302 redirect to /learn/1")
            print(f"  Got: {resp.status_code}, Location: {resp.location}")

        # Step 2: Walk through all lessons
        for n in range(1, 6):
            resp = client.get(f'/learn/{n}')
            check = resp.status_code == 200
            results.append((f"GET /learn/{n} returns 200", check))
            print(f"{'PASS' if check else 'FAIL'}: GET /learn/{n} returns 200")
            if not check:
                print(f"  Got: {resp.status_code}")

        # Step 3: Submit answers to all 4 quiz questions
        # Q1 (multi_select): Submit WRONG answer - ["No compensations"]
        # Correct is ["Excessive Forward Lean", "Lumbar Flexion"]
        resp = client.post('/submit-answer',
            json={"question_id": 1, "answer": ["No compensations"]},
            content_type='application/json')
        data = resp.get_json()
        check = resp.status_code == 200 and data.get('correct') == False
        results.append(("Q1 wrong answer marked incorrect", check))
        print(f"{'PASS' if check else 'FAIL'}: Q1 wrong answer marked incorrect")
        if not check:
            print(f"  Response: {data}")

        # Q2 (single_select): Submit CORRECT answer
        resp = client.post('/submit-answer',
            json={"question_id": 2, "answer": "Excessive Forward Lean"},
            content_type='application/json')
        data = resp.get_json()
        check = resp.status_code == 200 and data.get('correct') == True
        results.append(("Q2 correct answer marked correct", check))
        print(f"{'PASS' if check else 'FAIL'}: Q2 correct answer marked correct")
        if not check:
            print(f"  Response: {data}")

        # Q3 (true_false_multi): Submit CORRECT answer [False, True, True, False]
        resp = client.post('/submit-answer',
            json={"question_id": 3, "answer": [False, True, True, False]},
            content_type='application/json')
        data = resp.get_json()
        check = resp.status_code == 200 and data.get('correct') == True
        results.append(("Q3 correct answer marked correct", check))
        print(f"{'PASS' if check else 'FAIL'}: Q3 correct answer marked correct")
        if not check:
            print(f"  Response: {data}")

        # Q4 (spot_click): Submit CORRECT answer
        resp = client.post('/submit-answer',
            json={"question_id": 4, "answer": {"correct": True, "x": 0.6, "y": 0.13}},
            content_type='application/json')
        data = resp.get_json()
        check = resp.status_code == 200 and data.get('correct') == True
        results.append(("Q4 correct answer marked correct", check))
        print(f"{'PASS' if check else 'FAIL'}: Q4 correct answer marked correct")
        if not check:
            print(f"  Response: {data}")

        # Step 4: GET /result and verify content
        print("\n--- Checking /result page ---")
        resp = client.get('/result')
        html = resp.data.decode('utf-8')

        # Check 3a: Score header (3 / 4)
        check_score = '3 / 4' in html
        results.append(("Result page shows score '3 / 4'", check_score))
        print(f"{'PASS' if check_score else 'FAIL'}: Result page shows score '3 / 4'")
        if not check_score:
            # Find the score line
            import re
            score_match = re.search(r'(\d+)\s*/\s*(\d+)', html)
            if score_match:
                print(f"  Found: {score_match.group(0)}")
            else:
                print("  No score pattern found in HTML")

        # Check 3b: FAIL badge for wrong answer
        check_fail_badge = 'badge-fail' in html and 'FAIL' in html
        results.append(("Result page contains FAIL badge", check_fail_badge))
        print(f"{'PASS' if check_fail_badge else 'FAIL'}: Result page contains FAIL badge")
        if not check_fail_badge:
            print("  'badge-fail' or 'FAIL' not found in HTML")

        # Check 3c: Explanation text from quiz.json visible (for Q1 wrong answer)
        explanation_q1 = "Heels stay flat on the floor"
        check_explanation = explanation_q1 in html
        results.append(("Result page shows explanation for wrong answer", check_explanation))
        print(f"{'PASS' if check_explanation else 'FAIL'}: Result page shows explanation for wrong answer")
        if not check_explanation:
            print(f"  Expected to find: '{explanation_q1}'")
            # Check for any explanation
            if 'callout-blue' in html:
                print("  'callout-blue' class found (explanation container exists)")
            else:
                print("  'callout-blue' class not found")

        # Check 3d: Review Lessons link pointing to /learn/1
        check_review = 'href="/learn/1"' in html and 'Review Lessons' in html
        results.append(("Result page has 'Review Lessons' link to /learn/1", check_review))
        print(f"{'PASS' if check_review else 'FAIL'}: Result page has 'Review Lessons' link to /learn/1")
        if not check_review:
            if 'Review Lessons' in html:
                print("  'Review Lessons' text found but link may be different")
            else:
                print("  'Review Lessons' text not found")

        # Check 3e: Restart button/link pointing to /
        check_restart = 'href="/"' in html and 'Restart' in html
        results.append(("Result page has 'Restart' link to /", check_restart))
        print(f"{'PASS' if check_restart else 'FAIL'}: Result page has 'Restart' link to /")
        if not check_restart:
            if 'Restart' in html:
                print("  'Restart' text found but link may be different")
            else:
                print("  'Restart' text not found")

        # Additional check: PASS badges for correct answers
        pass_badge_count = html.count('badge-pass')
        check_pass_badges = pass_badge_count == 3  # 3 correct answers
        results.append(("Result page shows 3 PASS badges", check_pass_badges))
        print(f"{'PASS' if check_pass_badges else 'FAIL'}: Result page shows 3 PASS badges")
        if not check_pass_badges:
            print(f"  Expected: 3, Found: {pass_badge_count}")

        # ========================================
        # TEST 2: Edge case - no answers submitted
        # ========================================
        print("\n" + "=" * 60)
        print("TEST 2: Edge case - no answers submitted (fresh start)")
        print("=" * 60)

        # Start a new session
        client.get('/')  # Clear session
        client.post('/start')  # Start new session

        # Go directly to /result without submitting answers
        resp = client.get('/result')
        check_no_crash = resp.status_code == 200
        results.append(("GET /result with no answers doesn't crash", check_no_crash))
        print(f"{'PASS' if check_no_crash else 'FAIL'}: GET /result with no answers doesn't crash")
        if not check_no_crash:
            print(f"  Status code: {resp.status_code}")

        html = resp.data.decode('utf-8')

        # Check score is 0 / 4
        check_zero_score = '0 / 4' in html
        results.append(("Result page shows score '0 / 4' with no answers", check_zero_score))
        print(f"{'PASS' if check_zero_score else 'FAIL'}: Result page shows score '0 / 4' with no answers")

        # Check page handles None user_answer gracefully
        check_graceful = 'No answer selected' in html or 'text-muted' in html
        results.append(("Result page handles missing answers gracefully", check_graceful))
        print(f"{'PASS' if check_graceful else 'FAIL'}: Result page handles missing answers gracefully")
        if not check_graceful:
            # Check for any error indicators
            if 'error' in html.lower() or 'exception' in html.lower():
                print("  Found error/exception text in HTML")
            else:
                print("  No 'No answer selected' or 'text-muted' found")

        # All 4 should be FAIL
        fail_badge_count = html.count('badge-fail')
        check_all_fail = fail_badge_count == 4
        results.append(("All 4 questions show FAIL badge when unanswered", check_all_fail))
        print(f"{'PASS' if check_all_fail else 'FAIL'}: All 4 questions show FAIL badge when unanswered")
        if not check_all_fail:
            print(f"  Expected: 4, Found: {fail_badge_count}")

    # ========================================
    # SUMMARY
    # ========================================
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  [{status}] {name}")

    print(f"\nTotal: {passed}/{total} checks passed")

    if passed == total:
        print("\n✓ All checks passed!")
        return 0
    else:
        print(f"\n✗ {total - passed} check(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())
