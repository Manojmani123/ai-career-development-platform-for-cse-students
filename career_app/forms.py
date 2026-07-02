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
import os
from django import forms
from .models import ReadinessAssessment
from .models import IndustryTool, JobRoleTool,UserProject
from .models import (
    IndustryTool,
    JobRoleTool,
    UserProject,
    CareerTransitionAnalysis,
    CompetencyGroup,
    CompetencyGroupMember
    
)
class DatasetImportForm(forms.Form):
    dataset_file = forms.FileField(label="Upload Excel Dataset")
class CareerTransitionForm(forms.ModelForm):
    class Meta:
        model = CareerTransitionAnalysis
        fields = [
            'current_role',
            'target_role'
        ]
class CompetencyGroupForm(forms.ModelForm):
    class Meta:
        model = CompetencyGroup
        fields = ['job_role', 'group_name', 'rule']


class CompetencyGroupMemberForm(forms.Form):
    group = forms.ModelChoiceField(
        queryset=CompetencyGroup.objects.all(),
        label="Competency Group"
    )

    job_role_skills = forms.ModelMultipleChoiceField(
        queryset=JobRoleSkill.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        label="Skills in this Group",
        required=False
    )

    def __init__(self, *args, **kwargs):
        selected_group = kwargs.pop('selected_group', None)
        super().__init__(*args, **kwargs)

        if selected_group:
            self.fields['job_role_skills'].queryset = JobRoleSkill.objects.filter(
                job_role=selected_group.job_role
            ).select_related('skill', 'job_role')
class IndustryToolForm(forms.ModelForm):
    class Meta:
        model = IndustryTool
        fields = ['tool_name', 'category']


class JobRoleToolForm(forms.Form):
    job_role = forms.ModelChoiceField(
        queryset=JobRole.objects.none(),
        label="Job Role"
    )

    high_tools = forms.ModelMultipleChoiceField(
        queryset=IndustryTool.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="High Importance Tools"
    )

    medium_tools = forms.ModelMultipleChoiceField(
        queryset=IndustryTool.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Medium Importance Tools"
    )

    low_tools = forms.ModelMultipleChoiceField(
        queryset=IndustryTool.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Low Importance Tools"
    )

    def __init__(self, *args, **kwargs):
        super(JobRoleToolForm, self).__init__(*args, **kwargs)

        self.fields['job_role'].queryset = JobRole.objects.all()
        self.fields['high_tools'].queryset = IndustryTool.objects.all()
        self.fields['medium_tools'].queryset = IndustryTool.objects.all()
        self.fields['low_tools'].queryset = IndustryTool.objects.all()
class ReadinessAssessmentForm(forms.ModelForm):
    class Meta:
        model = ReadinessAssessment
        fields = ['job_role']

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
             'manual_skills',
             'manual_tools'
        ]
        widgets = {
            'manual_skills': forms.CheckboxSelectMultiple,
            'manual_tools': forms.CheckboxSelectMultiple,
        }
    def clean_resume(self):
        resume = self.cleaned_data.get('resume')

        if resume:
            allowed_extensions = ['.pdf', '.docx']
            ext = os.path.splitext(resume.name)[1].lower()

            if ext not in allowed_extensions:
                raise forms.ValidationError(
                    "Only PDF and DOCX resume files are allowed."
                )

            max_size = 5 * 1024 * 1024  # 5MB

            if resume.size > max_size:
                raise forms.ValidationError(
                    "Resume file size must be less than 5MB."
                )

        return resume
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
        fields = ['job_role']
class JobRoleForm(forms.ModelForm):
    class Meta:
        model = JobRole
        fields = ['role_name', 'description']


class SkillForm(forms.ModelForm):
    class Meta:
        model = Skill
        fields = ['skill_name', 'category']

class JobRoleSkillForm(forms.Form):
    job_role = forms.ModelChoiceField(
        queryset=JobRole.objects.all(),
        label="Job Role"
    )

    high_skills = forms.ModelMultipleChoiceField(
        queryset=Skill.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="High Importance Skills"
    )

    medium_skills = forms.ModelMultipleChoiceField(
        queryset=Skill.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Medium Importance Skills"
    )

    low_skills = forms.ModelMultipleChoiceField(
        queryset=Skill.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Low Importance Skills"
    )

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

class BottleneckForm(forms.Form):
    job_role = forms.ModelChoiceField(
        queryset=JobRole.objects.all()
    )

class UserProjectForm(forms.ModelForm):
    class Meta:
        model = UserProject
        fields = [
            'title',
            'description',
            'project_url',
            'github_url',
            'skills_used',
            'tools_used'
        ]

        widgets = {
            'skills_used': forms.CheckboxSelectMultiple,
            'tools_used': forms.CheckboxSelectMultiple,
        }
