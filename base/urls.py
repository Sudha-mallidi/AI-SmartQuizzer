from django.urls import path
from . import views
urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.login_view, name="login"),
    path("register/", views.register, name="register"),
    path("userdashboard/", views.userdashboard, name="userdashboard"),
    path("userlogout/", views.userlogout, name="userlogout"),
    path("profile/", views.user_profile, name="user_profile"),
    path("get_subtopics/", views.get_subtopics, name="get_subtopics"),

    # Quiz routes
    path("start-quiz/", views.start_quiz, name="start_quiz"),
    path("quiz/previous/", views.previous_question, name="previous_question"),
    path("quiz/submit/", views.submit_quiz, name="submit_quiz"),
    path("quiz/", views.take_quiz, name="take_quiz"),
    path("quiz_results/<int:quiz_id>/", views.quiz_results, name="quiz_results"),
    path('quiz-review/<int:quiz_id>/', views.quiz_review, name='quiz_review'),

    path("adminlogin/", views.admin_login, name="adminlogin"),
    path("admindashboard/", views.admindashboard, name="admindashboard"),
    path("adminlogout/", views.adminlogout, name="adminlogout"),
    path("delete_material/<int:material_id>/", views.delete_material, name="delete_material"),
]    