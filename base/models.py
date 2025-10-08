from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone

class Registration(models.Model):
    username = models.CharField(max_length=100, unique=True, null=False, blank=False)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    email = models.EmailField(unique=True)
    contact = models.CharField(max_length=15, blank=True, null=True)
    gender = models.CharField(
        max_length=10,
        choices=(('M', 'Male'), ('F', 'Female'), ('O', 'Other')),
        blank=True
    )
    password = models.CharField(max_length=128)
    is_admin = models.BooleanField(default=False)   

    def __str__(self):
        return self.username

    @property
    def is_staff(self):
        return self.is_admin  

    # Helper methods
    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password) 
        
class Topic(models.Model):
    name = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.name


class SubTopic(models.Model):
    topic = models.CharField(max_length=200,null=True, blank=True)
    name = models.CharField(max_length=200,null=True, blank=True)

    class Meta:
        unique_together = ('topic', 'name')

    def __str__(self):
        return self.name
            

class StudyMaterial(models.Model):
    topic = models.CharField(max_length=200, null=True, blank=True)      # changed from FK
    subtopic = models.CharField(max_length=200, null=True, blank=True) 
    difficulty_level = models.CharField(max_length=10, choices=[
        ("easy", "Easy"),
        ("medium", "Medium"),
        ("hard", "Hard"),
    ])
    document = models.FileField(upload_to="documents/")

    def __str__(self):
        return f"{self.topic} - {self.subtopic} ({self.difficulty_level})"

class MCQ(models.Model):
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]
    id = models.BigAutoField(primary_key=True)
    study_material = models.ForeignKey(
        StudyMaterial, on_delete=models.CASCADE, related_name="mcqs", null=True, blank=True
    )
    question_no = models.IntegerField()
    question = models.TextField()
    option_a = models.CharField(max_length=255)
    option_b = models.CharField(max_length=255)
    option_c = models.CharField(max_length=255)
    option_d = models.CharField(max_length=255)
    correct_answer = models.CharField(max_length=1, choices=[
        ('A', 'Option A'),
        ('B', 'Option B'),
        ('C', 'Option C'),
        ('D', 'Option D'),
    ],
    )
    difficulty_level = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES)

    class Meta:
        db_table = "base_mcq"
        unique_together = ('study_material', 'question_no')

    def __str__(self):
        return f"{self.study_material.topic} - {self.study_material.subtopic} - Q{self.question_no}"

                              
class QuizHistory(models.Model):
    user_id= models.IntegerField()
    username = models.CharField(max_length=100, default="unknown") 
    topic = models.CharField(max_length=200, null=True, blank=True)      # changed from FK
    subtopic = models.CharField(max_length=200, null=True, blank=True)
    level = models.CharField(max_length=10, choices=[('easy','Easy'),('medium','Medium'),('hard','Hard')])
    num_quizzes = models.IntegerField(default=0)   # total quizzes taken
    avg_score = models.FloatField(default=0.0)

    class Meta:
        unique_together = ('user_id', 'topic', 'subtopic', 'level')  # ensure one row per user/topic/subtopic/level

    def save(self, *args, **kwargs):
        if not self.username:
            self.username = "unknown"
        super().save(*args, **kwargs)

class QuizResult(models.Model):
    user = models.ForeignKey(Registration, on_delete=models.CASCADE)
    username = models.CharField(max_length=150, default="unknown")
    topic = models.CharField(max_length=200, null=True, blank=True)      # changed from FK
    subtopic = models.CharField(max_length=200, null=True, blank=True)   # changed from FK
    difficulty_level = models.CharField(max_length=20,default="easy")
    date_attempted = models.DateTimeField(default=timezone.now)
    
    total_questions = models.IntegerField(default=0)
    correct_answers = models.IntegerField(default=0)
    wrong_answers = models.IntegerField(default=0)
    score = models.FloatField(default=0.0)  # percentage
    status = models.CharField(max_length=20, default='Passed')

    def __str__(self):
        return f"{self.user.username} - {self.topic} - {self.subtopic} ({self.difficulty_level}"  
    
class QuizAnswer(models.Model):
    quiz_result = models.ForeignKey(
        'QuizResult', on_delete=models.CASCADE, related_name='answers'
    )
    question_text = models.TextField()
    option_a = models.CharField(max_length=200)
    option_b = models.CharField(max_length=200)
    option_c = models.CharField(max_length=200)
    option_d = models.CharField(max_length=200)
    correct_answer = models.CharField(max_length=1,choices=[
        ('A', 'Option A'),
        ('B', 'Option B'),
        ('C', 'Option C'),
        ('D', 'Option D'),
        ])  # 'A','B','C','D'
    user_answer = models.CharField(max_length=1, blank=True, null=True)

    def __str__(self):
        return f"{self.question_text[:50]}... ({self.user_answer})"
