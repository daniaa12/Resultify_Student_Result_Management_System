RESULTIFY - Student Result Management System

SETUP (Windows / VS Code)
1. Install Python 3.10 or newer.
2. Extract this project ZIP.
3. Open the extracted folder in VS Code.
4. In VS Code, choose Terminal > New Terminal.
5. Run:
   py -m pip install -r requirements.txt
6. Run:
   py app.py
7. Open Chrome and visit:
   http://127.0.0.1:5000

DEMO ADMIN LOGIN
Username: admin
Password: admin123

HOW TO USE
- Open Admin from the navigation and log in.
- Add a student, with a unique roll number.
- From the dashboard click Marks beside that student.
- Add subject names, obtained marks, and maximum marks; save.
- From dashboard click View, or search roll number on the home page.
- Use Print / Save PDF on the marksheet.

IMPORTANT
- This is a local demonstration project. Before deploying publicly, change ADMIN_USERNAME,
  ADMIN_PASSWORD, and app.secret_key in app.py, and use production deployment settings.
- Do not enter real sensitive student information into a publicly hosted demo.
- database.db is created automatically when app.py starts.
