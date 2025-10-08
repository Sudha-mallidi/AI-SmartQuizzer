import random, joblib
from collections import defaultdict
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from .models import Registration, StudyMaterial, MCQ, QuizResult, QuizHistory, Topic, SubTopic,QuizAnswer
from .forms import StudyMaterialForm
from .utils import extract_mcqs_from_pdf
from django.contrib import messages
import os
import numpy as np
from django.utils import timezone
from django.db.models import Count, Avg, Q
from django.conf import settings
from django.contrib.auth import logout
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

# Home
def home(request):
    return render(request, 'home.html')


# User Login
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        try:
            user = Registration.objects.get(username=username)
            if password == user.password:
                request.session['user_id'] = user.id
                request.session['username'] = user.username
                messages.success(request, f"Welcome {user.username}!")
                return redirect('userdashboard')
            else:
                messages.error(request, "Invalid password")
        except Registration.DoesNotExist:
            messages.error(request, "Invalid username or password")

        return redirect('login')

    return render(request, 'login.html')


# User Registration
def register(request):
    if request.method == "POST":
        username = request.POST.get("username")
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        contact = request.POST.get("contact")
        gender = request.POST.get("gender")
        password = request.POST.get("password")
        retype_password = request.POST.get("retype_password")

        if password != retype_password:
            messages.error(request, "Passwords do not match")
            return render(request, 'register.html')

        if Registration.objects.filter(email=email).exists():
            messages.error(request, "Email already registered. Please login.")
            return redirect('login')

        if Registration.objects.filter(username=username).exists():
            messages.error(request, "Username already exists. Please choose another.")
            return redirect('register')

        user = Registration(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email,
            contact=contact,
            gender=gender,
            password=password,  # plain text
        )
        user.save()

        messages.success(request, "Registration successful! Please login.")
        return redirect("login")

    return render(request, 'register.html')

# Load trained model if exists
MODEL_PATH = "recommender_model.pkl"
clf, le_topic, le_subtopic, le_level = None, None, None, None
if os.path.exists(MODEL_PATH):
    try:
        clf, le_topic, le_subtopic, le_level = joblib.load(MODEL_PATH)
    except Exception as e:
        print("⚠️ Could not load model:", e)

def get_ai_suggestion(topic, subtopic, level, avg_score, attempts):
    """
    Predict next level using trained ML model.
    """
    try:
        topic_enc = le_topic.transform([topic])[0]
        subtopic_enc = le_subtopic.transform([subtopic])[0]
        level_enc = le_level.transform([level])[0]
        X_new = [[topic_enc, subtopic_enc, level_enc, avg_score, attempts]]
        return clf.predict(X_new)[0]
    except Exception:
        return None  # fallback if model not ready

def build_suggestions(user):
    """
    Build AI/Rule-based suggestions for the user.
    """
    suggestions = []

    # Aggregate quiz stats grouped by topic & subtopic
    topic_sub_stats = list(
        QuizResult.objects.filter(user=user)
        .values("topic", "subtopic")
        .annotate(
            easy_count=Count("id", filter=Q(difficulty_level="easy")),
            easy_avg=Avg("score", filter=Q(difficulty_level="easy")),
            medium_count=Count("id", filter=Q(difficulty_level="medium")),
            medium_avg=Avg("score", filter=Q(difficulty_level="medium")),
            hard_count=Count("id", filter=Q(difficulty_level="hard")),
            hard_avg=Avg("score", filter=Q(difficulty_level="hard")),
        )
    )

    for ts in topic_sub_stats:
        topic = (ts.get("topic") or "Unknown").strip().title()
        subtopic = (ts.get("subtopic") or "General").strip().title()

        # Determine current and next level
        current_level, next_level, avg_score = None, None, None

        # Easy → Medium (optional, if user completed enough easy)
        if ts["easy_count"] >= 5 and (ts["easy_avg"] or 0) >= 80:
          current_level = "easy"
          next_level = "medium"
          avg_score = ts["easy_avg"]
        # Only include high-priority suggestions: medium→hard or hard→next topic
        if ts["medium_count"] >= 5 and (ts["medium_avg"] or 0) >= 75:
            current_level = "medium"
            next_level = "hard"
            avg_score = ts["medium_avg"]
        elif ts["hard_count"] >= 3 and (ts["hard_avg"] or 0) >= 80:
            current_level = "hard"
            next_level = "next topic"
            avg_score = ts["hard_avg"]

        if current_level and next_level:
            suggestions.append({
                "subtopic": subtopic,
                "topic": topic,
                "current_level": current_level,
                "next_level": next_level,
                "avg_score": round(avg_score or 0, 2)
            })

    return suggestions if suggestions else None

# User Dashboard
def userdashboard(request):
    user_id = request.session.get("user_id")
    if not user_id:
       messages.error(request, "Please login first")
       return redirect("login")

    user = Registration.objects.get(id=user_id)
    # Count of materials added by the user
    materials = StudyMaterial.objects.all()
    materials_count = materials.count()

    # Create all possible quiz combinations (topic, subtopic, difficulty_level)
    difficulty_levels = ['easy', 'medium', 'hard']
    all_combinations = set()
    for material in materials:
        for level in difficulty_levels:
            all_combinations.add((material.topic, material.subtopic, level))

    # Get completed quizzes (unique combinations attempted by the user)
    completed_qs = QuizResult.objects.filter(user=user).values_list(
        'topic', 'subtopic', 'difficulty_level'
    ).distinct()
    completed_combinations = set(completed_qs)

    completed_quizzes = len(completed_combinations)


    if request.method == "POST" and 'start_quiz' not in request.POST:
        form = StudyMaterialForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Study material added successfully!")
            return redirect("userdashboard")
    else:
        form = StudyMaterialForm()

    # Fetch Topics & Subtopics for Take Quiz form
    topics = Topic.objects.all()
    subtopics = SubTopic.objects.all()
    

    quiz_history = (
        QuizResult.objects.filter(user=user)
        .values("topic", "subtopic", "difficulty_level")
        .annotate(
            num_quizzes=Count("id"),
            avg_score=Avg("score")
        )
    )

    # ✅ Fetch latest results
    results = []
    quiz_results = QuizResult.objects.filter(user=user).order_by("-date_attempted")

    for r in quiz_results:
        if not r.id:
            continue
        # calculate pass/fail dynamically if you prefer (>=50% = Passed)
        status = "Passed" if r.score >= 60 else "Failed"

        results.append({
            "id": r.id,
            "topic": r.topic,
            "subtopic": r.subtopic,
            "difficulty_level": r.difficulty_level,
            "correct_answers": r.correct_answers,    # match template
        "total_questions": r.total_questions,    # match template
        "date_attempted": r.date_attempted, 
            "status": status,
        })   

    # Group by topic/subtopic with difficulty-level aggregates
    topic_sub_stats = (
    QuizResult.objects.filter(user=user)
    .values("topic", "subtopic")
    .annotate(
        easy_count=Count("id", filter=Q(difficulty_level="easy")),
        easy_avg=Avg("score", filter=Q(difficulty_level="easy")),
        medium_count=Count("id", filter=Q(difficulty_level="medium")),
        medium_avg=Avg("score", filter=Q(difficulty_level="medium")),
        hard_count=Count("id", filter=Q(difficulty_level="hard")),
        hard_avg=Avg("score", filter=Q(difficulty_level="hard")),
      )
    )

    suggestions_by_topic = defaultdict(list)

    for ts in topic_sub_stats:
        topic = (ts.get("topic") or "Unknown").title()
        subtopic = ts.get("subtopic") or "General"

        next_level = None
        current_level = None
        avg_score = None

        # ✅ Progression logic
        if ts["easy_count"] >= 5 and (ts["easy_avg"] or 0) >= 80:
            if ts["medium_count"] >= 5 and (ts["medium_avg"] or 0) >= 75:
                if ts["hard_count"] >= 3 and (ts["hard_avg"] or 0) >= 80:
                   current_level = "hard"
                   next_level = "next topic"
                   avg_score = ts["hard_avg"]
                else:
                   current_level = "medium"
                   next_level = "hard"
                   avg_score = ts["medium_avg"]
            else:
               current_level = "easy"
               next_level = "medium"
               avg_score = ts["easy_avg"]

        # ✅ Save in topic-grouped dict
        if next_level:
           suggestions_by_topic[topic].append({
            "subtopic": subtopic,
            "current_level": current_level,
            "next_level": next_level,
            "avg_score": round(avg_score or 0, 2)
        })

        # --- Build AI/Rule-based suggestions grouped by topic ---
    flat_suggestions = build_suggestions(user)
    if flat_suggestions:
      suggestions_dict = defaultdict(list)
      for s in flat_suggestions:
        topic = s["topic"].title().strip()
        suggestions_dict[topic].append(s)
      suggestions_by_topic = dict(suggestions_dict)

    # Convert to normal dict for template
    suggestions_by_topic = dict(suggestions_by_topic) if suggestions_by_topic else None

    return render(request, "userdashboard.html", {
      "user": user,
      "topics": topics,
      "subtopics": subtopics, 
      "quiz_history": quiz_history,
      "materials_count": materials_count,
      "completed_quizzes": completed_quizzes,
      "results": results,
      "form": form,
      "suggestions_by_topic": suggestions_by_topic,
    })

# User Profile
def user_profile(request):
    user_id = request.session.get("user_id")
    if not user_id:
        messages.error(request, "Please login first")
        return redirect("login")
    
    user = Registration.objects.get(id=user_id)
    return render(request, "user_profile.html", {"user": user})

# Start Quiz View
def start_quiz(request):
    user_id = request.session.get("user_id")
    if not user_id:
        messages.error(request, "Please login first")
        return redirect("login")

    if request.method == "POST":
        topic = request.POST.get("topic")
        subtopic = request.POST.get("subtopic")
        level = request.POST.get("level")
        num_questions = request.POST.get("num_questions")

        # Validate selections
        if not topic or not subtopic or not level or not num_questions:
            messages.warning(request, "Please select topic, subtopic, difficulty level, and number of questions.")
            return redirect("userdashboard")
        
        try:
            num_questions = int(num_questions)
        except ValueError:
            messages.warning(request, "Invalid number of questions.")
            return redirect("userdashboard")

        # Get related MCQs
        study_materials = StudyMaterial.objects.filter(topic=topic, subtopic=subtopic)
        mcqs = MCQ.objects.filter(study_material__in=study_materials, difficulty_level=level)

        if not mcqs.exists():
            messages.warning(request, "No MCQs found for the selected topic/subtopic/level.")
            return redirect("userdashboard")

        mcqs = list(mcqs)
        random.shuffle(mcqs)
        mcqs = mcqs[:num_questions]

        # Save in session
        request.session.update({
            "quiz_questions": [q.id for q in mcqs],
            "current_index": 0,
            "quiz_answers": {},
            "quiz_topic": topic,
            "quiz_subtopic": subtopic,
            "quiz_level": level
        })

        return redirect("take_quiz")

    return redirect("userdashboard")

def take_quiz(request):
    quiz_questions = request.session.get("quiz_questions", [])
    current_index = request.session.get("current_index", 0)
    answers = request.session.get("quiz_answers", {})
    total_questions = len(quiz_questions)

    if not quiz_questions:
        messages.warning(request, "No quiz found. Please start again.")
        return redirect("userdashboard")

    # Handle POST (Next button)
    if request.method == "POST":
        mcq_id = quiz_questions[current_index]
        selected_option = request.POST.get("answer")
        if selected_option:
            answers[str(mcq_id)] = selected_option
            request.session["quiz_answers"] = answers
        direction = request.POST.get("direction")
        if direction == "previous" and current_index > 0:
           current_index -= 1
        else:
           current_index += 1

        request.session["current_index"] = current_index
        # Redirect to submit_quiz only after the last question
        if current_index >= total_questions:
            return redirect("submit_quiz")
        
        # Display current question
    if current_index < total_questions:
        mcq_id = quiz_questions[current_index]
        try:
            mcq = MCQ.objects.get(id=mcq_id)
        except MCQ.DoesNotExist:
            messages.error(request, "Question not found. Quiz will restart.")
            return redirect("userdashboard")

        return render(request, "take_quiz.html", {
            "question": mcq,
            "current_index": current_index + 1,  # For display
            "total_questions": total_questions,
            "is_last": current_index == total_questions - 1,
            "answers": answers,
            "topic": request.session.get("quiz_topic"),
            "subtopic": request.session.get("quiz_subtopic"),
            "level": request.session.get("quiz_level"),
        })

    # Safety: if current_index somehow exceeds total, redirect to submit
    return redirect("submit_quiz")

def previous_question(request):
    current_index = request.session.get("current_index", 0)
    answers = request.session.get("quiz_answers", {})

    # Save current answer if posted
    if request.method == "POST":
        mcq_id = request.POST.get("question_id")
        selected_answer = request.POST.get("answer")
        if mcq_id and selected_answer:
            answers[mcq_id] = selected_answer
            request.session["quiz_answers"] = answers

    # Go back one question
    if current_index > 0:
        request.session["current_index"] = current_index - 1

    return redirect("take_quiz")


def submit_quiz(request):
    quiz_questions = request.session.get("quiz_questions", [])
    answers = request.session.get("quiz_answers", {})
    user_id = request.session.get("user_id")

    if not quiz_questions or not user_id:
        messages.warning(request, "No quiz in progress. Please start again.")
        return redirect("userdashboard")

    user = Registration.objects.get(id=user_id)
    topic = request.session.get("quiz_topic", "")
    subtopic = request.session.get("quiz_subtopic", "")
    difficulty = request.session.get("quiz_level", "easy")

    total_questions = len(quiz_questions)
    correct_count = 0
    results_list = []

    # Calculate correct / wrong answers
    for q_id in quiz_questions:
        try:
          mcq = MCQ.objects.get(id=q_id)
        except MCQ.DoesNotExist:
            continue

        user_answer = answers.get(str(q_id))
        is_correct = user_answer == mcq.correct_answer
        if is_correct:
            correct_count += 1

        # Map letter to text
        answer_map = {
        'A': mcq.option_a,
        'B': mcq.option_b,
        'C': mcq.option_c,
        'D': mcq.option_d,
        }    

        results_list.append({
            "question": mcq.question,
            "user_answer_letter": user_answer or "",
            "user_answer_text": answer_map.get(user_answer, "") if user_answer else "",
            "correct_answer_letter": mcq.correct_answer,
            "correct_answer_text": answer_map.get(mcq.correct_answer, ""),
            "is_correct": is_correct,
            "options": answer_map
        })   

    score = round((correct_count / total_questions) * 100, 2) if total_questions > 0 else 0
    status = "Passed" if score >= 60 else "Failed"


    # Save everything inside a transaction so we don't partially commit
    with transaction.atomic():
        quiz_result = QuizResult.objects.create(
          user=user,
          username=user.username,
          topic=topic,
          subtopic=subtopic,
          difficulty_level=difficulty,
          total_questions=total_questions,
          correct_answers=correct_count,
          wrong_answers=total_questions - correct_count,
          score=score,
          status=status,
          date_attempted=timezone.now()
        )

        for q_id in quiz_questions:
            mcq = MCQ.objects.get(id=q_id)
            user_answer = answers.get(str(q_id))

            QuizAnswer.objects.create(
              quiz_result=quiz_result,
              question_text=mcq.question,
              option_a=mcq.option_a,
              option_b=mcq.option_b,
              option_c=mcq.option_c,
              option_d=mcq.option_d,
              correct_answer=mcq.correct_answer,
              user_answer=user_answer
            )
    
    # Update QuizHistory
    stats = QuizResult.objects.filter(
        user=user,
        topic=topic,
        subtopic=subtopic,
        difficulty_level=difficulty
    ).aggregate(
        num_quizzes=Count('id'),
        avg_score=Avg('score')
    )

    QuizHistory.objects.update_or_create(
        user_id=user.id,
        topic=topic,
        subtopic=subtopic,
        level=difficulty,
        defaults={
            "username": user.username or "unknown",
            "num_quizzes": stats["num_quizzes"] or 0,
            "avg_score": stats["avg_score"] or 0.0
        }
    )

    # Clear session
    for key in ["quiz_questions", "quiz_answers", "current_index", "quiz_topic", "quiz_subtopic", "quiz_level"]:
        request.session.pop(key, None)
    # Render results page directly instead of redirecting
    return render(request, "quiz_results.html", {
        "results": results_list,
        "quiz_result": quiz_result,
        "score": score,
        "total": total_questions,
        "correct": correct_count,
        "wrong": total_questions - correct_count,
        "status": status,
        "review_url": f"/quiz-review/{quiz_result.id}/"
    })    


def get_subtopics(request):
    topic_name = request.GET.get("topic", "").strip()
    subtopic_list = []

    if topic_name:
        # Case-insensitive filtering using __iexact
        subtopics = SubTopic.objects.filter(topic__iexact=topic_name)
        for s in subtopics:
            if s.name:
                subtopic_list.append({"id": s.id, "name": s.name.strip()})

    return JsonResponse({"subtopics": subtopic_list})


def quiz_results(request,quiz_id):
    user_id = request.session.get("user_id")
    if not user_id:
        messages.error(request, "Please login first")
        return redirect("login")
    
    user = Registration.objects.get(id=user_id)
    

    quiz_questions = request.session.get("quiz_questions", [])
    answers = request.session.get("quiz_answers", {})
    topic = request.session.get("quiz_topic")
    subtopic = request.session.get("quiz_subtopic")
    level = request.session.get("quiz_level")

    if not quiz_questions:
        messages.warning(request, "No quiz found. Please start again.")
        return redirect("userdashboard")

    results = []
    correct = 0
    total = len(quiz_questions)

    for qid in quiz_questions:
        try:
            question = MCQ.objects.get(id=qid)
        except MCQ.DoesNotExist:
            continue

        user_answer = answers.get(str(qid))
        correct_answer = question.correct_answer  # assuming field name
        is_correct = (user_answer == correct_answer)

        if is_correct:
            correct += 1

        results.append({
            "question": question.question,
            "option_a": question.option_a,
            "option_b": question.option_b,
            "option_c": question.option_c,
            "option_d": question.option_d,
            "correct": correct_answer,
            "user_answer": user_answer,
            "is_correct": is_correct
        })

    wrong = total - correct
    score = (correct / total) * 100 if total > 0 else 0
    status = "Passed" if score >= 60 else "Failed"

    # ✅ Save to DB
    quiz_result = QuizResult.objects.create(
        user=user,
        topic=topic,
        subtopic=subtopic,
        difficulty_level=level,
        total_questions=total,
        correct_answers=correct,
        wrong_answers=wrong,
        score=score,
        status=status
    )

    # ✅ Clear session
    request.session.pop("quiz_questions", None)
    request.session.pop("quiz_answers", None)
    request.session.pop("current_index", None)
    request.session.pop("quiz_topic", None)
    request.session.pop("quiz_subtopic", None)
    request.session.pop("quiz_level", None)

    return render(request, "quiz_results.html", {
        "results": results,
        "score": score,
        "total": total,
        "correct": correct,
        "wrong": wrong,
        "status": status,
        "quiz_result": quiz_result,
        "review_url": f"/quiz-review/{quiz_result.id}/"
        })


def quiz_review(request, quiz_id):
    quiz_result = get_object_or_404(QuizResult, id=quiz_id)
    answers = quiz_result.answers.all()  # all Answer objects linked to this quiz

    results = []
    for ans in answers:
        answer_map = {
            "A": ans.option_a,
            "B": ans.option_b,
            "C": ans.option_c,
            "D": ans.option_d
        }

        results.append({
            "question": ans.question_text,  
            "user_answer_letter": ans.user_answer or "",
            "user_answer_text": answer_map.get(ans.user_answer, "") if ans.user_answer else "",
            "correct_answer_letter": ans.correct_answer,
            "correct_answer_text": answer_map.get(ans.correct_answer, ""),
            "is_correct": (ans.user_answer == ans.correct_answer),
            "options": answer_map
        })

    return render(request, "quiz_review.html", {
        "quiz_result": quiz_result,
        "results": results
    })


# User Logout
def userlogout(request):
    request.session.flush()
    messages.success(request, "You have been logged out successfully.")
    return redirect('login')


# Admin Login
def admin_login(request):
    if request.method == "POST":
        username = request.POST.get("username").strip()
        password = request.POST.get("password").strip()

        try: 
            user = Registration.objects.get(username=username)
            
            if user.is_admin and user.check_password(password):
                request.session['user_id'] = user.id
                request.session['username'] = user.username
                messages.success(request, f"Welcome Admin {user.username}!")
                return redirect('admindashboard')
            else:
               messages.error(request, "Invalid admin credentials")
        except Registration.DoesNotExist:
            messages.error(request, "Admin does not exist")

        return redirect('adminlogin')

    return render(request, 'admin.html')

# Admin dashboard
def admindashboard(request):
    user_id = request.session.get("user_id")
    if not user_id:
        messages.error(request, "Please login as admin first")
        return redirect("adminlogin")
    
    user = Registration.objects.get(id=user_id)
    if not user.is_admin:
        messages.error(request, "Access denied")
        return redirect("login")  # redirect normal users to user login
    
    form = StudyMaterialForm()

    # Admin dashboard logic
    if request.method == "POST":
        form = StudyMaterialForm(request.POST, request.FILES)
        if form.is_valid():
             # Use the correct field names from the form
           topic_name = form.cleaned_data['topic']
           subtopic_name = form.cleaned_data['subtopic']

        # Only create if values are not empty
        if topic_name and subtopic_name:
            topic_obj, _ = Topic.objects.get_or_create(name=topic_name)
            subtopic_obj, _ = SubTopic.objects.get_or_create(name=subtopic_name, topic=topic_obj)

            # Save StudyMaterial
            study_material = form.save(commit=False)
            study_material.topic = topic_obj
            study_material.subtopic = subtopic_obj
            study_material.save()

            # Extract and save MCQs (optional)
            mcqs = extract_mcqs_from_pdf(study_material.document.path)
            # Insert into MCQ table
            for idx, q in enumerate(mcqs, start=1):
              MCQ.objects.create(
               study_material=study_material,
               question_no=idx,
               question=q.get("question", ""),
               option_a=q.get("option_a", ""),
               option_b=q.get("option_b", ""),
               option_c=q.get("option_c", ""),
               option_d=q.get("option_d", ""),
               correct_answer=q.get("correct_answer", ""),  # must be 'A', 'B', 'C', or 'D'
               difficulty_level=study_material.difficulty_level
            )
            messages.success(request, "Study material and MCQs uploaded successfully!")
            return redirect("admindashboard")
        else:
            messages.error(request, "Topic and Subtopic cannot be empty.")
    else:
        messages.error(request, "Form is invalid. Please check all fields.")

    user_list = Registration.objects.all()
    materials = StudyMaterial.objects.all()
    mcq_count = MCQ.objects.count()

    return render(request, "admindashboard.html", {
        "user": user,
        "user_list": user_list,
        "form": form,
        "materials": materials,
        "mcq_count": mcq_count,
    })

def delete_material(request, material_id):
    material = get_object_or_404(StudyMaterial, id=material_id)

    # Delete file from MEDIA folder
    if material.document:
        file_path = os.path.join(settings.MEDIA_ROOT, str(material.document))
        if os.path.exists(file_path):
            os.remove(file_path)

    # Delete entry from database
    material.delete()
    messages.success(request, "Study material deleted successfully.")
    return redirect("admindashboard")


# Admin logout
@login_required(login_url='adminlogin')
def adminlogout(request):
    logout(request)
    messages.success(request, "Admin logged out successfully ✅")
    return redirect("adminlogin")
