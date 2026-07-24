from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
import os
from .models import InterviewAnswer
from .models import (
    AdminRequest,
    JobRole,
    Skill,
    JobRoleSkill,
    CareerMatchResult,
    LearningResource,
    UserProfile,
    ReadinessAssessment,
    IndustryTool,
    JobRoleTool,
    UserProject,
    CareerTransitionAnalysis,
    CompetencyGroup,
    CompetencyGroupMember,
     InterviewSession,
   
)


class DatasetImportForm(forms.Form):
    dataset_file = forms.FileField(label="Upload Excel Dataset")


class JobRoleForm(forms.ModelForm):
    class Meta:
        model = JobRole
        fields = ['role_name', 'description']

        widgets = {
            'role_name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4
            }),
        }


class SkillForm(forms.ModelForm):
    class Meta:
        model = Skill
        fields = ['skill_name', 'category']

        widgets = {
            'skill_name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
        }


class JobRoleSkillForm(forms.Form):
    job_role = forms.ModelChoiceField(
        queryset=JobRole.objects.all(),
        label="Job Role",
        widget=forms.Select(attrs={'class': 'form-select'})
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


class CareerMatchForm(forms.ModelForm):
    class Meta:
        model = CareerMatchResult
        fields = ['job_role']

        widgets = {
            'job_role': forms.Select(attrs={'class': 'form-select'})
        }


class LearningResourceForm(forms.ModelForm):
    class Meta:
        model = LearningResource
        fields = [
            'skill',
            'title',
            'resource_type',
            'url'
        ]

        widgets = {
            'skill': forms.Select(
                attrs={
                    'class': 'form-select'
                }
            ),

            'title': forms.TextInput(
                attrs={
                    'class': 'form-control'
                }
            ),

            'resource_type': forms.Select(
                attrs={
                    'class': 'form-select'
                }
            ),

            'url': forms.URLInput(
                attrs={
                    'class': 'form-control'
                }
            ),
        }


class ReadinessAssessmentForm(forms.ModelForm):
    class Meta:
        model = ReadinessAssessment
        fields = ['job_role']

        widgets = {
            'job_role': forms.Select(attrs={'class': 'form-select'})
        }


class IndustryToolForm(forms.ModelForm):
    class Meta:
        model = IndustryTool
        fields = [
            'tool_name',
            'category'
        ]

        widgets = {
            'tool_name': forms.TextInput(
                attrs={
                    'class': 'form-control'
                }
            ),

            'category': forms.TextInput(
                attrs={
                    'class': 'form-control'
                }
            ),
        }

class JobRoleToolForm(forms.Form):
    job_role = forms.ModelChoiceField(
        queryset=JobRole.objects.all(),
        label="Job Role",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    high_tools = forms.ModelMultipleChoiceField(
        queryset=IndustryTool.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="High Importance Tools"
    )

    medium_tools = forms.ModelMultipleChoiceField(
        queryset=IndustryTool.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Medium Importance Tools"
    )

    low_tools = forms.ModelMultipleChoiceField(
        queryset=IndustryTool.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Low Importance Tools"
    )


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
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'university': forms.TextInput(attrs={'class': 'form-control'}),
            'degree': forms.TextInput(attrs={'class': 'form-control'}),
            'year_of_study': forms.NumberInput(attrs={'class': 'form-control'}),
            'github_link': forms.URLInput(attrs={'class': 'form-control'}),
            'linkedin_link': forms.URLInput(attrs={'class': 'form-control'}),
            'resume': forms.ClearableFileInput(attrs={'class': 'form-control'}),
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

            max_size = 5 * 1024 * 1024

            if resume.size > max_size:
                raise forms.ValidationError(
                    "Resume file size must be less than 5MB."
                )

        return resume


class BottleneckForm(forms.Form):
    job_role = forms.ModelChoiceField(
        queryset=JobRole.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'})
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
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4
            }),
            'project_url': forms.URLInput(attrs={'class': 'form-control'}),
            'github_url': forms.URLInput(attrs={'class': 'form-control'}),
            'skills_used': forms.CheckboxSelectMultiple,
            'tools_used': forms.CheckboxSelectMultiple,
        }


class CareerTransitionForm(forms.ModelForm):
    class Meta:
        model = CareerTransitionAnalysis
        fields = ['current_role', 'target_role']

        widgets = {
            'current_role': forms.Select(attrs={'class': 'form-select'}),
            'target_role': forms.Select(attrs={'class': 'form-select'}),
        }


class CompetencyGroupForm(forms.ModelForm):
    class Meta:
        model = CompetencyGroup
        fields = ['job_role', 'group_name', 'rule']

        widgets = {
            'job_role': forms.Select(attrs={'class': 'form-select'}),
            'group_name': forms.TextInput(attrs={'class': 'form-control'}),
            'rule': forms.Select(attrs={'class': 'form-select'}),
        }


class CompetencyGroupMemberForm(forms.Form):
    group = forms.ModelChoiceField(
        queryset=CompetencyGroup.objects.select_related('job_role').all().order_by(
            'job_role__role_name',
            'group_name'
        ),
        label="Competency Group",
        widget=forms.Select(attrs={'class': 'form-select'})
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
            self.fields['group'].initial = selected_group
            self.fields['group'].queryset = CompetencyGroup.objects.filter(
                id=selected_group.id
            )

            self.fields['job_role_skills'].queryset = JobRoleSkill.objects.filter(
                job_role=selected_group.job_role
            ).select_related(
                'skill',
                'job_role'
            ).order_by(
                'skill__skill_name'
            )

            existing_members = CompetencyGroupMember.objects.filter(
                group=selected_group
            ).values_list(
                'job_role_skill_id',
                flat=True
            )

            self.fields['job_role_skills'].initial = existing_members


class AdminRequestForm(forms.ModelForm):
    class Meta:
        model = AdminRequest
        fields = ['full_name', 'email', 'invite_code']

        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'invite_code': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')

        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                "This email is already registered. Please use a different email."
            )

        if AdminRequest.objects.filter(email=email, status='Pending').exists():
            raise forms.ValidationError(
                "An admin request with this email is already pending approval."
            )

        return email


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']





class InterviewSetupForm(forms.ModelForm):
    class Meta:
        model = InterviewSession
        fields = ['job_role', 'project']

        widgets = {
            'job_role': forms.Select(
                attrs={
                    'class': 'form-control',
                }
            ),
            'project': forms.Select(
                attrs={
                    'class': 'form-control',
                }
            ),
        }

        labels = {
            'job_role': 'Target Job Role',
            'project': 'Project Evidence',
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['job_role'].queryset = JobRole.objects.all().order_by(
            'role_name'
        )

        if user:
            self.fields['project'].queryset = UserProject.objects.filter(
                user=user
            ).order_by('-created_at')
        else:
            self.fields['project'].queryset = UserProject.objects.none()

        self.fields['job_role'].empty_label = 'Select a job role'
        self.fields['project'].empty_label = 'Select one of your projects'


class InterviewAnswerForm(forms.ModelForm):
    class Meta:
        model = InterviewAnswer
        fields = ['answer_text']

        widgets = {
            'answer_text': forms.Textarea(
                attrs={
                    'class': 'answer-textarea',
                    'placeholder': (
                        'Type your answer here. Include specific examples, '
                        'technical decisions, challenges and outcomes.'
                    ),
                    'rows': 10,
                    'required': True,
                }
            )
        }

        labels = {
            'answer_text': ''
        }