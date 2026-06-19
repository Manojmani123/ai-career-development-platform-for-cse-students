from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import AdminRequest

from django.contrib.auth.models import User
from .models import AdminRequest
from .models import JobRole, Skill, JobRoleSkill

from .models import CareerMatchResult
from .models import LearningResource
from .models import UserProfile

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            'full_name',
            'university',
            'degree',
            'year_of_study',
            'github_link',
            'linkedin_link',
            'resume',
        ]

class LearningResourceForm(forms.ModelForm):
    class Meta:
        model = LearningResource
        fields = [
            'skill',
            'title',
            'resource_type',
            'url'
        ]

class CareerMatchForm(forms.ModelForm):
    class Meta:
        model = CareerMatchResult
        fields = ['job_role', 'selected_skills']

        widgets = {
            'selected_skills': forms.CheckboxSelectMultiple,
        }
class JobRoleForm(forms.ModelForm):
    class Meta:
        model = JobRole
        fields = ['role_name', 'description']


class SkillForm(forms.ModelForm):
    class Meta:
        model = Skill
        fields = ['skill_name', 'category']


class JobRoleSkillForm(forms.ModelForm):
    class Meta:
        model = JobRoleSkill
        fields = ['job_role', 'skill', 'importance']

class AdminRequestForm(forms.ModelForm):
    class Meta:
        model = AdminRequest
        fields = ['full_name', 'email', 'invite_code']

    def clean_email(self):
        email = self.cleaned_data.get('email')

        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered. Please use a different email.")

        if AdminRequest.objects.filter(email=email, status='Pending').exists():
            raise forms.ValidationError("An admin request with this email is already pending approval.")

        return email

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
