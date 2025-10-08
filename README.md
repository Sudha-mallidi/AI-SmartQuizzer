# 🧠 AI SmartQuizzer

An intelligent Django-based quiz platform that uses **Machine Learning (Decision Tree Classifier)** to suggest personalized quiz difficulty levels and topics based on user performance.

---

## 🚀 Features
- 🎯 **AI-Powered Quiz Recommendations** using a Decision Tree Classifier (Supervised Learning)
- 📊 Personalized user dashboard with quiz progress and performance analytics
- 📚 Admin module to upload study materials and auto-generate MCQs
- 🧾 Quiz history tracking and result visualization
- 🔐 User authentication and session management

---

## 🧠 AI Technique Used
We used a **Decision Tree Classifier** from **scikit-learn**, a supervised machine learning algorithm that learns from users’ quiz history data (topic, subtopic, level, scores, attempts) to predict the most suitable **next level** or **next topic** for improvement.

**Why Decision Tree?**
- Easy to interpret (shows clear decision rules)
- Works with both numeric and categorical data
- Performs well with limited data
- Matches the natural learning progression hierarchy (Easy → Medium → Hard → Next Topic)

---

## ⚙️ Tech Stack
- **Backend:** Django (Python)
- **Frontend:** HTML, CSS, JavaScript
- **AI/ML:** scikit-learn (Decision Tree Classifier)
- **Database:** MySQL (via MySQL Workbench)
- **Version Control:** Git + GitHub

---

## 🪪 License
This project is licensed under the [MIT License](LICENSE).

---

## 👩‍💻 Author
**Mohana Sudha Mallidi**  
[GitHub Profile](https://github.com/Sudha-mallidi)

---

## 💡 How to Run Locally
```bash
# 1️⃣ Clone the repository
git clone https://github.com/Sudha-mallidi/AI-SmartQuizzer.git
cd AI-SmartQuizzer

# 2️⃣ Create a virtual environment
python -m venv venv
venv\Scripts\activate   # (Windows)

# 3️⃣ Install dependencies
pip install -r requirements.txt

# 4️⃣ Configure MySQL Database
# In your settings.py, update:
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.mysql',
#         'NAME': 'smartquizzer_db',
#         'USER': 'root',
#         'PASSWORD': 'yourpassword',
#         'HOST': 'localhost',
#         'PORT': '3306',
#     }
# }

# 5️⃣ Run migrations
python manage.py makemigrations
python manage.py migrate

# 6️⃣ Start the server
python manage.py runserver