import os
import django
import joblib
import numpy as np
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import LabelEncoder

# ✅ 1. Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sample.settings")
django.setup()

# ✅ 2. Import your model
from base.models import QuizHistory

# ✅ 3. Fetch data from QuizHistory
data = QuizHistory.objects.all().values("level", "avg_score", "num_quizzes", "topic", "subtopic")

if not data:
    print("⚠️ No quiz history found. Users need to attempt quizzes first.")
    exit()

# ✅ 4. Prepare features
levels = [d["level"] for d in data]
avg_scores = [d["avg_score"] for d in data]
num_attempts = [d["num_quizzes"] for d in data]

# Encode levels
le_level = LabelEncoder()
level_enc = le_level.fit_transform(levels)

# Feature matrix
X = np.array([level_enc, avg_scores, num_attempts]).T

# ✅ 5. Define target suggestions based on your rules
y = []
for lvl, score, attempts in zip(levels, avg_scores, num_attempts):
    if lvl == "easy" and attempts >= 5 and score >= 80:
        y.append("medium")
    elif lvl == "medium" and attempts >= 5 and score >= 75:
        y.append("hard")
    elif lvl == "hard" and attempts >= 3 and score >= 80:
        y.append("next_topic")
    else:
        y.append(lvl)  # continue at same level if conditions not met

# Encode target
le_suggestion = LabelEncoder()
y_enc = le_suggestion.fit_transform(y)

# ✅ 6. Train Decision Tree
clf = DecisionTreeClassifier()
clf.fit(X, y_enc)

# ✅ 7. Save model for later use
joblib.dump((clf, le_level, le_suggestion), "dashboard_suggester.pkl")
print("✅ Suggestion model trained and saved as dashboard_suggester.pkl")

# ✅ 8. Example: Making a suggestion for a single user
# Sample user
sample_level = "easy"
sample_avg = 82
sample_attempts = 5

sample_level_enc = le_level.transform([sample_level])[0]
X_new = [[sample_level_enc, sample_avg, sample_attempts]]
predicted_suggestion_enc = clf.predict(X_new)[0]
predicted_suggestion = le_suggestion.inverse_transform([predicted_suggestion_enc])[0]

print(f"Suggested next step for user: {predicted_suggestion}")