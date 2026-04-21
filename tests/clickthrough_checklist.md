
## How to Run
1. `pip install -r requirements.txt`  
2. `flask --app app run` 
3. Open http://localhost:5000  

## Click-through Section
| # | Action | Expected Result | Pass/Fail | Notes |
|---|---|---|---|---|
| [ ] 1 | Open `/` | Home page loads with Start button visible  | | |
| [ ] 2 | Click Start | URL changes to `/learn/1` and intro is visible  | | |
| [ ] 3 | Click Next (Lessons 1-5) |URL advances `/learn/1` → `/learn/2` ... → `/learn/5`  | | |
| [ ] 4 | Click Next from Lesson 5 | URL changes to `/quiz/1`  | | |
| [ ] 5 | Q1: Submit multi-select | Advances to `/quiz/2`  | | |
| [ ] 6 | Q2: Submit single-select | Advances to `/quiz/3`  | | |
| [ ] 7 | Q3: Submit True/False | Advances to `/result`  | | |
| [ ] 8 | View Result page | Score displays correctly out of 3 | | |
| [ ] 9 | Click Restart | Returns to `/` and session resets  | | |
| [ ] 10| Use Browser Back Button | App does not crash at any stage  | | |

## Backend Verification
* [ ] **Start Time**: Confirm `start_time` is printed in server console after clicking Start
* [ ] **Lesson Visits**: Confirm `lesson_visits` has a new timestamp after each lesson visit 
* [ ] **Quiz Answers**: Confirm `answers[id]` is populated with answer + correct flag after submit 
* [ ] **Scoring**: Confirm `/result` score matches the sum of correct flags in console 

#Bug Log
| Date | URL | What I did | What happened | What I expected | Assigned to |
|---|---|---|---|---|---|
| | | | | | |
