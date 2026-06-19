from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class AdminInviteCode(models.Model):
    code = models.CharField(max_length=50, unique=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.code


class AdminRequest(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]

    full_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    invite_code = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.full_name} - {self.status}"
class UserSecurityQuestion(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    question = models.CharField(max_length=255)
    answer = models.CharField(max_length=255)

    def __str__(self):
        return self.user.username
    
class JobRole(models.Model):
    role_name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.role_name


class Skill(models.Model):
    CATEGORY_CHOICES = [
        ('Programming', 'Programming'),
        ('Database', 'Database'),
        ('Web Development', 'Web Development'),
        ('AI/ML', 'AI/ML'),
        ('Cybersecurity', 'Cybersecurity'),
        ('Cloud', 'Cloud'),
        ('Tools', 'Tools'),
        ('Soft Skill', 'Soft Skill'),
    ]

    skill_name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)

    def __str__(self):
        return self.skill_name


class JobRoleSkill(models.Model):
    IMPORTANCE_CHOICES = [
        ('High', 'High'),
        ('Medium', 'Medium'),
        ('Low', 'Low'),
    ]

    job_role = models.ForeignKey(JobRole, on_delete=models.CASCADE)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    importance = models.CharField(max_length=20, choices=IMPORTANCE_CHOICES, default='Medium')

class Meta:
        unique_together = ('job_role', 'skill')
        def __str__(self):
            return f"{self.job_role.role_name} - {self.skill.skill_name}"
class CareerMatchResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    job_role = models.ForeignKey(JobRole, on_delete=models.CASCADE)
    selected_skills = models.ManyToManyField(Skill, related_name='selected_skills')
    matched_skills = models.ManyToManyField(Skill, related_name='matched_skills', blank=True)
    missing_skills = models.ManyToManyField(Skill, related_name='missing_skills', blank=True)
    match_score = models.FloatField(default=0)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.username} - {self.job_role.role_name} - {self.match_score}%"