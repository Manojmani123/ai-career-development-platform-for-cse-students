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
    
class LearningResource(models.Model):
    RESOURCE_TYPES = [
        ('Course', 'Course'),
        ('Video', 'Video'),
        ('Documentation', 'Documentation'),
        ('Book', 'Book'),
        ('Article', 'Article'),
    ]

    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)

    title = models.CharField(max_length=200)

    resource_type = models.CharField(
        max_length=50,
        choices=RESOURCE_TYPES
    )

    url = models.URLField()

    def __str__(self):
        return self.title
    
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    full_name = models.CharField(max_length=200)

    university = models.CharField(
        max_length=200,
        blank=True,
        null=True
    )

    degree = models.CharField(
        max_length=200,
        blank=True,
        null=True
    )

    year_of_study = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    github_link = models.URLField(
        blank=True,
        null=True
    )

    linkedin_link = models.URLField(
        blank=True,
        null=True
    )

    resume = models.FileField(
        upload_to='resumes/',
        blank=True,
        null=True
    )
    extracted_text = models.TextField(
        blank=True,
        null=True
    )

    extracted_skills = models.ManyToManyField(
        Skill,
        blank=True
    )

    manual_skills = models.ManyToManyField(
    Skill,
    blank=True,
    related_name='manual_user_profiles'
)
    
    manual_tools = models.ManyToManyField(
    'IndustryTool',
    blank=True,
    related_name='user_profiles'
)
    is_resume_valid = models.BooleanField(
        default=False
    )
    def __str__(self):
        return self.user.username
    
class ReadinessAssessment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    job_role = models.ForeignKey(JobRole, on_delete=models.CASCADE)

    academic_score = models.FloatField(default=0)
    industry_score = models.FloatField(default=0)
    overall_readiness_score = models.FloatField(default=0)

    strengths = models.TextField(blank=True, null=True)
    weaknesses = models.TextField(blank=True, null=True)
    recommendation = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.username} - {self.job_role.role_name} - {self.overall_readiness_score}%"
    
class IndustryTool(models.Model):
    CATEGORY_CHOICES = [
        ('Development Tool', 'Development Tool'),
        ('Data Tool', 'Data Tool'),
        ('Cloud Tool', 'Cloud Tool'),
        ('AI/ML Tool', 'AI/ML Tool'),
        ('Testing Tool', 'Testing Tool'),
        ('DevOps Tool', 'DevOps Tool'),
    ]

    tool_name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES)

    def __str__(self):
        return self.tool_name


class JobRoleTool(models.Model):
    IMPORTANCE_CHOICES = [
        ('High', 'High'),
        ('Medium', 'Medium'),
        ('Low', 'Low'),
    ]

    job_role = models.ForeignKey(JobRole, on_delete=models.CASCADE)
    tool = models.ForeignKey(IndustryTool, on_delete=models.CASCADE)
    importance = models.CharField(max_length=20, choices=IMPORTANCE_CHOICES, default='Medium')

    class Meta:
        unique_together = ('job_role', 'tool')

    def __str__(self):
        return f"{self.job_role.role_name} - {self.tool.tool_name}"
    
class EmployabilityBottleneck(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    job_role = models.ForeignKey(JobRole, on_delete=models.CASCADE)

    readiness_assessment = models.ForeignKey(
        ReadinessAssessment,
        on_delete=models.CASCADE
    )

    main_bottleneck = models.CharField(max_length=200)
    explanation = models.TextField()
    recommendation = models.TextField()

    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.username} - {self.job_role.role_name} - {self.main_bottleneck}"
    
class UserProject(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    title = models.CharField(max_length=200)
    description = models.TextField()

    project_url = models.URLField(blank=True, null=True)
    github_url = models.URLField(blank=True, null=True)

    skills_used = models.ManyToManyField(
        Skill,
        blank=True
    )

    tools_used = models.ManyToManyField(
        'IndustryTool',
        blank=True
    )

    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.username} - {self.title}"
    

class CareerTransitionAnalysis(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    current_role = models.ForeignKey(
        JobRole,
        on_delete=models.CASCADE,
        related_name='current_transition_roles'
    )

    target_role = models.ForeignKey(
        JobRole,
        on_delete=models.CASCADE,
        related_name='target_transition_roles'
    )

    skill_match_score = models.FloatField(default=0)
    tool_match_score = models.FloatField(default=0)
    feasibility_score = models.FloatField(default=0)

    difficulty_level = models.CharField(max_length=100)

    missing_skills = models.TextField(blank=True, null=True)
    missing_tools = models.TextField(blank=True, null=True)

    recommendation = models.TextField()

    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.username}: {self.current_role.role_name} to {self.target_role.role_name}"