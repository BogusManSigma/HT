HABITLINE SOURCE CODE
=====================

This folder contains the complete editable Habitline 4.6 application.
Your personal tracking data is not included.

MAIN FILES
----------

habit_tracker.py
  Python server, local data storage, validation, food search and XP awards.

index.html
  The complete interface, styling, graphs and browser-side interactions.

manifest.json and service-worker.js
  Phone/desktop installation and interface caching.

test_habit_tracker.py
  Automated tests for storage, nutrition, schedules, XP and interface rules.

START THE APP
-------------

Double-click "Launch Habitline.bat".

The app creates data/habits.json automatically the first time it starts.

RUN TESTS
---------

Open PowerShell in this folder and run:

python -m unittest discover -s . -p "test_*.py"

SAFE EXPERIMENTING
------------------

Make changes in this source folder so the working Habitline app remains
untouched. Keep backups of any data/habits.json file you care about.
