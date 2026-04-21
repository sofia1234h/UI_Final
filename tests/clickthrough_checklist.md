
#How to run
1. pip install -r requirements.txt 
2. flask --app app run 
3. Open http://localhost:5000 

#Click through Section
| # | Action | Expected Result | Pass/Fail | Notes |
| [ ] 1 | Open `/` | [cite_start]Home page loads with Start button visible [cite: 253] | | |
| [ ] 2 | Click Start | [cite_start]URL changes to `/learn/1` and intro is visible [cite: 253] | | |
| [ ] 3 | Click Next (Lessons 1-5) | [cite_start]URL advances `/learn/1` → `/learn/2` ... → `/learn/5` [cite: 253] | | |
| [ ] 4 | Click Next from Lesson 5 | [cite_start]URL changes to `/quiz/1` [cite: 253] | | |
| [ ] 5 | Q1: Submit multi-select | [cite_start]Advances to `/quiz/2` [cite: 253] | | |
| [ ] 6 | Q2: Submit single-select | [cite_start]Advances to `/quiz/3` [cite: 253] | | |
| [ ] 7 | Q3: Submit True/False | [cite_start]Advances to `/result` [cite: 253] | | |
| [ ] 8 | View Result page | [cite_start]Score displays correctly out of 3 [cite: 253] | | |
| [ ] 9 | Click Restart | [cite_start]Returns to `/` and session resets [cite: 253] | | |
| [ ] 10| Use Browser Back Button | [cite_start]App does not crash at any stage [cite: 253] | | |

##Backend Verification
* [cite_start][ ] **Start Time**: Confirm `start_time` is printed in server console after clicking Start[cite: 254].
* [cite_start][ ] **Lesson Visits**: Confirm `lesson_visits` has a new timestamp after each lesson visit[cite: 255].
* [cite_start][ ] **Quiz Answers**: Confirm `answers[id]` is populated with answer + correct flag after submit[cite: 256].
* [cite_start][ ] **Scoring**: Confirm `/result` score matches the sum of correct flags in console[cite: 257].

#Bug Log
| Date | URL | What I did | What happened | What I expected | Assigned to |
|---|---|---|---|---|---|
| | | | | | |
