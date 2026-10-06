# -*- coding: utf-8 -*-
"""
Upgrade script to implement individual certificates per syllabus topic and per project step
Docente & Administrador: Econ. Janio Cerezo Piedrahita, Mgs.
"""

import os

html_path = os.path.join(os.path.dirname(__file__), "index.html")

with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

# Verify markers
assert 'id="moodle-selector-modal"' in html, "moodle-selector-modal not found"
assert 'function generateMoodleReport(type)' in html, "generateMoodleReport not found"
assert 'function renderActiveTopic(topic)' in html, "renderActiveTopic not found"
assert 'function renderActiveProjectStep(step)' in html, "renderActiveProjectStep not found"

print("All markers found in index.html!")
