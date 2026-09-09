
import json

from sqlite3 import IntegrityError
from unittest import result
from django.db import models, transaction
from django.urls import reverse
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .forms import RegisterForm
from django.contrib import messages
from django.contrib.auth.models import User
from django.utils.crypto import get_random_string
from .models import AdminInviteCode, AdminRequest
from .forms import AdminRequestForm
from .forms import JobRoleForm, SkillForm, JobRoleSkillForm
from .models import  JobRole, Skill, JobRoleSkill
from .forms import CareerMatchForm
from .models import CareerMatchResult
from .models import LearningResource
from .forms import LearningResourceForm
from django.shortcuts import  get_object_or_404
from .forms import UserProfileForm
from .models import UserProfile
from .utils import extract_text_from_resume, is_valid_resume, extract_skills_from_text

from .forms import ReadinessAssessmentForm
from .models import ReadinessAssessment
from .forms import IndustryToolForm, JobRoleToolForm

from .models import IndustryTool, JobRoleTool
from django.db.models import Avg
from django.core.paginator import Paginator
from django.db.models import Prefetch
from .models import CompetencyGroup, CompetencyGroupMember
from django.utils import timezone
from .forms import CompetencyGroupForm, CompetencyGroupMemberForm
from openpyxl import load_workbook
from .forms import DatasetImportForm
from .forms import BottleneckForm
from .models import EmployabilityBottleneck
from .models import CareerTransitionAnalysis
from .forms import CareerTransitionForm
from django.conf import settings
from .models import UserProject
from .forms import UserProjectForm
from .forms import InterviewSetupForm
from .models import InterviewSession
from .models import InterviewQuestion,InterviewAnswer
from .forms import InterviewAnswerForm
import logging


from .services.ai_interview_evaluator import evaluate_answer_with_ai
from openai import OpenAI

logger = logging.getLogger(__name__)
@login_required
def view_users(request):
    if not request.user.is_superuser:
        return redirect('user_dashboard')

    users = User.objects.filter(
        is_staff=False,
        is_superuser=False
    )

    return render(
        request,
        'career_app/view_users.html',
        {'users': users}
    )


@login_required
def view_admins(request):
    if not request.user.is_superuser:
        return redirect('user_dashboard')

    admins = User.objects.filter(
        is_staff=True,
        is_superuser=False
    )

    return render(
        request,
        'career_app/view_admins.html',
        {'admins': admins}
    )


def home(request):
    return render(request, 'career_app/home.html')


def dashboard_redirect(request):
    if request.user.is_superuser:
        return redirect('super_admin_dashboard')
    elif request.user.is_staff:
        return redirect('admin_dashboard')
    else:
        return redirect('user_dashboard')


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard_redirect')
    else:
        form = RegisterForm()

    return render(request, 'career_app/register.html', {'form': form})


@login_required
def user_dashboard(request):
    return render(request, 'career_app/user_dashboard.html')


@login_required
def admin_dashboard(request):
    if not request.user.is_staff:
        return redirect('user_dashboard')
    return render(request, 'career_app/admin_dashboard.html')


@login_required
def super_admin_dashboard(request):
    if not request.user.is_superuser:
        return redirect('user_dashboard')
    return render(request, 'career_app/super_admin_dashboard.html')


def logout_view(request):
    logout(request)
    return redirect('home')

@login_required
def generate_admin_invite(request):
    if not request.user.is_superuser:
        return redirect('user_dashboard')

    code = None

    if request.method == 'POST':
        code = get_random_string(12).upper()
        AdminInviteCode.objects.create(
            code=code,
            created_by=request.user
        )

    return render(request, 'career_app/generate_admin_invite.html', {'code': code})


def admin_request(request):
    if request.method == 'POST':
        form = AdminRequestForm(request.POST)

        if form.is_valid():
            invite_code = form.cleaned_data['invite_code']

            try:
                code_obj = AdminInviteCode.objects.get(code=invite_code, is_used=False)
            except AdminInviteCode.DoesNotExist:
                messages.error(request, 'Invalid or already used invite code.')
                return redirect('admin_request')

            form.save()
            code_obj.is_used = True
            code_obj.save()

            messages.success(request, 'Admin request submitted successfully. Wait for Super Admin approval.')
            return redirect('login')
    else:
        form = AdminRequestForm()

    return render(request, 'career_app/admin_request.html', {'form': form})


@login_required
def view_admin_requests(request):
    if not request.user.is_superuser:
        return redirect('user_dashboard')

    requests = AdminRequest.objects.all().order_by('-created_at')
    return render(request, 'career_app/view_admin_requests.html', {'requests': requests})


@login_required
def approve_admin_request(request, request_id):
    if not request.user.is_superuser:
        return redirect('user_dashboard')

    admin_req = AdminRequest.objects.get(id=request_id)

    if User.objects.filter(email=admin_req.email).exists():
        messages.error(request, 'A user with this email already exists.')
        return redirect('view_admin_requests')

    username_base = admin_req.email.split('@')[0]
    username = username_base
    counter = 1

    while User.objects.filter(username=username).exists():
        username = f"{username_base}{counter}"
        counter += 1

    temp_password = get_random_string(10)

    User.objects.create_user(
        username=username,
        email=admin_req.email,
        password=temp_password,
        first_name=admin_req.full_name,
        is_staff=True
    )

    admin_req.status = 'Approved'
    admin_req.save()

    return render(request, 'career_app/admin_created.html', {
        'username': username,
        'temp_password': temp_password
    })


@login_required
def reject_admin_request(request, request_id):
    if not request.user.is_superuser:
        return redirect('user_dashboard')

    admin_req = AdminRequest.objects.get(id=request_id)
    admin_req.status = 'Rejected'
    admin_req.save()

    return redirect('view_admin_requests')
from django.core.mail import send_mail
from django.http import HttpResponse
@login_required
def add_job_role(request):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    form = JobRoleForm(request.POST or None)

    if form.is_valid():
        form.save()
        return redirect('view_job_roles')

    return render(request, 'career_app/add_job_role.html', {'form': form})


@login_required
def view_job_roles(request):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    roles = JobRole.objects.all()
    return render(request, 'career_app/view_job_roles.html', {'roles': roles})

@login_required
def edit_job_role(request, role_id):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    role = JobRole.objects.get(id=role_id)

    form = JobRoleForm(
        request.POST or None,
        instance=role
    )

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Job role updated successfully.")
        return redirect('view_job_roles')

    return render(
        request,
        'career_app/edit_job_role.html',
        {
            'form': form,
            'role': role
        }
    )


@login_required
def delete_job_role(request, role_id):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    role = JobRole.objects.get(id=role_id)

    if request.method == 'POST':
        role.delete()
        messages.success(request, "Job role deleted successfully.")
        return redirect('view_job_roles')

    return render(
        request,
        'career_app/delete_job_role.html',
        {
            'role': role
        }
    )

@login_required
def add_skill(request):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    form = SkillForm(request.POST or None)

    if form.is_valid():
        form.save()
        return redirect('view_skills')

    return render(request, 'career_app/add_skill.html', {'form': form})


@login_required
def view_skills(request):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    skills = Skill.objects.all()
    return render(request, 'career_app/view_skills.html', {'skills': skills})

@login_required
def edit_skill(request, skill_id):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    skill = Skill.objects.get(id=skill_id)

    form = SkillForm(
        request.POST or None,
        instance=skill
    )

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Skill updated successfully.")
        return redirect('view_skills')

    return render(
        request,
        'career_app/edit_skill.html',
        {
            'form': form,
            'skill': skill
        }
    )


@login_required
def delete_skill(request, skill_id):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    skill = Skill.objects.get(id=skill_id)

    if request.method == 'POST':
        skill.delete()
        messages.success(request, "Skill deleted successfully.")
        return redirect('view_skills')

    return render(
        request,
        'career_app/delete_skill.html',
        {
            'skill': skill
        }
    )
@login_required
def assign_skill_to_role(request):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    form = JobRoleSkillForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        job_role = form.cleaned_data['job_role']

        importance_groups = {
            'High': form.cleaned_data['high_skills'],
            'Medium': form.cleaned_data['medium_skills'],
            'Low': form.cleaned_data['low_skills'],
        }

        for importance, skills in importance_groups.items():
            for skill in skills:
                obj, created = JobRoleSkill.objects.get_or_create(
                    job_role=job_role,
                    skill=skill,
                    defaults={'importance': importance}
                )

                if not created:
                    obj.importance = importance
                    obj.save()

        return redirect('view_role_skills')

    return render(request, 'career_app/assign_skill_to_role.html', {'form': form})


@login_required
def view_role_skills(request):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    role_skills = JobRoleSkill.objects.select_related('job_role', 'skill').all()
    return render(request, 'career_app/view_role_skills.html', {'role_skills': role_skills})

@login_required
def career_match(request):
    form = CareerMatchForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        profile = UserProfile.objects.filter(
            user=request.user
        ).first()

        if not profile:
            return redirect('create_profile')

        result = form.save(commit=False)
        result.user = request.user
        result.save()

        user_skills = (
            profile.extracted_skills.all()
            | profile.manual_skills.all()
        ).distinct()

        result.selected_skills.set(user_skills)

        user_skill_ids = set(
            user_skills.values_list('id', flat=True)
        )

        required_skills = Skill.objects.filter(
            jobroleskill__job_role=result.job_role
        ).distinct()

        if not required_skills.exists():
            result.match_score = 0
            result.save()

            result.matched_skills.clear()
            result.missing_skills.clear()

            return redirect(
                'career_match_result',
                result_id=result.id
            )

        matched_skill_ids = set()
        missing_skill_ids = set()
        grouped_skill_ids = set()

        satisfied_requirement_count = 0
        total_requirement_count = 0

        groups = CompetencyGroup.objects.filter(
            job_role=result.job_role
        ).prefetch_related(
            Prefetch(
                'members',
                queryset=CompetencyGroupMember.objects.select_related(
                    'job_role_skill__skill'
                )
            )
        )

        for group in groups:
            members = list(group.members.all())

            skill_ids = {
                member.job_role_skill.skill_id
                for member in members
            }

            if not skill_ids:
                continue

            grouped_skill_ids.update(skill_ids)

            matched_ids = skill_ids.intersection(
                user_skill_ids
            )

            if group.rule == 'ANY_ONE':

                total_requirement_count += 1

                if matched_ids:
                    satisfied_requirement_count += 1


                    matched_skill_ids.update(matched_ids)


            elif group.rule == 'ALL_REQUIRED':

                total_requirement_count += len(skill_ids)
                satisfied_requirement_count += len(matched_ids)

                matched_skill_ids.update(matched_ids)

                missing_skill_ids.update(
                    skill_ids.difference(user_skill_ids)
                )

        standalone_skills = required_skills.exclude(
            id__in=grouped_skill_ids
        )

        for skill in standalone_skills:
            total_requirement_count += 1

            if skill.id in user_skill_ids:
                satisfied_requirement_count += 1
                matched_skill_ids.add(skill.id)
            else:
                missing_skill_ids.add(skill.id)

        if total_requirement_count > 0:
            match_score = (
                satisfied_requirement_count
                / total_requirement_count
            ) * 100
        else:
            match_score = 0

        result.match_score = round(match_score, 2)
        result.save()

        result.matched_skills.set(
            Skill.objects.filter(
                id__in=matched_skill_ids
            )
        )

        result.missing_skills.set(
            Skill.objects.filter(
                id__in=missing_skill_ids
            )
        )

        return redirect(
            'career_match_result',
            result_id=result.id
        )

    return render(
        request,
        'career_app/career_match.html',
        {
            'form': form
        }
    )
@login_required
def career_match_result(request, result_id):
    result = CareerMatchResult.objects.get(
        id=result_id,
        user=request.user
    )

    user_skill_ids = set(
        result.selected_skills.values_list(
            'id',
            flat=True
        )
    )

    grouped_skill_ids = set()
    competency_results = []

    groups = CompetencyGroup.objects.filter(
        job_role=result.job_role
    ).prefetch_related(
        Prefetch(
            'members',
            queryset=CompetencyGroupMember.objects.select_related(
                'job_role_skill__skill'
            ).order_by(
                'job_role_skill__skill__skill_name'
            )
        )
    ).order_by(
        'group_name'
    )

    for group in groups:
        members = list(
            group.members.all()
        )

        skills = [
            member.job_role_skill.skill
            for member in members
        ]

        skill_ids = {
            skill.id
            for skill in skills
        }

        if not skill_ids:
            continue

        grouped_skill_ids.update(
            skill_ids
        )

        matched_skills = [
            skill
            for skill in skills
            if skill.id in user_skill_ids
        ]

        missing_skills = [
            skill
            for skill in skills
            if skill.id not in user_skill_ids
        ]

        if group.rule == 'ANY_ONE':
            is_satisfied = bool(
                matched_skills
            )

            competency_results.append({
                'group_name': group.group_name,
                'rule': group.rule,
                'rule_label': 'Choose any one',
                'status': (
                    'SATISFIED'
                    if is_satisfied
                    else 'MISSING'
                ),
                'is_satisfied': is_satisfied,
                'is_partial': False,
                'matched_skills': matched_skills,
                'missing_skills': [],
                'options': skills,
            })

        else:
            is_satisfied = (
                len(missing_skills) == 0
            )

            is_partial = (
                bool(matched_skills)
                and bool(missing_skills)
            )

            competency_results.append({
                'group_name': group.group_name,
                'rule': group.rule,
                'rule_label': 'All required',
                'status': (
                    'SATISFIED'
                    if is_satisfied
                    else (
                        'PARTIAL'
                        if is_partial
                        else 'MISSING'
                    )
                ),
                'is_satisfied': is_satisfied,
                'is_partial': is_partial,
                'matched_skills': matched_skills,
                'missing_skills': missing_skills,
                'options': skills,
            })

    standalone_skills = Skill.objects.filter(
        jobroleskill__job_role=result.job_role
    ).exclude(
        id__in=grouped_skill_ids
    ).distinct().order_by(
        'skill_name'
    )

    standalone_results = []

    for skill in standalone_skills:
        is_satisfied = (
            skill.id in user_skill_ids
        )

        standalone_results.append({
            'skill': skill,
            'is_satisfied': is_satisfied,
        })

    missing_all_required_skill_ids = set()

    for competency in competency_results:
        if competency['rule'] == 'ALL_REQUIRED':
            missing_all_required_skill_ids.update(
                skill.id
                for skill in competency['missing_skills']
            )

    missing_standalone_skill_ids = {
        item['skill'].id
        for item in standalone_results
        if not item['is_satisfied']
    }

    learning_skill_ids = (
        missing_all_required_skill_ids
        | missing_standalone_skill_ids
    )

    resources = LearningResource.objects.filter(
        skill_id__in=learning_skill_ids
    ).select_related(
        'skill'
    ).order_by(
        'skill__skill_name',
        'title'
    )

    satisfied_competencies = sum(
        1
        for item in competency_results
        if item['is_satisfied']
    )

    total_competencies = len(
        competency_results
    )

    return render(
        request,
        'career_app/career_match_result.html',
        {
            'result': result,
            'competency_results': competency_results,
            'standalone_results': standalone_results,
            'resources': resources,
            'satisfied_competencies': satisfied_competencies,
            'total_competencies': total_competencies,
        }
    )
@login_required
def add_learning_resource(request):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    form = LearningResourceForm(request.POST or None)

    if form.is_valid():
        form.save()
        return redirect('view_learning_resources')

    return render(
        request,
        'career_app/add_learning_resource.html',
        {'form': form}
    )


@login_required
def view_learning_resources(request):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    resources = LearningResource.objects.select_related('skill')

    return render(
        request,
        'career_app/view_learning_resources.html',
        {'resources': resources}
    )

@login_required
def edit_learning_resource(request, resource_id):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    resource = LearningResource.objects.get(id=resource_id)

    form = LearningResourceForm(
        request.POST or None,
        instance=resource
    )

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Learning resource updated successfully.")
        return redirect('view_learning_resources')

    return render(
        request,
        'career_app/edit_learning_resource.html',
        {
            'form': form,
            'resource': resource
        }
    )


@login_required
def delete_learning_resource(request, resource_id):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    resource = LearningResource.objects.get(id=resource_id)

    if request.method == 'POST':
        resource.delete()
        messages.success(request, "Learning resource deleted successfully.")
        return redirect('view_learning_resources')

    return render(
        request,
        'career_app/delete_learning_resource.html',
        {
            'resource': resource
        }
    )

def generate_ai_learning_roadmap(result):
    client = OpenAI(
        api_key=settings.OPENAI_API_KEY
    )

    user = result.user
    job_role = result.job_role

    profile = UserProfile.objects.filter(
        user=user
    ).first()

    matched_skills = list(
        result.matched_skills.values_list(
            'skill_name',
            flat=True
        )
    )

    missing_skills = list(
        result.missing_skills.values_list(
            'skill_name',
            flat=True
        )
    )

    projects = list(
        UserProject.objects.filter(
            user=user
        ).values(
            'title',
            'description',
            'project_type'
        )
    )

    latest_readiness = ReadinessAssessment.objects.filter(
        user=user,
        job_role=job_role
    ).order_by(
        '-created_at'
    ).first()

    latest_bottleneck = EmployabilityBottleneck.objects.filter(
        user=user,
        job_role=job_role
    ).order_by(
        '-created_at'
    ).first()

    profile_skills = []

    if profile:
        profile_skills = list(
            (
                profile.extracted_skills.all()
                | profile.manual_skills.all()
            ).distinct().values_list(
                'skill_name',
                flat=True
            )
        )

    context = {
        'target_role': job_role.role_name,
        'career_match_score': result.match_score,
        'matched_skills': matched_skills,
        'missing_skills': missing_skills,
        'profile_skills': profile_skills,
        'projects': projects,
        'readiness': (
            {
                'academic_score': latest_readiness.academic_score,
                'industry_score': latest_readiness.industry_score,
                'overall_score': latest_readiness.overall_readiness_score,
                'weaknesses': latest_readiness.weaknesses,
            }
            if latest_readiness
            else None
        ),
        'bottleneck': (
            {
                'name': latest_bottleneck.main_bottleneck,
                'explanation': latest_bottleneck.explanation,
                'recommendation': latest_bottleneck.recommendation,
            }
            if latest_bottleneck
            else None
        ),
    }

    system_prompt = """
You are the Career Action Roadmap generator inside CareerReady AI.

Use ONLY the supplied CareerReady AI evidence.

Do not invent skills, tools, projects, qualifications, experience,
scores, achievements or technologies that are not present in the
supplied evidence.

The purpose of the roadmap is NOT to create a generic study plan.

The roadmap must show how the student can move from their current
career position toward the target role by closing competency gaps,
applying skills practically, producing portfolio evidence and
preparing for employment.

ROADMAP PRINCIPLES:

1. Start from the student's current strengths and detected gaps.

2. Prioritise the most important missing competencies for the target role.

3. Do not simply say "learn X".
   Every phase must connect learning to a concrete action.

4. Where possible, connect the action to one of the student's existing projects.

5. If an existing project is suitable, recommend extending that project
   rather than always recommending a completely new project.

6. Each phase must produce measurable employability evidence.

7. Do not ask the student to relearn competencies they already demonstrate
   unless the supplied evidence clearly indicates that improvement is needed.

8. Include production-oriented actions where relevant, such as testing,
   deployment, scalability, security, documentation or CI/CD.

9. Include portfolio strengthening before the final interview phase.

10. The final phase should focus on interview preparation and job readiness.

11. Do not recalculate or modify any CareerReady AI score.

12. Keep each phase concise, practical and achievable.

Return a structured Career Action Roadmap.

The roadmap must contain:

summary

current_position

phases

final_outcome

Each phase must contain:

title
priority
gap
action
project_application
evidence
expected_outcome
""".strip()

    try:
        response = client.responses.create(
            model='gpt-5',
            instructions=system_prompt,
            input=json.dumps(
                context,
                indent=2,
                default=str
            ),
            text={
                'format': {
                    'type': 'json_schema',
                    'name': 'career_action_roadmap',
                    'strict': True,
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'summary': {
                                'type': 'string'
                            },
                            'current_position': {
                                'type': 'string'
                            },
                            'phases': {
                                'type': 'array',
                                'minItems': 3,
                                'maxItems': 6,
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'title': {
                                            'type': 'string'
                                        },
                                        'priority': {
                                            'type': 'string',
                                            'enum': [
                                                'HIGH',
                                                'MEDIUM',
                                                'LOW'
                                            ]
                                        },
                                        'gap': {
                                            'type': 'string'
                                        },
                                        'action': {
                                            'type': 'string'
                                        },
                                        'project_application': {
                                            'type': 'string'
                                        },
                                        'evidence': {
                                            'type': 'string'
                                        },
                                        'expected_outcome': {
                                            'type': 'string'
                                        },
                                    },
                                    'required': [
                                        'title',
                                        'priority',
                                        'gap',
                                        'action',
                                        'project_application',
                                        'evidence',
                                        'expected_outcome'
                                    ],
                                    'additionalProperties': False,
                                }
                            },
                            'final_outcome': {
                                'type': 'string'
                            },
                        },
                        'required': [
                            'summary',
                            'current_position',
                            'phases',
                            'final_outcome'
                        ],
                        'additionalProperties': False,
                    }
                }
            }
        )

        return json.loads(
            response.output_text
        )

    except Exception as error:
        logger.warning(
            'AI career action roadmap generation failed for '
            'career match result %s: %s',
            result.id,
            error
        )

        return None

@login_required
def learning_roadmap(request, result_id):
    result = get_object_or_404(
        CareerMatchResult,
        id=result_id,
        user=request.user
    )

    roadmap_data = None

    if result.ai_roadmap:
        try:
            roadmap_data = json.loads(
                result.ai_roadmap
            )
        except (TypeError, ValueError):
            roadmap_data = None

    if not roadmap_data:
        return redirect(
            'prepare_learning_roadmap',
            result_id=result.id
        )

    return render(
        request,
        'career_app/learning_roadmap.html',
        {
            'result': result,
            'ai_roadmap': roadmap_data,
            'roadmap_steps': None,
        }
    )

@login_required
def prepare_learning_roadmap(request, result_id):
    result = get_object_or_404(
        CareerMatchResult,
        id=result_id,
        user=request.user
    )

    if result.ai_roadmap:
        return redirect(
            'learning_roadmap',
            result_id=result.id
        )

    if request.method == 'GET':
        return render(
            request,
            'career_app/preparing_learning_roadmap.html',
            {
                'result': result
            }
        )

    roadmap_data = generate_ai_learning_roadmap(
        result
    )

    if roadmap_data:
        result.ai_roadmap = json.dumps(
            roadmap_data
        )

        result.save(
            update_fields=[
                'ai_roadmap'
            ]
        )

        messages.success(
            request,
            'Your personalised AI career roadmap is ready.'
        )

        return redirect(
            'learning_roadmap',
            result_id=result.id
        )

    messages.warning(
        request,
        'AI roadmap generation was unavailable.'
    )

    missing_skills = result.missing_skills.all()

    roadmap_steps = [
        f"Step {index}: Learn {skill.skill_name}"
        for index, skill in enumerate(
            missing_skills,
            start=1
        )
    ]

    roadmap_steps.append(
        f"Build a project related to "
        f"{result.job_role.role_name}"
    )

    return render(
        request,
        'career_app/learning_roadmap.html',
        {
            'result': result,
            'ai_roadmap': None,
            'roadmap_steps': roadmap_steps,
        }
    )
@login_required
def create_profile(request):
    if UserProfile.objects.filter(user=request.user).exists():
        return redirect('view_profile')

    form = UserProfileForm(request.POST or None, request.FILES or None)

    if form.is_valid():
        profile = form.save(commit=False)
        profile.user = request.user
        profile.save()
        form.save_m2m()

        if profile.resume:
            file_path = profile.resume.path

            extracted_text = extract_text_from_resume(file_path)
            profile.extracted_text = extracted_text
            profile.is_resume_valid = is_valid_resume(extracted_text)
            profile.save()

            if profile.is_resume_valid:
                all_skills = Skill.objects.all()
                extracted_skills = extract_skills_from_text(
                    extracted_text,
                    all_skills
                )
                profile.extracted_skills.set(extracted_skills)

        return redirect('view_profile')

    return render(request, 'career_app/create_profile.html', {'form': form})


@login_required
def view_profile(request):
    profile = UserProfile.objects.filter(user=request.user).first()
    return render(request, 'career_app/view_profile.html', {'profile': profile})


@login_required
def edit_profile(request):
    profile = UserProfile.objects.get(user=request.user)

    form = UserProfileForm(
        request.POST or None,
        request.FILES or None,
        instance=profile
    )

    if form.is_valid():
        profile = form.save()

        if profile.resume:
            file_path = profile.resume.path

            extracted_text = extract_text_from_resume(file_path)
            profile.extracted_text = extracted_text
            profile.is_resume_valid = is_valid_resume(extracted_text)
            profile.save()

            if profile.is_resume_valid:
                all_skills = Skill.objects.all()
                extracted_skills = extract_skills_from_text(
                    extracted_text,
                    all_skills
                )
                profile.extracted_skills.set(extracted_skills)
            else:
                profile.extracted_skills.clear()

        return redirect('view_profile')

    return render(request, 'career_app/edit_profile.html', {'form': form})


def generate_ai_readiness_analysis(assessment):
    client = OpenAI(
        api_key=settings.OPENAI_API_KEY
    )

    prompt = f"""
You are analysing a student's career readiness assessment.

Use only the supplied CareerReady AI results.

Target Role:
{assessment.job_role.role_name}

Academic Readiness:
{assessment.academic_score}%

Industry Readiness:
{assessment.industry_score}%

Overall Readiness:
{assessment.overall_readiness_score}%

Strengths:
{assessment.strengths}

Weaknesses:
{assessment.weaknesses}

Rules:
1. Do not change or recalculate any readiness score.
2. Do not invent skills, tools, projects, experience or qualifications.
3. Explain why the student's readiness looks like this.
4. Identify the highest-priority gaps.
5. Give practical actions the student can take.
6. Keep the response concise and career-focused.

Return JSON with:
- analysis
- recommendation
"""

    try:
        response = client.responses.create(
            model='gpt-5',
            input=prompt,
            text={
                'format': {
                    'type': 'json_schema',
                    'name': 'readiness_analysis',
                    'strict': True,
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'analysis': {
                                'type': 'string'
                            },
                            'recommendation': {
                                'type': 'string'
                            }
                        },
                        'required': [
                            'analysis',
                            'recommendation'
                        ],
                        'additionalProperties': False
                    }
                }
            }
        )

        data = json.loads(
            response.output_text
        )

        assessment.ai_analysis = data[
            'analysis'
        ]

        assessment.ai_recommendation = data[
            'recommendation'
        ]

        assessment.save(
            update_fields=[
                'ai_analysis',
                'ai_recommendation'
            ]
        )

    except Exception as error:
        logger.warning(
            'AI readiness analysis failed for assessment %s: %s',
            assessment.id,
            error
        )

def generate_ai_readiness_assessment(user, job_role):
    client = OpenAI(
        api_key=settings.OPENAI_API_KEY
    )
    profile = UserProfile.objects.filter(user=user).first()
    user_skills = []
    user_tools = []
    if profile:
        user_skills = list(
            (
                profile.extracted_skills.all()
                | profile.manual_skills.all()
            ).distinct().values_list(
                'skill_name',
                flat=True
            )
        )

        user_tools = list(
            profile.manual_tools.values_list(
                'tool_name',
                flat=True
            )
        )

    projects = UserProject.objects.filter(
        user=user
    ).prefetch_related(
        'skills_used',
        'tools_used'
    )

    project_evidence = []

    for project in projects:
        project_evidence.append({
            'title': project.title,
            'project_type': (
                project.get_project_type_display()
                if hasattr(
                    project,
                    'get_project_type_display'
                )
                else 'Not specified'
            ),
            'description': project.description or '',
            'skills_used': list(
                project.skills_used.values_list(
                    'skill_name',
                    flat=True
                )
            ),
            'tools_used': list(
                project.tools_used.values_list(
                    'tool_name',
                    flat=True
                )
            ),
        })

    required_skills = list(
        JobRoleSkill.objects.filter(
            job_role=job_role
        ).values(
            'skill__skill_name',
            'importance'
        )
    )

    required_tools = list(
        JobRoleTool.objects.filter(
            job_role=job_role
        ).values(
            'tool__tool_name',
            'importance'
        )
    )

    context = {
        'target_role': job_role.role_name,
        'required_skills': required_skills,
        'required_tools': required_tools,
        'user_skills': user_skills,
        'user_tools': user_tools,
        'projects': project_evidence,
    }

    instructions = """
You are the AI readiness assessment engine inside CareerReady AI.

Evaluate the student's readiness for the supplied target job role.

Use ONLY the evidence and role requirements supplied in the input.

Do not invent:
- skills
- tools
- projects
- experience
- qualifications
- achievements

Evaluate relevance, not simply the number of skills.

Academic Readiness Score:
Score from 0 to 100 based primarily on the student's demonstrated
technical and conceptual competencies relative to the supplied
required role skills.

Industry Readiness Score:
Score from 0 to 100 based primarily on relevant tools and practical
project evidence relative to the supplied role requirements.

Overall Readiness Score:
Score from 0 to 100 representing the student's overall readiness
for the target role.

Important:
- High-importance requirements should influence the assessment more strongly.
- Project-backed evidence is stronger than merely listing a competency.
- Missing important competencies should reduce readiness.
- Do not reward unrelated skills.
- Scores must be consistent with the explanation.
- Be conservative when evidence is weak.
- Clearly explain why the scores were assigned.

Return strengths, weaknesses, recommendations and concise scoring reasoning.
""".strip()

    try:
        response = client.responses.create(
            model='gpt-5',
            instructions=instructions,
            input=json.dumps(
                context,
                indent=2,
                default=str
            ),
            text={
                'format': {
                    'type': 'json_schema',
                    'name': 'ai_readiness_assessment',
                    'strict': True,
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'academic_score': {
                                'type': 'number',
                                'minimum': 0,
                                'maximum': 100
                            },
                            'industry_score': {
                                'type': 'number',
                                'minimum': 0,
                                'maximum': 100
                            },
                            'overall_score': {
                                'type': 'number',
                                'minimum': 0,
                                'maximum': 100
                            },
                            'strengths': {
                                'type': 'string'
                            },
                            'weaknesses': {
                                'type': 'string'
                            },
                            'recommendation': {
                                'type': 'string'
                            },
                            'reasoning': {
                                'type': 'string'
                            }
                        },
                        'required': [
                            'academic_score',
                            'industry_score',
                            'overall_score',
                            'strengths',
                            'weaknesses',
                            'recommendation',
                            'reasoning'
                        ],
                        'additionalProperties': False
                    }
                }
            }
        )

        return json.loads(
            response.output_text
        )

    except Exception as error:
        logger.warning(
            'AI readiness assessment failed for user %s and role %s: %s',
            user.id,
            job_role.id,
            error
        )

        return None
    
@login_required
def readiness_assessment(request):
    form = ReadinessAssessmentForm(
        request.POST or None
    )

    if request.method == 'POST' and form.is_valid():
        assessment = form.save(
            commit=False
        )

        assessment.user = request.user
        job_role = assessment.job_role

        assessment_method = form.cleaned_data.get(
            'assessment_method',
            'RULE_BASED'
        )

        assessment.assessment_method = assessment_method

        if assessment_method == 'AI_POWERED':
            return redirect(
                'prepare_ai_readiness',
                job_role_id=job_role.id
            )

        profile = UserProfile.objects.filter(
            user=request.user
        ).first()

        if profile:
            user_skills = (
                profile.extracted_skills.all()
                | profile.manual_skills.all()
            ).distinct()

            user_tools = profile.manual_tools.all()

        else:
            user_skills = Skill.objects.none()
            user_tools = IndustryTool.objects.none()

        user_skill_ids = set(
            user_skills.values_list(
                'id',
                flat=True
            )
        )

        user_tool_ids = set(
            user_tools.values_list(
                'id',
                flat=True
            )
        )

        required_skills = Skill.objects.filter(
            jobroleskill__job_role=job_role
        ).distinct()

        required_tools = IndustryTool.objects.filter(
            jobroletool__job_role=job_role
        ).distinct()

        matched_skill_ids = set()
        missing_skill_ids = set()
        grouped_skill_ids = set()

        missing_any_one_groups = []
        satisfied_any_one_groups = []

        satisfied_requirement_count = 0
        total_requirement_count = 0

        groups = CompetencyGroup.objects.filter(
            job_role=job_role
        ).order_by(
            'group_name'
        )

        for group in groups:
            members = CompetencyGroupMember.objects.filter(
                group=group
            ).select_related(
                'job_role_skill__skill'
            ).order_by(
                'job_role_skill__skill__skill_name'
            )

            skills = [
                member.job_role_skill.skill
                for member in members
            ]

            skill_ids = {
                skill.id
                for skill in skills
            }

            if not skill_ids:
                continue

            grouped_skill_ids.update(
                skill_ids
            )

            matched_ids = skill_ids.intersection(
                user_skill_ids
            )

            if group.rule == 'ANY_ONE':

                total_requirement_count += 1

                if matched_ids:
                    satisfied_requirement_count += 1

                    matched_skill_ids.update(
                        matched_ids
                    )

                    matched_names = [
                        skill.skill_name
                        for skill in skills
                        if skill.id in matched_ids
                    ]

                    satisfied_any_one_groups.append({
                        'group_name': group.group_name,
                        'matched_skills': matched_names,
                    })

                else:
                    option_names = [
                        skill.skill_name
                        for skill in skills
                    ]

                    missing_any_one_groups.append({
                        'group_name': group.group_name,
                        'options': option_names,
                    })

            elif group.rule == 'ALL_REQUIRED':

                total_requirement_count += len(
                    skill_ids
                )

                satisfied_requirement_count += len(
                    matched_ids
                )

                matched_skill_ids.update(
                    matched_ids
                )

                missing_skill_ids.update(
                    skill_ids.difference(
                        user_skill_ids
                    )
                )

        standalone_skills = required_skills.exclude(
            id__in=grouped_skill_ids
        )

        for skill in standalone_skills:
            total_requirement_count += 1

            if skill.id in user_skill_ids:
                satisfied_requirement_count += 1
                matched_skill_ids.add(
                    skill.id
                )
            else:
                missing_skill_ids.add(
                    skill.id
                )

        matched_skills = Skill.objects.filter(
            id__in=matched_skill_ids
        ).order_by(
            'skill_name'
        )

        missing_skills = Skill.objects.filter(
            id__in=missing_skill_ids
        ).order_by(
            'skill_name'
        )

        if total_requirement_count > 0:
            academic_score = (
                satisfied_requirement_count
                / total_requirement_count
            ) * 100
        else:
            academic_score = 0

        required_tool_ids = set(
            required_tools.values_list(
                'id',
                flat=True
            )
        )

        matched_tool_ids = required_tool_ids.intersection(
            user_tool_ids
        )

        missing_tool_ids = required_tool_ids.difference(
            user_tool_ids
        )

        matched_tools = IndustryTool.objects.filter(
            id__in=matched_tool_ids
        ).order_by(
            'tool_name'
        )

        missing_tools = IndustryTool.objects.filter(
            id__in=missing_tool_ids
        ).order_by(
            'tool_name'
        )

        if required_tool_ids:
            industry_score = (
                len(matched_tool_ids)
                / len(required_tool_ids)
            ) * 100
        else:
            industry_score = 0

        overall_score = (
            academic_score * 0.6
        ) + (
            industry_score * 0.4
        )

        assessment.academic_score = round(
            academic_score,
            2
        )

        assessment.industry_score = round(
            industry_score,
            2
        )

        assessment.overall_readiness_score = round(
            overall_score,
            2
        )

        matched_skill_names = list(
            matched_skills.values_list(
                'skill_name',
                flat=True
            )
        )

        missing_skill_names = list(
            missing_skills.values_list(
                'skill_name',
                flat=True
            )
        )

        matched_tool_names = list(
            matched_tools.values_list(
                'tool_name',
                flat=True
            )
        )

        missing_tool_names = list(
            missing_tools.values_list(
                'tool_name',
                flat=True
            )
        )

        strength_parts = []

        if matched_skill_names:
            strength_parts.append(
                "Matched Skills: "
                + ", ".join(
                    matched_skill_names
                )
            )
        else:
            strength_parts.append(
                "Matched Skills: None"
            )

        for group_data in satisfied_any_one_groups:
            matched_options = ", ".join(
                group_data['matched_skills']
            )

            strength_parts.append(
                f"{group_data['group_name']}: "
                f"satisfied with {matched_options}"
            )

        if matched_tool_names:
            strength_parts.append(
                "Matched Tools: "
                + ", ".join(
                    matched_tool_names
                )
            )
        else:
            strength_parts.append(
                "Matched Tools: None"
            )

        assessment.strengths = "\n\n".join(
            strength_parts
        )

        weakness_parts = []

        if missing_skill_names:
            weakness_parts.append(
                "Missing Required Skills: "
                + ", ".join(
                    missing_skill_names
                )
            )

        for group_data in missing_any_one_groups:
            options = ", ".join(
                group_data['options']
            )

            weakness_parts.append(
                f"{group_data['group_name']}: "
                f"choose any one of {options}"
            )

        if missing_tool_names:
            weakness_parts.append(
                "Missing Tools: "
                + ", ".join(
                    missing_tool_names
                )
            )

        if not weakness_parts:
            weakness_parts.append(
                "No major skill or tool gaps found."
            )

        assessment.weaknesses = "\n\n".join(
            weakness_parts
        )

        if overall_score >= 75:
            assessment.recommendation = (
                "You are close to industry-ready for this role. "
                "Focus on portfolio projects and interview preparation."
            )

        elif overall_score >= 50:
            assessment.recommendation = (
                "You have a moderate readiness level. "
                "Complete the missing competencies, improve required "
                "tools, and build practical projects."
            )

        else:
            assessment.recommendation = (
                "Your readiness is low for this role. "
                "Start with the missing core competencies and required "
                "industry tools before applying."
            )

        assessment.save()

        return redirect(
            'readiness_result',
            assessment_id=assessment.id
        )

    return render(
        request,
        'career_app/readiness_assessment.html',
        {
            'form': form
        }
    )

@login_required
def prepare_ai_readiness(request, job_role_id):
    job_role = get_object_or_404(
        JobRole,
        id=job_role_id
    )

    if request.method == 'GET':
        return render(
            request,
            'career_app/preparing_ai_readiness.html',
            {
                'job_role': job_role
            }
        )

    ai_result = generate_ai_readiness_assessment(
        request.user,
        job_role
    )

    if not ai_result:
        messages.error(
            request,
            'AI readiness assessment could not be generated. Please try again.'
        )

        return redirect(
            'readiness_assessment'
        )

    assessment = ReadinessAssessment.objects.create(
        user=request.user,
        job_role=job_role,
        academic_score=round(
            ai_result['academic_score'],
            2
        ),
        industry_score=round(
            ai_result['industry_score'],
            2
        ),
        overall_readiness_score=round(
            ai_result['overall_score'],
            2
        ),
        strengths=ai_result['strengths'],
        weaknesses=ai_result['weaknesses'],
        recommendation=ai_result['recommendation'],
        ai_analysis=ai_result['reasoning'],
        ai_recommendation=ai_result['recommendation'],
        assessment_method='AI_POWERED'
    )

    messages.success(
        request,
        'Your AI-powered career readiness assessment is ready.'
    )

    return redirect(
        'readiness_result',
        assessment_id=assessment.id
    )


@login_required
def readiness_result(request, assessment_id):
    assessment = ReadinessAssessment.objects.get(
        id=assessment_id,
        user=request.user
    )

    return render(
        request,
        'career_app/readiness_result.html',
        {'assessment': assessment}
    )
@login_required
def add_industry_tool(request):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    form = IndustryToolForm(request.POST or None)

    if form.is_valid():
        form.save()
        return redirect('view_industry_tools')

    return render(request, 'career_app/add_industry_tool.html', {'form': form})


@login_required
def view_industry_tools(request):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    tools = IndustryTool.objects.all()
    return render(request, 'career_app/view_industry_tools.html', {'tools': tools})

@login_required
def edit_industry_tool(request, tool_id):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    tool = IndustryTool.objects.get(id=tool_id)

    form = IndustryToolForm(
        request.POST or None,
        instance=tool
    )

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Industry tool updated successfully.")
        return redirect('view_industry_tools')

    return render(
        request,
        'career_app/edit_industry_tool.html',
        {
            'form': form,
            'tool': tool
        }
    )


@login_required
def delete_industry_tool(request, tool_id):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    tool = IndustryTool.objects.get(id=tool_id)

    if request.method == 'POST':
        tool.delete()
        messages.success(request, "Industry tool deleted successfully.")
        return redirect('view_industry_tools')

    return render(
        request,
        'career_app/delete_industry_tool.html',
        {
            'tool': tool
        }
    )

@login_required
def assign_tool_to_role(request):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    form = JobRoleToolForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        job_role = form.cleaned_data['job_role']

        importance_groups = {
            'High': form.cleaned_data['high_tools'],
            'Medium': form.cleaned_data['medium_tools'],
            'Low': form.cleaned_data['low_tools'],
        }

        for importance, tools in importance_groups.items():
            for tool in tools:
                obj, created = JobRoleTool.objects.get_or_create(
                    job_role=job_role,
                    tool=tool,
                    defaults={'importance': importance}
                )

                if not created:
                    obj.importance = importance
                    obj.save()

        return redirect('view_role_tools')

    return render(request, 'career_app/assign_tool_to_role.html', {'form': form})


@login_required
def view_role_tools(request):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    role_tools = JobRoleTool.objects.select_related('job_role', 'tool').all()
    return render(request, 'career_app/view_role_tools.html', {'role_tools': role_tools})

def generate_ai_bottleneck_analysis(bottleneck):
    client = OpenAI(
        api_key=settings.OPENAI_API_KEY
    )

    user = bottleneck.user
    job_role = bottleneck.job_role
    assessment = bottleneck.readiness_assessment

    profile = UserProfile.objects.filter(
        user=user
    ).first()

    user_skills = []
    user_tools = []

    if profile:
        user_skills = list(
            (
                profile.extracted_skills.all()
                | profile.manual_skills.all()
            ).distinct().values_list(
                'skill_name',
                flat=True
            )
        )

        user_tools = list(
            profile.manual_tools.values_list(
                'tool_name',
                flat=True
            )
        )

    projects = UserProject.objects.filter(
        user=user
    ).prefetch_related(
        'skills_used',
        'tools_used'
    )

    project_evidence = []

    for project in projects:
        project_evidence.append({
            'title': project.title,
            'project_type': (
                project.get_project_type_display()
                if hasattr(
                    project,
                    'get_project_type_display'
                )
                else 'Not specified'
            ),
            'description': project.description or '',
            'skills_used': list(
                project.skills_used.values_list(
                    'skill_name',
                    flat=True
                )
            ),
            'tools_used': list(
                project.tools_used.values_list(
                    'tool_name',
                    flat=True
                )
            ),
        })

    required_skills = list(
        JobRoleSkill.objects.filter(
            job_role=job_role
        ).values(
            'skill__skill_name',
            'importance'
        )
    )

    required_tools = list(
        JobRoleTool.objects.filter(
            job_role=job_role
        ).values(
            'tool__tool_name',
            'importance'
        )
    )

    context = {
        'target_role': job_role.role_name,
        'detected_bottleneck': bottleneck.main_bottleneck,
        'rule_based_explanation': bottleneck.explanation,
        'rule_based_recommendation': bottleneck.recommendation,
        'readiness': {
            'academic_score': (
                assessment.academic_score
                if assessment
                else None
            ),
            'industry_score': (
                assessment.industry_score
                if assessment
                else None
            ),
            'overall_score': (
                assessment.overall_readiness_score
                if assessment
                else None
            ),
        },
        'user_skills': user_skills,
        'user_tools': user_tools,
        'required_skills': required_skills,
        'required_tools': required_tools,
        'projects': project_evidence,
    }

    instructions = """
You are the AI employability bottleneck analysis engine
inside CareerReady AI.

The rule-based system has already identified the student's
primary employability bottleneck.

Do NOT replace or change that detected bottleneck.

Use ONLY the supplied evidence.

Do not invent:
- skills
- tools
- projects
- work experience
- qualifications
- achievements

Your job is to interpret and prioritise the existing diagnosis.

Return:

1. severity
   Must be one of:
   LOW
   MODERATE
   HIGH

2. analysis
   Explain why the detected bottleneck is limiting readiness
   for the selected target role.

3. priority_gaps
   Identify the most important gaps the student should address
   first. Prioritise high-importance role requirements and
   evidence weaknesses.

4. action_plan
   Give a concise, practical improvement plan.
   Connect actions to existing projects where appropriate.

Important:
- Do not recalculate readiness scores.
- Do not change the detected bottleneck.
- Do not recommend unrelated technologies.
- Prefer project-backed practical actions.
- Be concise and specific.
""".strip()

    try:
        response = client.responses.create(
            model='gpt-5',
            instructions=instructions,
            input=json.dumps(
                context,
                indent=2,
                default=str
            ),
            text={
                'format': {
                    'type': 'json_schema',
                    'name': 'ai_bottleneck_analysis',
                    'strict': True,
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'severity': {
                                'type': 'string',
                                'enum': [
                                    'LOW',
                                    'MODERATE',
                                    'HIGH'
                                ]
                            },
                            'analysis': {
                                'type': 'string'
                            },
                            'priority_gaps': {
                                'type': 'string'
                            },
                            'action_plan': {
                                'type': 'string'
                            }
                        },
                        'required': [
                            'severity',
                            'analysis',
                            'priority_gaps',
                            'action_plan'
                        ],
                        'additionalProperties': False
                    }
                }
            }
        )

        return json.loads(
            response.output_text
        )

    except Exception as error:
        logger.warning(
            'AI bottleneck analysis failed for bottleneck %s: %s',
            bottleneck.id,
            error
        )

        return None
@login_required
def bottleneck_detection(request):
    form = BottleneckForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        job_role = form.cleaned_data['job_role']

        assessment = ReadinessAssessment.objects.filter(
            user=request.user,
            job_role=job_role
        ).order_by('-created_at').first()

        if not assessment:
            messages.warning(
                request,
                'Please complete a readiness assessment for this role first.'
            )
            return redirect('readiness_assessment')

        projects = UserProject.objects.filter(
            user=request.user
        )

        project_count = projects.count()

        required_skills = Skill.objects.filter(
            jobroleskill__job_role=job_role
        ).distinct()

        required_tools = IndustryTool.objects.filter(
            jobroletool__job_role=job_role
        ).distinct()

        project_skill_ids = set()
        project_tool_ids = set()

        for project in projects:
            project_skill_ids.update(
                project.skills_used.values_list(
                    'id',
                    flat=True
                )
            )

            project_tool_ids.update(
                project.tools_used.values_list(
                    'id',
                    flat=True
                )
            )

        matched_project_skill_ids = set()
        missing_project_skill_ids = set()
        grouped_skill_ids = set()

        groups = CompetencyGroup.objects.filter(
            job_role=job_role
        )

        for group in groups:
            members = CompetencyGroupMember.objects.filter(
                group=group
            ).select_related(
                'job_role_skill__skill'
            )

            skills = [
                member.job_role_skill.skill
                for member in members
            ]

            skill_ids = {
                skill.id
                for skill in skills
            }

            grouped_skill_ids.update(
                skill_ids
            )

            if group.rule == 'ANY_ONE':
                matched = skill_ids.intersection(
                    project_skill_ids
                )

                if matched:
                    matched_project_skill_ids.add(
                        next(iter(matched))
                    )

                else:
                    missing_project_skill_ids.update(
                        skill_ids
                    )

            else:
                for skill in skills:
                    if skill.id in project_skill_ids:
                        matched_project_skill_ids.add(
                            skill.id
                        )
                    else:
                        missing_project_skill_ids.add(
                            skill.id
                        )

        normal_required_skills = required_skills.exclude(
            id__in=grouped_skill_ids
        )

        for skill in normal_required_skills:
            if skill.id in project_skill_ids:
                matched_project_skill_ids.add(
                    skill.id
                )
            else:
                missing_project_skill_ids.add(
                    skill.id
                )

        required_tool_ids = set(
            required_tools.values_list(
                'id',
                flat=True
            )
        )

        relevant_project_tools = (
            project_tool_ids.intersection(
                required_tool_ids
            )
        )

        missing_project_tool_ids = (
            required_tool_ids.difference(
                project_tool_ids
            )
        )

        total_skill_items = (
            len(matched_project_skill_ids)
            + len(missing_project_skill_ids)
        )

        if total_skill_items > 0:
            project_skill_coverage = round(
                (
                    len(matched_project_skill_ids)
                    / total_skill_items
                ) * 100,
                2
            )
        else:
            project_skill_coverage = 0

        if len(required_tool_ids) > 0:
            project_tool_coverage = round(
                (
                    len(relevant_project_tools)
                    / len(required_tool_ids)
                ) * 100,
                2
            )
        else:
            project_tool_coverage = 0

        total_required_items = (
            total_skill_items
            + len(required_tool_ids)
        )

        total_relevant_items = (
            len(matched_project_skill_ids)
            + len(relevant_project_tools)
        )

        if total_required_items > 0:
            project_relevance_score = round(
                (
                    total_relevant_items
                    / total_required_items
                ) * 100,
                2
            )
        else:
            project_relevance_score = 0

        missing_project_skills = Skill.objects.filter(
            id__in=missing_project_skill_ids
        )

        missing_project_tools = IndustryTool.objects.filter(
            id__in=missing_project_tool_ids
        )

        missing_skill_names = ', '.join(
            missing_project_skills.values_list(
                'skill_name',
                flat=True
            )
        )

        missing_tool_names = ', '.join(
            missing_project_tools.values_list(
                'tool_name',
                flat=True
            )
        )

        bottleneck = EmployabilityBottleneck(
            user=request.user,
            job_role=job_role,
            readiness_assessment=assessment
        )

        if assessment.academic_score < 50:
            bottleneck.main_bottleneck = (
                'Skill Deficiency'
            )

            bottleneck.explanation = (
                f'Your academic readiness score is '
                f'{assessment.academic_score}%, which means '
                f'your core skill foundation for '
                f'{job_role.role_name} is weak.'
            )

            bottleneck.recommendation = (
                'First improve the missing core skills for '
                'this role before focusing on projects.'
            )

        elif assessment.industry_score < 50:
            bottleneck.main_bottleneck = (
                'Industry Tool Deficiency'
            )

            bottleneck.explanation = (
                f'Your industry tool readiness score is '
                f'{assessment.industry_score}%, which means '
                f'you are missing important tools required '
                f'for {job_role.role_name}.'
            )

            bottleneck.recommendation = (
                'Learn the missing tools and use them '
                'inside practical projects.'
            )

        elif project_count == 0:
            bottleneck.main_bottleneck = (
                'Lack of Practical Projects'
            )

            bottleneck.explanation = (
                'You have not added any projects to prove '
                'practical experience.'
            )

            bottleneck.recommendation = (
                f'Add at least one {job_role.role_name} '
                f'project and map the skills/tools used.'
            )

        elif project_skill_coverage < 50:
            bottleneck.main_bottleneck = (
                'Weak Project Skill Evidence'
            )

            bottleneck.explanation = (
                f'You added {project_count} project(s), but '
                f'they only prove {project_skill_coverage}% '
                f'of the required skill competencies for '
                f'{job_role.role_name}.'
            )

            bottleneck.recommendation = (
                f'Strengthen your projects using missing '
                f'role skills such as: '
                f'{missing_skill_names if missing_skill_names else "more target-role skills"}.'
            )

        elif project_tool_coverage < 50:
            bottleneck.main_bottleneck = (
                'Weak Project Tool Evidence'
            )

            bottleneck.explanation = (
                f'You added {project_count} project(s), but '
                f'they only show {project_tool_coverage}% '
                f'of the required tools for '
                f'{job_role.role_name}.'
            )

            bottleneck.recommendation = (
                f'Update your projects to include tools '
                f'such as: '
                f'{missing_tool_names if missing_tool_names else "more industry tools"}.'
            )

        elif project_relevance_score < 70:
            bottleneck.main_bottleneck = (
                'Weak Project Relevance'
            )

            bottleneck.explanation = (
                f'You added {project_count} project(s), but '
                f'their combined relevance score is only '
                f'{project_relevance_score}% for '
                f'{job_role.role_name}.'
            )

            bottleneck.recommendation = (
                'Build one stronger role-specific project '
                'instead of adding many weak or unrelated '
                'projects.'
            )

        elif assessment.overall_readiness_score < 75:
            bottleneck.main_bottleneck = (
                'Moderate Readiness'
            )

            bottleneck.explanation = (
                f'Your projects are relevant, but your '
                f'overall readiness score is '
                f'{assessment.overall_readiness_score}%, '
                f'which is still below industry-ready level.'
            )

            bottleneck.recommendation = (
                'Improve your weakest readiness area and '
                'polish your best project into portfolio '
                'quality.'
            )

        else:
            bottleneck.main_bottleneck = (
                'No Major Bottleneck'
            )

            bottleneck.explanation = (
                f'You appear ready for '
                f'{job_role.role_name} based on your '
                f'current skills, tools, and projects.'
            )

            bottleneck.recommendation = (
                'Focus on interview preparation, '
                'portfolio polishing, and job applications.'
            )

        bottleneck.save()

        return redirect(
            'prepare_ai_bottleneck',
            bottleneck_id=bottleneck.id
        )

    return render(
        request,
        'career_app/bottleneck_detection.html',
        {
            'form': form
        }
    )


@login_required
def prepare_ai_bottleneck(request, bottleneck_id):
    bottleneck = get_object_or_404(
        EmployabilityBottleneck,
        id=bottleneck_id,
        user=request.user
    )

    if request.method == 'POST':
        try:
            ai_result = generate_ai_bottleneck_analysis(
                bottleneck
            )

            if ai_result:
                bottleneck.ai_severity = ai_result.get(
                    'severity',
                    ''
                )

                bottleneck.ai_analysis = ai_result.get(
                    'analysis',
                    ''
                )

                bottleneck.ai_priority_gaps = ai_result.get(
                    'priority_gaps',
                    ''
                )

                bottleneck.ai_action_plan = ai_result.get(
                    'action_plan',
                    ''
                )

                bottleneck.save(
                    update_fields=[
                        'ai_severity',
                        'ai_analysis',
                        'ai_priority_gaps',
                        'ai_action_plan'
                    ]
                )

        except Exception as error:
            print(
                'AI bottleneck analysis error:',
                error
            )

            messages.warning(
                request,
                'The bottleneck was detected, but the AI analysis '
                'could not be generated.'
            )

        return redirect(
            'bottleneck_result',
            bottleneck_id=bottleneck.id
        )

    return render(
        request,
        'career_app/prepare_ai_bottleneck.html',
        {
            'bottleneck': bottleneck
        }
    )
@login_required
def bottleneck_result(request, bottleneck_id):
    bottleneck = EmployabilityBottleneck.objects.get(
        id=bottleneck_id,
        user=request.user
    )

    return render(
        request,
        'career_app/bottleneck_result.html',
        {'bottleneck': bottleneck}
    )

@login_required
def add_project(request):

    form = UserProjectForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():

            project = form.save(commit=False)
            project.user = request.user
            project.save()

            form.save_m2m()

            return redirect('view_projects')

    return render(
        request,
        'career_app/add_project.html',
        {'form': form}
    )

@login_required
def view_projects(request):

    projects = UserProject.objects.filter(
        user=request.user
    )

    return render(
        request,
        'career_app/view_projects.html',
        {'projects': projects}
    )

@login_required
def delete_project(request, project_id):
    project = UserProject.objects.get(
        id=project_id,
        user=request.user
    )

    project.delete()

    return redirect('view_projects')


def generate_ai_career_transition_analysis(analysis):
    """
    Interpret an existing CareerReady AI career transition analysis.

    The deterministic transition engine remains responsible for:
    - skill match score
    - tool match score
    - feasibility score
    - difficulty level
    - missing skills
    - missing tools

    AI only interprets those results and generates personalised
    transition guidance.
    """

    client = OpenAI(
        api_key=settings.OPENAI_API_KEY
    )

    user = analysis.user
    current_role = analysis.current_role
    target_role = analysis.target_role

    profile = UserProfile.objects.filter(
        user=user
    ).first()

    user_skills = []
    user_tools = []

    if profile:
        user_skills = list(
            (
                profile.extracted_skills.all()
                | profile.manual_skills.all()
            ).distinct().values_list(
                'skill_name',
                flat=True
            )
        )

        user_tools = list(
            profile.manual_tools.values_list(
                'tool_name',
                flat=True
            )
        )

    # --------------------------------------------------
    # Current-role requirements
    # --------------------------------------------------

    current_role_skills = list(
        JobRoleSkill.objects.filter(
            job_role=current_role
        ).values(
            'skill__skill_name',
            'importance'
        )
    )

    current_role_tools = list(
        JobRoleTool.objects.filter(
            job_role=current_role
        ).values(
            'tool__tool_name',
            'importance'
        )
    )

    # --------------------------------------------------
    # Target-role requirements
    # --------------------------------------------------

    target_role_skills = list(
        JobRoleSkill.objects.filter(
            job_role=target_role
        ).values(
            'skill__skill_name',
            'importance'
        )
    )

    target_role_tools = list(
        JobRoleTool.objects.filter(
            job_role=target_role
        ).values(
            'tool__tool_name',
            'importance'
        )
    )

    # --------------------------------------------------
    # Projects
    # --------------------------------------------------

    projects = UserProject.objects.filter(
        user=user
    ).prefetch_related(
        'skills_used',
        'tools_used'
    )

    project_evidence = []

    for project in projects:
        project_evidence.append({
            'title': project.title,
            'project_type': (
                project.get_project_type_display()
                if hasattr(
                    project,
                    'get_project_type_display'
                )
                else 'Not specified'
            ),
            'description': project.description or '',
            'skills_used': list(
                project.skills_used.values_list(
                    'skill_name',
                    flat=True
                )
            ),
            'tools_used': list(
                project.tools_used.values_list(
                    'tool_name',
                    flat=True
                )
            ),
        })

    context = {
        'current_role': current_role.role_name,
        'target_role': target_role.role_name,

        'deterministic_transition_analysis': {
            'skill_match_score': (
                analysis.skill_match_score
            ),
            'tool_match_score': (
                analysis.tool_match_score
            ),
            'feasibility_score': (
                analysis.feasibility_score
            ),
            'difficulty_level': (
                analysis.difficulty_level
            ),
            'missing_skills': (
                analysis.missing_skills or ''
            ),
            'missing_tools': (
                analysis.missing_tools or ''
            ),
            'recommendation': (
                analysis.recommendation
            ),
        },

        'user_evidence': {
            'skills': user_skills,
            'tools': user_tools,
            'projects': project_evidence,
        },

        'current_role_requirements': {
            'skills': current_role_skills,
            'tools': current_role_tools,
        },

        'target_role_requirements': {
            'skills': target_role_skills,
            'tools': target_role_tools,
        },
    }

    instructions = """
You are the AI Career Transition Advisor inside CareerReady AI.

CareerReady AI has already performed a deterministic career-transition
feasibility analysis.

The deterministic system has already calculated:

- skill match score
- tool match score
- overall feasibility score
- transition difficulty
- missing skills
- missing tools

DO NOT recalculate, replace, alter or contradict these values.

Your responsibility is to interpret the existing transition analysis
and provide personalised career-transition guidance.

Use ONLY the supplied CareerReady AI evidence.

Do not invent:
- skills
- tools
- projects
- work experience
- qualifications
- achievements
- certifications
- technologies

IMPORTANT RULES:

1. Explain why the transition has the supplied feasibility level.

2. Identify transferable strengths that genuinely help the candidate
   move from the current role toward the target role.

3. Transferable strengths must be supported by supplied user evidence
   and/or overlap between current-role and target-role requirements.

4. Identify the highest-priority gaps from the supplied missing
   skills and tools.

5. High-importance target-role requirements should receive greater
   attention than lower-priority requirements.

6. Give a practical transition plan in a sensible order.

7. Where appropriate, recommend extending an existing project to
   demonstrate a missing target-role competency.

8. Do not tell the candidate to relearn competencies they already
   demonstrate unless improvement is clearly necessary.

9. Do not change the deterministic difficulty classification.

10. Do not generate a new percentage or numerical transition score.

11. Keep the response practical, concise and career-focused.

Return exactly:

analysis
transferable_strengths
priority_gaps
action_plan
""".strip()

    try:
        response = client.responses.create(
            model='gpt-5',
            instructions=instructions,
            input=json.dumps(
                context,
                indent=2,
                default=str
            ),
            text={
                'format': {
                    'type': 'json_schema',
                    'name': 'career_transition_ai_analysis',
                    'strict': True,
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'analysis': {
                                'type': 'string'
                            },
                            'transferable_strengths': {
                                'type': 'string'
                            },
                            'priority_gaps': {
                                'type': 'string'
                            },
                            'action_plan': {
                                'type': 'string'
                            }
                        },
                        'required': [
                            'analysis',
                            'transferable_strengths',
                            'priority_gaps',
                            'action_plan'
                        ],
                        'additionalProperties': False
                    }
                }
            }
        )

        return json.loads(
            response.output_text
        )

    except Exception as error:
        logger.warning(
            'AI career transition analysis failed '
            'for analysis %s: %s',
            analysis.id,
            error
        )

        return None
    
@login_required
def career_transition_analysis(request):
    form = CareerTransitionForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        current_role = form.cleaned_data['current_role']
        target_role = form.cleaned_data['target_role']

        if current_role == target_role:
            messages.error(request, "Current role and target role cannot be the same.")
            return redirect('career_transition_analysis')

        profile = UserProfile.objects.filter(user=request.user).first()

        if not profile:
            return redirect('create_profile')

        user_skills = (
            profile.extracted_skills.all() | profile.manual_skills.all()
        ).distinct()

        user_tools = profile.manual_tools.all()

        target_required_skills = Skill.objects.filter(
            jobroleskill__job_role=target_role
        ).distinct()

        target_required_tools = IndustryTool.objects.filter(
            jobroletool__job_role=target_role
        ).distinct()

        matched_skill_ids = set()
        missing_skill_ids = set()

        user_skill_ids = set(
            user_skills.values_list('id', flat=True)
        )

        grouped_skill_ids = set()

        groups = CompetencyGroup.objects.filter(
            job_role=target_role
        )

        for group in groups:
            members = CompetencyGroupMember.objects.filter(
                group=group
            ).select_related('job_role_skill__skill')

            skills = [
                member.job_role_skill.skill
                for member in members
            ]

            skill_ids = {
                skill.id
                for skill in skills
            }

            grouped_skill_ids.update(skill_ids)

            if group.rule == "ANY_ONE":
                matched = skill_ids.intersection(user_skill_ids)

                if matched:
                    matched_skill_ids.add(next(iter(matched)))
                else:
                    missing_skill_ids.update(skill_ids)

            else:
                for skill in skills:
                    if skill.id in user_skill_ids:
                        matched_skill_ids.add(skill.id)
                    else:
                        missing_skill_ids.add(skill.id)

        normal_skills = target_required_skills.exclude(
            id__in=grouped_skill_ids
        )

        for skill in normal_skills:
            if skill.id in user_skill_ids:
                matched_skill_ids.add(skill.id)
            else:
                missing_skill_ids.add(skill.id)

        matched_skills = Skill.objects.filter(
            id__in=matched_skill_ids
        )

        missing_skills = Skill.objects.filter(
            id__in=missing_skill_ids
        )

        total_required_skills = len(matched_skill_ids) + len(missing_skill_ids)

        if total_required_skills > 0:
            skill_match_score = (
                len(matched_skill_ids) / total_required_skills
            ) * 100
        else:
            skill_match_score = 0

        matched_tools = user_tools.filter(
            id__in=target_required_tools.values_list('id', flat=True)
        )

        missing_tools = target_required_tools.exclude(
            id__in=user_tools.values_list('id', flat=True)
        )

        if target_required_tools.count() > 0:
            tool_match_score = (
                matched_tools.count() / target_required_tools.count()
            ) * 100
        else:
            tool_match_score = 0

        feasibility_score = (skill_match_score * 0.7) + (tool_match_score * 0.3)

        if feasibility_score >= 75:
            difficulty_level = "Easy Transition"
            recommendation = (
                f"Transition from {current_role.role_name} to {target_role.role_name} is realistic. "
                "Focus on portfolio projects and interview preparation."
            )
        elif feasibility_score >= 50:
            difficulty_level = "Moderate Transition"
            recommendation = (
                f"Transition from {current_role.role_name} to {target_role.role_name} is possible, "
                "but you need to close the missing skill and tool gaps first."
            )
        else:
            difficulty_level = "Difficult Transition"
            recommendation = (
                f"Transition from {current_role.role_name} to {target_role.role_name} is currently difficult. "
                "Build foundational skills and tools before targeting this role."
            )

        analysis = CareerTransitionAnalysis.objects.create(
            user=request.user,
            current_role=current_role,
            target_role=target_role,
            skill_match_score=round(skill_match_score, 2),
            tool_match_score=round(tool_match_score, 2),
            feasibility_score=round(feasibility_score, 2),
            difficulty_level=difficulty_level,
            missing_skills=", ".join(
                missing_skills.values_list('skill_name', flat=True)
            ),
            missing_tools=", ".join(
                missing_tools.values_list('tool_name', flat=True)
            ),
            recommendation=recommendation
        )

        return redirect(
            'prepare_ai_career_transition',
            analysis_id=analysis.id
        )

    return render(
        request,
        'career_app/career_transition_analysis.html',
        {'form': form}
    )

@login_required
def prepare_ai_career_transition(
    request,
    analysis_id
):
    analysis = get_object_or_404(
        CareerTransitionAnalysis.objects.select_related(
            'current_role',
            'target_role'
        ),
        id=analysis_id,
        user=request.user
    )

    # If AI analysis already exists,
    # don't generate it again.
    if analysis.ai_analysis:
        return redirect(
            'career_transition_result',
            analysis_id=analysis.id
        )

    # GET displays the loading page.
    if request.method == 'GET':
        return render(
            request,
            'career_app/preparing_ai_career_transition.html',
            {
                'analysis': analysis
            }
        )

    # POST performs the actual AI request.
    ai_result = generate_ai_career_transition_analysis(
        analysis
    )

    if ai_result:
        analysis.ai_analysis = ai_result.get(
            'analysis',
            ''
        )

        analysis.ai_transferable_strengths = ai_result.get(
            'transferable_strengths',
            ''
        )

        analysis.ai_priority_gaps = ai_result.get(
            'priority_gaps',
            ''
        )

        analysis.ai_action_plan = ai_result.get(
            'action_plan',
            ''
        )

        analysis.save(
            update_fields=[
                'ai_analysis',
                'ai_transferable_strengths',
                'ai_priority_gaps',
                'ai_action_plan'
            ]
        )

        messages.success(
            request,
            'AI career transition analysis generated successfully.'
        )

    else:
        messages.warning(
            request,
            'The transition was analysed, but the AI guidance '
            'could not be generated.'
        )

    return redirect(
        'career_transition_result',
        analysis_id=analysis.id
    )

@login_required
def career_transition_result(request, analysis_id):
    analysis = CareerTransitionAnalysis.objects.get(
        id=analysis_id,
        user=request.user
    )

    return render(
        request,
        'career_app/career_transition_result.html',
        {'analysis': analysis}
    )
@login_required
def import_dataset(request):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    form = DatasetImportForm(
        request.POST or None,
        request.FILES or None
    )

    if request.method != 'POST' or not form.is_valid():
        return render(
            request,
            'career_app/import_dataset.html',
            {
                'form': form
            }
        )

    dataset_file = request.FILES['dataset_file']

    try:
        workbook = load_workbook(
            dataset_file,
            data_only=True
        )
    except Exception as error:
        messages.error(
            request,
            f"Could not open the Excel file: {error}"
        )

        return render(
            request,
            'career_app/import_dataset.html',
            {
                'form': form
            }
        )

    summary = {
        'created': {
            'roles': 0,
            'skills': 0,
            'tools': 0,
            'role_skills': 0,
            'role_tools': 0,
            'resources': 0,
            'competency_groups': 0,
            'competency_group_members': 0,
            'users': 0,
            'user_profiles': 0,
            'user_profile_skills': 0,
            'user_projects': 0,
            'user_project_skills': 0,
            'user_project_tools': 0,
        },

        'updated': {
            'roles': 0,
            'skills': 0,
            'tools': 0,
            'role_skills': 0,
            'role_tools': 0,
            'resources': 0,
            'competency_groups': 0,
            'competency_group_members': 0,
            'users': 0,
            'user_profiles': 0,
            'user_profile_skills': 0,
            'user_projects': 0,
            'user_project_skills': 0,
            'user_project_tools': 0,
        },

        'duplicates': 0,
        'skipped': 0,
        'warnings': [],
    }

    def clean(value):
        if value is None:
            return ''

        return str(value).strip()

    def add_warning(message):

        if len(summary['warnings']) < 200:
            summary['warnings'].append(message)

    def get_sheet(*possible_names):
        for sheet_name in possible_names:
            if sheet_name in workbook.sheetnames:
                return workbook[sheet_name]

        return None

    def get_headers(sheet):
        header_row = next(
            sheet.iter_rows(
                min_row=1,
                max_row=1,
                values_only=True
            ),
            ()
        )

        return {
            clean(value).lower(): index
            for index, value in enumerate(header_row)
            if clean(value)
        }

    def get_value(row, headers, *possible_headers):
        for header_name in possible_headers:
            index = headers.get(
                header_name.lower()
            )

            if index is not None and index < len(row):
                return clean(row[index])

        return ''

    def to_boolean(value, default=True):
        normalized = clean(value).lower()

        if normalized in [
            '0',
            'false',
            'no',
            'inactive',
        ]:
            return False

        if normalized in [
            '1',
            'true',
            'yes',
            'active',
        ]:
            return True

        return default


    sheet = get_sheet(
        'JobRoles',
        'JobRole'
    )

    if sheet:
        headers = get_headers(sheet)

        for index, row in enumerate(
            sheet.iter_rows(
                min_row=2,
                values_only=True
            ),
            start=2
        ):
            role_name = get_value(
                row,
                headers,
                'role_name',
                'job_role',
                'job role',
                'role'
            )

            description = get_value(
                row,
                headers,
                'description',
                'role_description',
                'role description'
            )

            if not role_name:
                summary['skipped'] += 1

                add_warning(
                    f"JobRoles row {index}: "
                    "missing role name."
                )

                continue

            role = JobRole.objects.filter(
                role_name__iexact=role_name
            ).first()

            if not role:
                JobRole.objects.create(
                    role_name=role_name,
                    description=description
                )

                summary['created']['roles'] += 1

            else:
                if (
                    description
                    and role.description != description
                ):
                    role.description = description
                    role.save(
                        update_fields=[
                            'description'
                        ]
                    )

                    summary['updated']['roles'] += 1

                else:
                    summary['duplicates'] += 1


    sheet = get_sheet(
        'Skills',
        'Skill'
    )

    if sheet:
        headers = get_headers(sheet)

        for index, row in enumerate(
            sheet.iter_rows(
                min_row=2,
                values_only=True
            ),
            start=2
        ):
            skill_name = get_value(
                row,
                headers,
                'skill_name',
                'skill name',
                'skill'
            )

            category = get_value(
                row,
                headers,
                'category',
                'skill_category',
                'skill category'
            )

            if not skill_name:
                summary['skipped'] += 1

                add_warning(
                    f"Skills row {index}: "
                    "missing skill name."
                )

                continue

            if skill_name.isdigit():
                summary['skipped'] += 1

                add_warning(
                    f"Skills row {index}: "
                    f"invalid numeric skill '{skill_name}'."
                )

                continue

            skill = Skill.objects.filter(
                skill_name__iexact=skill_name
            ).first()

            if not skill:
                Skill.objects.create(
                    skill_name=skill_name,
                    category=category or 'Other'
                )

                summary['created']['skills'] += 1

            else:
                if (
                    category
                    and skill.category != category
                ):
                    skill.category = category
                    skill.save(
                        update_fields=[
                            'category'
                        ]
                    )

                    summary['updated']['skills'] += 1

                else:
                    summary['duplicates'] += 1


    sheet = get_sheet(
        'Tools',
        'IndustryTools',
        'IndustryTool'
    )

    if sheet:
        headers = get_headers(sheet)

        for index, row in enumerate(
            sheet.iter_rows(
                min_row=2,
                values_only=True
            ),
            start=2
        ):
            tool_name = get_value(
                row,
                headers,
                'tool_name',
                'tool name',
                'tool'
            )

            category = get_value(
                row,
                headers,
                'category',
                'tool_category',
                'tool category'
            )

            if not tool_name:
                summary['skipped'] += 1

                add_warning(
                    f"Tools row {index}: "
                    "missing tool name."
                )

                continue

            if tool_name.isdigit():
                summary['skipped'] += 1

                add_warning(
                    f"Tools row {index}: "
                    f"invalid numeric tool '{tool_name}'."
                )

                continue

            tool = IndustryTool.objects.filter(
                tool_name__iexact=tool_name
            ).first()

            if not tool:
                IndustryTool.objects.create(
                    tool_name=tool_name,
                    category=category or 'Other'
                )

                summary['created']['tools'] += 1

            else:
                if (
                    category
                    and tool.category != category
                ):
                    tool.category = category
                    tool.save(
                        update_fields=[
                            'category'
                        ]
                    )

                    summary['updated']['tools'] += 1

                else:
                    summary['duplicates'] += 1


    sheet = get_sheet(
        'RoleSkills',
        'JobRoleSkills',
        'JobRoleSkill'
    )

    if sheet:
        headers = get_headers(sheet)

        for index, row in enumerate(
            sheet.iter_rows(
                min_row=2,
                values_only=True
            ),
            start=2
        ):
            role_name = get_value(
                row,
                headers,
                'role_name',
                'job_role',
                'job role',
                'role'
            )

            skill_name = get_value(
                row,
                headers,
                'skill_name',
                'skill name',
                'skill'
            )

            importance = get_value(
                row,
                headers,
                'importance',
                'priority'
            ) or 'Medium'

            if not role_name or not skill_name:
                summary['skipped'] += 1

                add_warning(
                    f"RoleSkills row {index}: "
                    "missing role or skill."
                )

                continue

            if importance not in [
                'High',
                'Medium',
                'Low'
            ]:
                summary['skipped'] += 1

                add_warning(
                    f"RoleSkills row {index}: "
                    f"invalid importance '{importance}'."
                )

                continue

            job_role = JobRole.objects.filter(
                role_name__iexact=role_name
            ).first()

            skill = Skill.objects.filter(
                skill_name__iexact=skill_name
            ).first()

            if not job_role:
                summary['skipped'] += 1

                add_warning(
                    f"RoleSkills row {index}: "
                    f"role '{role_name}' not found."
                )

                continue

            if not skill:
                summary['skipped'] += 1

                add_warning(
                    f"RoleSkills row {index}: "
                    f"skill '{skill_name}' not found."
                )

                continue

            mapping = JobRoleSkill.objects.filter(
                job_role=job_role,
                skill=skill
            ).first()

            if not mapping:
                JobRoleSkill.objects.create(
                    job_role=job_role,
                    skill=skill,
                    importance=importance
                )

                summary['created']['role_skills'] += 1

            else:
                if mapping.importance != importance:
                    mapping.importance = importance
                    mapping.save(
                        update_fields=[
                            'importance'
                        ]
                    )

                    summary['updated']['role_skills'] += 1

                else:
                    summary['duplicates'] += 1


    sheet = get_sheet(
        'RoleTools',
        'JobRoleTools',
        'JobRoleTool'
    )

    if sheet:
        headers = get_headers(sheet)

        for index, row in enumerate(
            sheet.iter_rows(
                min_row=2,
                values_only=True
            ),
            start=2
        ):
            role_name = get_value(
                row,
                headers,
                'role_name',
                'job_role',
                'job role',
                'role'
            )

            tool_name = get_value(
                row,
                headers,
                'tool_name',
                'tool name',
                'tool'
            )

            importance = get_value(
                row,
                headers,
                'importance',
                'priority'
            ) or 'Medium'

            if not role_name or not tool_name:
                summary['skipped'] += 1

                add_warning(
                    f"RoleTools row {index}: "
                    "missing role or tool."
                )

                continue

            if importance not in [
                'High',
                'Medium',
                'Low'
            ]:
                summary['skipped'] += 1

                add_warning(
                    f"RoleTools row {index}: "
                    f"invalid importance '{importance}'."
                )

                continue

            job_role = JobRole.objects.filter(
                role_name__iexact=role_name
            ).first()

            tool = IndustryTool.objects.filter(
                tool_name__iexact=tool_name
            ).first()

            if not job_role:
                summary['skipped'] += 1

                add_warning(
                    f"RoleTools row {index}: "
                    f"role '{role_name}' not found."
                )

                continue

            if not tool:
                summary['skipped'] += 1

                add_warning(
                    f"RoleTools row {index}: "
                    f"tool '{tool_name}' not found."
                )

                continue

            mapping = JobRoleTool.objects.filter(
                job_role=job_role,
                tool=tool
            ).first()

            if not mapping:
                JobRoleTool.objects.create(
                    job_role=job_role,
                    tool=tool,
                    importance=importance
                )

                summary['created']['role_tools'] += 1

            else:
                if mapping.importance != importance:
                    mapping.importance = importance
                    mapping.save(
                        update_fields=[
                            'importance'
                        ]
                    )

                    summary['updated']['role_tools'] += 1

                else:
                    summary['duplicates'] += 1


    sheet = get_sheet(
        'LearningResources',
        'LearningResource'
    )

    if sheet:
        headers = get_headers(sheet)

        valid_resource_types = [
            'Course',
            'Video',
            'Documentation',
            'Book',
            'Article',
        ]

        for index, row in enumerate(
            sheet.iter_rows(
                min_row=2,
                values_only=True
            ),
            start=2
        ):
            skill_name = get_value(
                row,
                headers,
                'skill_name',
                'skill name',
                'skill'
            )

            title = get_value(
                row,
                headers,
                'title',
                'resource_title',
                'resource title'
            )

            resource_type = get_value(
                row,
                headers,
                'resource_type',
                'resource type',
                'type'
            ) or 'Course'

            url = get_value(
                row,
                headers,
                'url',
                'link',
                'resource_url',
                'resource url'
            )

            if (
                not skill_name
                or not title
                or not url
            ):
                summary['skipped'] += 1

                add_warning(
                    f"LearningResources row {index}: "
                    "missing skill, title or URL."
                )

                continue

            if resource_type not in valid_resource_types:
                summary['skipped'] += 1

                add_warning(
                    f"LearningResources row {index}: "
                    f"invalid resource type "
                    f"'{resource_type}'."
                )

                continue

            skill = Skill.objects.filter(
                skill_name__iexact=skill_name
            ).first()

            if not skill:
                summary['skipped'] += 1

                add_warning(
                    f"LearningResources row {index}: "
                    f"skill '{skill_name}' not found."
                )

                continue

            resource = LearningResource.objects.filter(
                skill=skill,
                title__iexact=title
            ).first()

            if not resource:
                LearningResource.objects.create(
                    skill=skill,
                    title=title,
                    resource_type=resource_type,
                    url=url
                )

                summary['created']['resources'] += 1

            else:
                changed = False

                if resource.resource_type != resource_type:
                    resource.resource_type = resource_type
                    changed = True

                if resource.url != url:
                    resource.url = url
                    changed = True

                if changed:
                    resource.save()

                    summary['updated']['resources'] += 1

                else:
                    summary['duplicates'] += 1


    sheet = get_sheet(
        'CompetencyGroups',
        'CompetencyGroup'
    )

    if sheet:
        headers = get_headers(sheet)

        for index, row in enumerate(
            sheet.iter_rows(
                min_row=2,
                values_only=True
            ),
            start=2
        ):
            role_name = get_value(
                row,
                headers,
                'role_name',
                'job_role',
                'job role',
                'role'
            )

            group_name = get_value(
                row,
                headers,
                'group_name',
                'group name',
                'competency_group',
                'competency group'
            )

            rule = get_value(
                row,
                headers,
                'rule',
                'group_rule',
                'group rule'
            ).upper()

            if (
                not role_name
                or not group_name
                or not rule
            ):
                summary['skipped'] += 1

                add_warning(
                    f"CompetencyGroups row {index}: "
                    "missing role, group name or rule."
                )

                continue

            if rule not in [
                'ANY_ONE',
                'ALL_REQUIRED'
            ]:
                summary['skipped'] += 1

                add_warning(
                    f"CompetencyGroups row {index}: "
                    f"invalid rule '{rule}'."
                )

                continue

            job_role = JobRole.objects.filter(
                role_name__iexact=role_name
            ).first()

            if not job_role:
                summary['skipped'] += 1

                add_warning(
                    f"CompetencyGroups row {index}: "
                    f"role '{role_name}' not found."
                )

                continue

            group = CompetencyGroup.objects.filter(
                job_role=job_role,
                group_name__iexact=group_name
            ).first()

            if not group:
                CompetencyGroup.objects.create(
                    job_role=job_role,
                    group_name=group_name,
                    rule=rule
                )

                summary['created'][
                    'competency_groups'
                ] += 1

            else:
                if group.rule != rule:
                    group.rule = rule
                    group.save(
                        update_fields=[
                            'rule'
                        ]
                    )

                    summary['updated'][
                        'competency_groups'
                    ] += 1

                else:
                    summary['duplicates'] += 1


    sheet = get_sheet(
        'CompetencyGroupMembers',
        'CompetencyGroupMember'
    )

    if sheet:
        headers = get_headers(sheet)

        for index, row in enumerate(
            sheet.iter_rows(
                min_row=2,
                values_only=True
            ),
            start=2
        ):
            role_name = get_value(
                row,
                headers,
                'role_name',
                'job_role',
                'job role',
                'role'
            )

            group_name = get_value(
                row,
                headers,
                'group_name',
                'group name',
                'competency_group',
                'competency group'
            )

            skill_name = get_value(
                row,
                headers,
                'skill_name',
                'skill name',
                'skill'
            )

            if (
                not role_name
                or not group_name
                or not skill_name
            ):
                summary['skipped'] += 1

                add_warning(
                    f"CompetencyGroupMembers row {index}: "
                    "missing role, group name or skill."
                )

                continue

            job_role = JobRole.objects.filter(
                role_name__iexact=role_name
            ).first()

            if not job_role:
                summary['skipped'] += 1

                add_warning(
                    f"CompetencyGroupMembers row {index}: "
                    f"role '{role_name}' not found."
                )

                continue

            group = CompetencyGroup.objects.filter(
                job_role=job_role,
                group_name__iexact=group_name
            ).first()

            if not group:
                summary['skipped'] += 1

                add_warning(
                    f"CompetencyGroupMembers row {index}: "
                    f"group '{group_name}' not found "
                    f"for role '{role_name}'."
                )

                continue

            job_role_skill = JobRoleSkill.objects.filter(
                job_role=job_role,
                skill__skill_name__iexact=skill_name
            ).select_related(
                'skill'
            ).first()

            if not job_role_skill:
                summary['skipped'] += 1

                add_warning(
                    f"CompetencyGroupMembers row {index}: "
                    f"skill '{skill_name}' is not mapped "
                    f"to role '{role_name}'."
                )

                continue

            member, created = (
                CompetencyGroupMember.objects.get_or_create(
                    group=group,
                    job_role_skill=job_role_skill
                )
            )

            if created:
                summary['created'][
                    'competency_group_members'
                ] += 1

            else:
                summary['duplicates'] += 1


    sheet = get_sheet(
        'User',
        'Users'
    )

    if sheet:
        headers = get_headers(sheet)

        for index, row in enumerate(
            sheet.iter_rows(
                min_row=2,
                values_only=True
            ),
            start=2
        ):
            username = get_value(
                row,
                headers,
                'username',
                'user_name',
                'user name'
            )

            first_name = get_value(
                row,
                headers,
                'first_name',
                'first name'
            )

            last_name = get_value(
                row,
                headers,
                'last_name',
                'last name'
            )

            email = get_value(
                row,
                headers,
                'email',
                'email_address',
                'email address'
            )

            is_active_value = get_value(
                row,
                headers,
                'is_active',
                'active'
            )

            password = get_value(
                row,
                headers,
                'temporary_password',
                'password'
            ) or 'CareerReady@123'

            username = User.normalize_username(
                username
            )

            if not username or not email:
                summary['skipped'] += 1

                add_warning(
                    f"User row {index}: "
                    "missing username or email."
                )

                continue

            expected_active = to_boolean(
                is_active_value,
                default=True
            )

            user = User.objects.filter(
                username__iexact=username
            ).first()

            if user:
                if (
                    user.is_staff
                    or user.is_superuser
                ):
                    summary['skipped'] += 1

                    add_warning(
                        f"User row {index}: "
                        f"'{username}' is an admin account "
                        "and was not changed."
                    )

                    continue

                email_conflict = User.objects.filter(
                    email__iexact=email
                ).exclude(
                    id=user.id
                ).exists()

                if email_conflict:
                    summary['skipped'] += 1

                    add_warning(
                        f"User row {index}: "
                        f"email '{email}' is already used."
                    )

                    continue

                changed = False

                if user.first_name != first_name:
                    user.first_name = first_name
                    changed = True

                if user.last_name != last_name:
                    user.last_name = last_name
                    changed = True

                if user.email != email:
                    user.email = email
                    changed = True

                if user.is_active != expected_active:
                    user.is_active = expected_active
                    changed = True

                if changed:
                    user.save(
                        update_fields=[
                            'first_name',
                            'last_name',
                            'email',
                            'is_active',
                        ]
                    )

                    summary['updated']['users'] += 1

                else:
                    summary['duplicates'] += 1

                continue

            if User.objects.filter(
                email__iexact=email
            ).exists():
                summary['skipped'] += 1

                add_warning(
                    f"User row {index}: "
                    f"email '{email}' is already used."
                )

                continue

            try:
                User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    is_active=expected_active,
                    is_staff=False,
                    is_superuser=False
                )

                summary['created']['users'] += 1

            except IntegrityError:
                summary['skipped'] += 1

                add_warning(
                    f"User row {index}: "
                    f"username '{username}' could not "
                    "be created."
                )


    profile_source_map = {}

    sheet = get_sheet(
        'UserProfile',
        'UserProfiles'
    )

    if sheet:
        headers = get_headers(sheet)

        for index, row in enumerate(
            sheet.iter_rows(
                min_row=2,
                values_only=True
            ),
            start=2
        ):
            source_profile_id = get_value(
                row,
                headers,
                'id',
                'user_profile_id',
                'profile_id'
            )

            username = get_value(
                row,
                headers,
                'username',
                'user_name',
                'user name'
            )

            full_name = get_value(
                row,
                headers,
                'full_name',
                'full name'
            )

            university = get_value(
                row,
                headers,
                'university'
            )

            degree = get_value(
                row,
                headers,
                'degree'
            )

            year_of_study = get_value(
                row,
                headers,
                'year_of_study',
                'year of study'
            )

            github_link = get_value(
                row,
                headers,
                'github_link',
                'github_url',
                'github'
            )

            linkedin_link = get_value(
                row,
                headers,
                'linkedin_link',
                'linkedin_url',
                'linkedin'
            )

            resume_valid_value = get_value(
                row,
                headers,
                'is_resume_valid',
                'resume_valid'
            )

            if not username:
                summary['skipped'] += 1

                add_warning(
                    f"UserProfile row {index}: "
                    "missing username."
                )

                continue

            user = User.objects.filter(
                username__iexact=username
            ).first()

            if not user:
                summary['skipped'] += 1

                add_warning(
                    f"UserProfile row {index}: "
                    f"user '{username}' not found."
                )

                continue

            default_full_name = (
                user.get_full_name().strip()
                or user.username
            )

            values = {
                'full_name': (
                    full_name
                    or default_full_name
                ),
                'university': university or None,
                'degree': degree or None,
                'year_of_study': (
                    year_of_study or None
                ),
                'github_link': github_link or None,
                'linkedin_link': (
                    linkedin_link or None
                ),
                'is_resume_valid': to_boolean(
                    resume_valid_value,
                    default=False
                ),
            }

            profile = UserProfile.objects.filter(
                user=user
            ).first()

            if not profile:
                profile = UserProfile.objects.create(
                    user=user,
                    **values
                )

                summary['created'][
                    'user_profiles'
                ] += 1

            else:
                changed = False

                for field_name, value in values.items():
                    if getattr(
                        profile,
                        field_name
                    ) != value:
                        setattr(
                            profile,
                            field_name,
                            value
                        )

                        changed = True

                if changed:
                    profile.save()

                    summary['updated'][
                        'user_profiles'
                    ] += 1

                else:
                    summary['duplicates'] += 1

            if source_profile_id:
                profile_source_map[
                    source_profile_id
                ] = profile


    sheet = get_sheet(
        'UserProfile_Skills',
        'UserProfileSkills'
    )

    if sheet:
        headers = get_headers(sheet)

        for index, row in enumerate(
            sheet.iter_rows(
                min_row=2,
                values_only=True
            ),
            start=2
        ):
            source_profile_id = get_value(
                row,
                headers,
                'user_profile_id',
                'profile_id'
            )

            username = get_value(
                row,
                headers,
                'username',
                'user_name'
            )

            skill_name = get_value(
                row,
                headers,
                'skill_name',
                'skill name',
                'skill'
            )

            profile = None

            if source_profile_id:
                profile = profile_source_map.get(
                    source_profile_id
                )

            if not profile and username:
                profile = UserProfile.objects.filter(
                    user__username__iexact=username
                ).first()

            skill = Skill.objects.filter(
                skill_name__iexact=skill_name
            ).first()

            if not profile or not skill:
                summary['skipped'] += 1

                add_warning(
                    f"UserProfile_Skills row {index}: "
                    "profile or skill not found."
                )

                continue

            if profile.manual_skills.filter(
                id=skill.id
            ).exists():
                summary['duplicates'] += 1

            else:
                profile.manual_skills.add(
                    skill
                )

                summary['created'][
                    'user_profile_skills'
                ] += 1


    project_source_map = {}

    sheet = get_sheet(
        'UserProject',
        'UserProjects'
    )

    if sheet:
        headers = get_headers(sheet)

        for index, row in enumerate(
            sheet.iter_rows(
                min_row=2,
                values_only=True
            ),
            start=2
        ):
            source_project_id = get_value(
                row,
                headers,
                'id',
                'user_project_id',
                'project_id'
            )

            username = get_value(
                row,
                headers,
                'username',
                'user_name'
            )

            title = get_value(
                row,
                headers,
                'title',
                'project_title',
                'project title'
            )

            description = get_value(
                row,
                headers,
                'description',
                'project_description',
                'project description'
            )

            project_url = get_value(
                row,
                headers,
                'project_url',
                'project link',
                'url'
            )

            github_url = get_value(
                row,
                headers,
                'github_url',
                'github_link',
                'github'
            )

            if not username or not title:
                summary['skipped'] += 1

                add_warning(
                    f"UserProject row {index}: "
                    "missing username or project title."
                )

                continue

            user = User.objects.filter(
                username__iexact=username
            ).first()

            if not user:
                summary['skipped'] += 1

                add_warning(
                    f"UserProject row {index}: "
                    f"user '{username}' not found."
                )

                continue

            project = UserProject.objects.filter(
                user=user,
                title__iexact=title
            ).first()

            if not project:
                project = UserProject.objects.create(
                    user=user,
                    title=title,
                    description=description,
                    project_url=project_url or None,
                    github_url=github_url or None
                )

                summary['created'][
                    'user_projects'
                ] += 1

            else:
                changed = False

                expected_values = {
                    'description': description,
                    'project_url': (
                        project_url or None
                    ),
                    'github_url': (
                        github_url or None
                    ),
                }

                for field_name, value in expected_values.items():
                    if getattr(
                        project,
                        field_name
                    ) != value:
                        setattr(
                            project,
                            field_name,
                            value
                        )

                        changed = True

                if changed:
                    project.save()

                    summary['updated'][
                        'user_projects'
                    ] += 1

                else:
                    summary['duplicates'] += 1

            if source_project_id:
                project_source_map[
                    source_project_id
                ] = project


    sheet = get_sheet(
        'UserProject_Skills',
        'UserProjectSkills'
    )

    if sheet:
        headers = get_headers(sheet)

        for index, row in enumerate(
            sheet.iter_rows(
                min_row=2,
                values_only=True
            ),
            start=2
        ):
            source_project_id = get_value(
                row,
                headers,
                'user_project_id',
                'project_id'
            )

            skill_name = get_value(
                row,
                headers,
                'skill_name',
                'skill name',
                'skill'
            )

            project = project_source_map.get(
                source_project_id
            )

            skill = Skill.objects.filter(
                skill_name__iexact=skill_name
            ).first()

            if not project or not skill:
                summary['skipped'] += 1

                add_warning(
                    f"UserProject_Skills row {index}: "
                    "project or skill not found."
                )

                continue

            if project.skills_used.filter(
                id=skill.id
            ).exists():
                summary['duplicates'] += 1

            else:
                project.skills_used.add(
                    skill
                )

                summary['created'][
                    'user_project_skills'
                ] += 1


    sheet = get_sheet(
        'UserProject_Tools',
        'UserProjectTools'
    )

    if sheet:
        headers = get_headers(sheet)

        for index, row in enumerate(
            sheet.iter_rows(
                min_row=2,
                values_only=True
            ),
            start=2
        ):
            source_project_id = get_value(
                row,
                headers,
                'user_project_id',
                'project_id'
            )

            tool_name = get_value(
                row,
                headers,
                'tool_name',
                'tool name',
                'tool'
            )

            project = project_source_map.get(
                source_project_id
            )

            tool = IndustryTool.objects.filter(
                tool_name__iexact=tool_name
            ).first()

            if not project or not tool:
                summary['skipped'] += 1

                add_warning(
                    f"UserProject_Tools row {index}: "
                    "project or tool not found."
                )

                continue

            if project.tools_used.filter(
                id=tool.id
            ).exists():
                summary['duplicates'] += 1

            else:
                project.tools_used.add(
                    tool
                )

                summary['created'][
                    'user_project_tools'
                ] += 1

    created_total = sum(
        summary['created'].values()
    )

    updated_total = sum(
        summary['updated'].values()
    )

    messages.success(
        request,
        "Dataset import completed. "
        f"Created: {created_total}, "
        f"Updated: {updated_total}, "
        f"Duplicates: {summary['duplicates']}, "
        f"Skipped: {summary['skipped']}."
    )

    return render(
        request,
        'career_app/import_dataset.html',
        {
            'form': DatasetImportForm(),
            'summary': summary
        }
    )
@login_required
def add_competency_group(request):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    form = CompetencyGroupForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('view_competency_groups')

    return render(
        request,
        'career_app/add_competency_group.html',
        {'form': form}
    )


@login_required
def view_competency_groups(request):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    member_queryset = CompetencyGroupMember.objects.select_related(
        'job_role_skill',
        'job_role_skill__skill',
        'job_role_skill__job_role'
    ).order_by(
        'job_role_skill__skill__skill_name'
    )

    groups_queryset = CompetencyGroup.objects.select_related(
        'job_role'
    ).prefetch_related(
        Prefetch(
            'members',
            queryset=member_queryset
        )
    ).order_by(
        'job_role__role_name',
        'group_name'
    )

    paginator = Paginator(
        groups_queryset,
        25
    )

    page_number = request.GET.get('page')

    groups = paginator.get_page(
        page_number
    )

    return render(
        request,
        'career_app/view_competency_groups.html',
        {
            'groups': groups
        }
    )
@login_required
def add_competency_group_members(request):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    selected_group = None
    group_id = request.GET.get('group') or request.POST.get('group')

    if group_id:
        selected_group = CompetencyGroup.objects.filter(id=group_id).first()

    if request.method == 'POST':
        form = CompetencyGroupMemberForm(
            request.POST,
            selected_group=selected_group
        )

        if form.is_valid():
            group = form.cleaned_data['group']
            job_role_skills = form.cleaned_data['job_role_skills']

            CompetencyGroupMember.objects.filter(group=group).delete()

            for job_role_skill in job_role_skills:
                CompetencyGroupMember.objects.get_or_create(
                    group=group,
                    job_role_skill=job_role_skill
                )

            return redirect('view_competency_groups')
    else:
        form = CompetencyGroupMemberForm(
            selected_group=selected_group
        )

    return render(
        request,
        'career_app/add_competency_group_members.html',
        {
            'form': form,
            'selected_group': selected_group
        }
    )

@login_required
def edit_competency_group(request, group_id):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    group = CompetencyGroup.objects.get(id=group_id)

    form = CompetencyGroupForm(
        request.POST or None,
        instance=group
    )

    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('view_competency_groups')

    return render(
        request,
        'career_app/edit_competency_group.html',
        {
            'form': form,
            'group': group
        }
    )


@login_required
def delete_competency_group(request, group_id):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    group = CompetencyGroup.objects.get(id=group_id)

    if request.method == 'POST':
        group.delete()
        return redirect('view_competency_groups')

    return render(
        request,
        'career_app/delete_competency_group.html',
        {'group': group}
    )

@login_required
def platform_analytics(request):
    if not request.user.is_superuser:
        return redirect('user_dashboard')

    context = {
        'total_users': User.objects.filter(is_staff=False, is_superuser=False).count(),
        'total_admins': User.objects.filter(is_staff=True, is_superuser=False).count(),
        'total_job_roles': JobRole.objects.count(),
        'total_skills': Skill.objects.count(),
        'total_tools': IndustryTool.objects.count(),
        'total_learning_resources': LearningResource.objects.count(),
        'total_projects': UserProject.objects.count(),
        'total_readiness_assessments': ReadinessAssessment.objects.count(),
        'total_bottleneck_reports': EmployabilityBottleneck.objects.count(),
        'total_transition_analyses': CareerTransitionAnalysis.objects.count(),
        'pending_admin_requests': AdminRequest.objects.filter(status='Pending').count(),
        'approved_admin_requests': AdminRequest.objects.filter(status='Approved').count(),
        'rejected_admin_requests': AdminRequest.objects.filter(status='Rejected').count(),
        'used_invites': AdminInviteCode.objects.filter(is_used=True).count(),
        'unused_invites': AdminInviteCode.objects.filter(is_used=False).count(),
    }

    return render(
        request,
        'career_app/platform_analytics.html',
        context
    )

def _professional_skill_names():
    """
    Professional / behavioural competencies that should not be treated
    as technical weaknesses or technical interview skills.
    """
    return {
        'communication',
        'teamwork',
        'collaboration',
        'leadership',
        'adaptability',
        'time management',
        'problem solving',
        'critical thinking',
        'creativity',
        'presentation skills',
        'decision making',
        'conflict resolution',
        'attention to detail',
    }


def _is_professional_skill(skill):
    if not skill:
        return False

    return (
        skill.skill_name.strip().lower()
        in _professional_skill_names()
    )


def _is_technical_skill(skill):
    return (
        skill is not None
        and not _is_professional_skill(skill)
    )


def _build_ai_interview_context(session):
    """
    Build grounded context for AI-generated interview questions.

    The context deliberately separates:
    - evidence actually linked to the selected project;
    - competencies/tools known elsewhere in the user profile;
    - missing target-role requirements;
    - ANY_ONE competency groups from ALL_REQUIRED competencies.

    This prevents the model from treating an unused option in a
    satisfied ANY_ONE group as a separate weakness.
    """

    user = session.user
    job_role = session.job_role
    project = session.project

    project_skills = list(
        project.skills_used.all().order_by('skill_name')
    )

    project_tools = list(
        project.tools_used.all().order_by('tool_name')
    )

    project_skill_ids = {
        skill.id
        for skill in project_skills
    }

    project_tool_ids = {
        tool.id
        for tool in project_tools
    }

    profile = UserProfile.objects.filter(
        user=user
    ).first()

    user_skill_ids = set(project_skill_ids)
    user_tool_ids = set(project_tool_ids)

    if profile:
        user_skill_ids.update(
            profile.extracted_skills.values_list(
                'id',
                flat=True
            )
        )

        user_skill_ids.update(
            profile.manual_skills.values_list(
                'id',
                flat=True
            )
        )

        user_tool_ids.update(
            profile.manual_tools.values_list(
                'id',
                flat=True
            )
        )

    role_skills = list(
        JobRoleSkill.objects.filter(
            job_role=job_role
        ).select_related(
            'skill'
        ).order_by(
            'importance',
            'skill__skill_name'
        )
    )

    role_tools = list(
        JobRoleTool.objects.filter(
            job_role=job_role
        ).select_related(
            'tool'
        ).order_by(
            'importance',
            'tool__tool_name'
        )
    )

    competency_groups = list(
        CompetencyGroup.objects.filter(
            job_role=job_role
        ).prefetch_related(
            'members__job_role_skill__skill'
        ).order_by(
            'group_name'
        )
    )

    grouped_skill_ids = set()
    competency_group_context = []
    missing_all_required = []

    for group in competency_groups:
        members = [
            member
            for member in group.members.all()
            if (
                member.job_role_skill
                and _is_technical_skill(
                    member.job_role_skill.skill
                )
            )
        ]

        if not members:
            continue

        skills = [
            member.job_role_skill.skill
            for member in members
        ]

        skill_ids = {
            skill.id
            for skill in skills
        }

        grouped_skill_ids.update(skill_ids)

        matched_ids = skill_ids.intersection(
            user_skill_ids
        )

        if group.rule == 'ANY_ONE':
            competency_group_context.append({
                'name': group.group_name,
                'rule': 'ANY_ONE',
                'status': (
                    'SATISFIED'
                    if matched_ids
                    else 'MISSING'
                ),
                'options': [
                    skill.skill_name
                    for skill in skills
                ],
                'matched_options': [
                    skill.skill_name
                    for skill in skills
                    if skill.id in matched_ids
                ],
            })

        elif group.rule == 'ALL_REQUIRED':
            missing_names = []

            for member in members:
                role_skill = member.job_role_skill

                if role_skill.skill_id not in user_skill_ids:
                    missing_all_required.append(
                        role_skill
                    )
                    missing_names.append(
                        role_skill.skill.skill_name
                    )

            competency_group_context.append({
                'name': group.group_name,
                'rule': 'ALL_REQUIRED',
                'status': (
                    'SATISFIED'
                    if not missing_names
                    else 'PARTIAL_OR_MISSING'
                ),
                'options': [
                    skill.skill_name
                    for skill in skills
                ],
                'missing_options': missing_names,
            })

    standalone_role_skills = [
        role_skill
        for role_skill in role_skills
        if (
            role_skill.skill_id not in grouped_skill_ids
            and _is_technical_skill(role_skill.skill)
        )
    ]

    missing_standalone = [
        role_skill
        for role_skill in standalone_role_skills
        if role_skill.skill_id not in user_skill_ids
    ]

    matched_project_technical = [
        role_skill.skill.skill_name
        for role_skill in role_skills
        if (
            role_skill.skill_id in project_skill_ids
            and _is_technical_skill(role_skill.skill)
        )
    ]

    matched_project_professional = [
        role_skill.skill.skill_name
        for role_skill in role_skills
        if (
            role_skill.skill_id in project_skill_ids
            and _is_professional_skill(role_skill.skill)
        )
    ]

    matched_project_tools = [
        role_tool.tool.tool_name
        for role_tool in role_tools
        if role_tool.tool_id in project_tool_ids
    ]

    missing_role_tools = [
        role_tool.tool.tool_name
        for role_tool in role_tools
        if role_tool.tool_id not in user_tool_ids
    ]

    missing_role_skills = []

    for role_skill in missing_all_required:
        if role_skill.skill.skill_name not in missing_role_skills:
            missing_role_skills.append(
                role_skill.skill.skill_name
            )

    for role_skill in missing_standalone:
        if role_skill.skill.skill_name not in missing_role_skills:
            missing_role_skills.append(
                role_skill.skill.skill_name
            )

    latest_assessment = ReadinessAssessment.objects.filter(
        user=user,
        job_role=job_role
    ).order_by(
        '-created_at'
    ).first()

    latest_bottleneck = EmployabilityBottleneck.objects.filter(
        user=user,
        job_role=job_role
    ).order_by(
        '-created_at'
    ).first()

    return {
        'target_role': job_role.role_name,
        'project': {
            'title': project.title,
            'type': (
                project.get_project_type_display()
                if hasattr(
                    project,
                    'get_project_type_display'
                )
                else 'Not specified'
            ),
            'description': project.description or '',
            'skills_used': [
                skill.skill_name
                for skill in project_skills
            ],
            'tools_used': [
                tool.tool_name
                for tool in project_tools
            ],
        },
        'project_evidence': {
            'matched_technical_role_skills': (
                matched_project_technical
            ),
            'matched_professional_role_skills': (
                matched_project_professional
            ),
            'matched_role_tools': (
                matched_project_tools
            ),
        },
        'competency_groups': competency_group_context,
        'missing_required_skills': missing_role_skills,
        'missing_required_tools': missing_role_tools,
        'readiness': (
            {
                'academic_score': latest_assessment.academic_score,
                'industry_score': latest_assessment.industry_score,
                'overall_score': (
                    latest_assessment.overall_readiness_score
                ),
            }
            if latest_assessment
            else None
        ),
        'bottleneck': (
            {
                'name': latest_bottleneck.main_bottleneck,
                'explanation': latest_bottleneck.explanation,
            }
            if latest_bottleneck
            else None
        ),
    }


def _generate_ai_question_set(session):
    """
    Generate one complete set of 10 grounded interview questions.

    CareerReady AI supplies the evidence and constraints. The model
    generates the wording and scenarios. The returned metadata is
    validated against the database before questions are saved.

    Returns a list of dictionaries, or None if generation fails.
    """

    context = _build_ai_interview_context(session)

    client = OpenAI(
        api_key=settings.OPENAI_API_KEY
    )

    system_prompt = """
You are an interview question generator inside CareerReady AI.

Generate exactly 10 realistic interview questions for a Computer Science student.

The questions must be grounded ONLY in the supplied CareerReady AI evidence.

STRICT GROUNDING RULES:
1. Never invent technologies, frameworks, tools, project features,
   architecture, responsibilities, team activities, testing methods,
   metrics or outcomes.
2. A skill/tool listed under project evidence may be treated as something
   the candidate actually used in the selected project.
3. A skill/tool listed as missing must NEVER be described as something the
   candidate already used. Ask a hypothetical application question instead.
4. For a satisfied ANY_ONE competency group, do not treat the unused options
   as separate weaknesses.
5. For a missing ANY_ONE competency group, ask about choosing/applying one
   suitable option rather than requiring every option.
6. Professional competencies such as Communication and Teamwork belong in
   BEHAVIOURAL questions, not technical weakness questions.

QUESTION QUALITY RULES:
7. Every question must be specific to the target role and/or selected project.
8. Each question must be no more than 80 words.
9. Assess at most two main technical ideas in a single question.
10. Do not create long numbered lists or multiple questions disguised as one.
11. A question should normally be answerable verbally in about 2 to 4 minutes.
12. Make HARD questions deeper through reasoning and trade-offs, not length.
13. Avoid duplicate or near-duplicate questions.
14. Do not ask the candidate to define a professional competency such as
    Communication. Ask for behavioural evidence instead.

COVERAGE:
15. Include a balanced interview containing project evidence, system design,
    matched technical evidence when available, behavioural evidence when
    available, competency gaps, tool knowledge and production thinking.
16. Use only these question types:
    PROJECT, TECHNICAL, TOOL, COMPETENCY, WEAKNESS, SYSTEM_DESIGN, BEHAVIOURAL.
17. Use only these difficulty values: EASY, MEDIUM, HARD.
18. Return exactly 10 question objects in the required structured format.
""".strip()

    user_prompt = (
        "CAREERREADY AI INTERVIEW CONTEXT:\n\n"
        + json.dumps(
            context,
            indent=2,
            default=str
        )
    )

    try:
        response = client.responses.create(
            model='gpt-5',
            instructions=system_prompt,
            input=user_prompt,
            text={
                'format': {
                    'type': 'json_schema',
                    'name': 'careerready_interview_questions',
                    'strict': True,
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'questions': {
                                'type': 'array',
                                'minItems': 10,
                                'maxItems': 10,
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'question_text': {
                                            'type': 'string'
                                        },
                                        'question_type': {
                                            'type': 'string',
                                            'enum': [
                                                'PROJECT',
                                                'TECHNICAL',
                                                'TOOL',
                                                'COMPETENCY',
                                                'WEAKNESS',
                                                'SYSTEM_DESIGN',
                                                'BEHAVIOURAL',
                                            ]
                                        },
                                        'difficulty': {
                                            'type': 'string',
                                            'enum': [
                                                'EASY',
                                                'MEDIUM',
                                                'HARD',
                                            ]
                                        },
                                        'expected_skill': {
                                            'type': [
                                                'string',
                                                'null'
                                            ]
                                        },
                                        'expected_tool': {
                                            'type': [
                                                'string',
                                                'null'
                                            ]
                                        },
                                        'competency_group': {
                                            'type': [
                                                'string',
                                                'null'
                                            ]
                                        },
                                    },
                                    'required': [
                                        'question_text',
                                        'question_type',
                                        'difficulty',
                                        'expected_skill',
                                        'expected_tool',
                                        'competency_group',
                                    ],
                                    'additionalProperties': False,
                                }
                            }
                        },
                        'required': [
                            'questions'
                        ],
                        'additionalProperties': False,
                    }
                }
            }
        )

        data = json.loads(
            response.output_text
        )

        questions = data.get(
            'questions',
            []
        )

        if len(questions) != 10:
            raise ValueError(
                'AI did not return exactly 10 questions.'
            )

        return questions

    except Exception as error:
        logger.warning(
            'AI interview question generation failed for '
            'session %s: %s',
            session.id,
            error,
        )

        return None



def generate_ai_interview_questions(session):
    """
    Generate and save exactly 10 AI-powered interview questions.

    CareerReady AI supplies grounded user, project, role, competency,
    readiness and bottleneck evidence. If AI generation or validation fails,
    the interview is not replaced with rule-based questions; the failure is
    returned to the user so they can retry.
    """

    if session.questions.exists():
        return session.questions.order_by(
            'display_order',
            'id'
        )

    generated_questions = _generate_ai_question_set(
        session
    )

    if not generated_questions:
        raise ValueError(
            'AI interview question generation returned no usable questions.'
        )

    allowed_skill_names = {
        skill.skill_name.lower(): skill
        for skill in Skill.objects.filter(
            jobroleskill__job_role=session.job_role
        ).distinct()
    }

    allowed_tool_names = {
        tool.tool_name.lower(): tool
        for tool in IndustryTool.objects.filter(
            jobroletool__job_role=session.job_role
        ).distinct()
    }

    allowed_group_names = {
        group.group_name.lower(): group
        for group in CompetencyGroup.objects.filter(
            job_role=session.job_role
        )
    }

    allowed_question_types = {
        'PROJECT',
        'TECHNICAL',
        'TOOL',
        'COMPETENCY',
        'WEAKNESS',
        'SYSTEM_DESIGN',
        'BEHAVIOURAL',
    }

    allowed_difficulties = {
        'EASY',
        'MEDIUM',
        'HARD',
    }

    validated_questions = []
    normalized_texts = set()

    for item in generated_questions:
        question_text = str(
            item.get(
                'question_text',
                ''
            )
        ).strip()

        question_type = str(
            item.get(
                'question_type',
                ''
            )
        ).strip().upper()

        difficulty = str(
            item.get(
                'difficulty',
                ''
            )
        ).strip().upper()

        if not question_text:
            continue

        if question_type not in allowed_question_types:
            logger.warning(
                'Rejected invalid AI interview question type %s '
                'for session %s.',
                question_type,
                session.id,
            )
            continue

        if difficulty not in allowed_difficulties:
            logger.warning(
                'Rejected invalid AI interview difficulty %s '
                'for session %s.',
                difficulty,
                session.id,
            )
            continue

        if len(question_text.split()) > 90:
            logger.warning(
                'Rejected overlong AI interview question '
                'for session %s.',
                session.id,
            )
            continue

        normalized_text = ' '.join(
            question_text.lower().split()
        )

        if normalized_text in normalized_texts:
            continue

        normalized_texts.add(
            normalized_text
        )

        skill_name = item.get(
            'expected_skill'
        )
        tool_name = item.get(
            'expected_tool'
        )
        group_name = item.get(
            'competency_group'
        )

        expected_skill = None
        expected_tool = None
        competency_group = None

        if skill_name:
            expected_skill = allowed_skill_names.get(
                str(skill_name).strip().lower()
            )

        if tool_name:
            expected_tool = allowed_tool_names.get(
                str(tool_name).strip().lower()
            )

        if group_name:
            competency_group = allowed_group_names.get(
                str(group_name).strip().lower()
            )

        validated_questions.append({
            'question_text': question_text,
            'question_type': question_type,
            'difficulty': difficulty,
            'expected_skill': expected_skill,
            'expected_tool': expected_tool,
            'competency_group': competency_group,
        })

    if len(validated_questions) != 10:
        raise ValueError(
            f'AI question validation produced '
            f'{len(validated_questions)}/10 usable questions.'
        )

    with transaction.atomic():
        for index, item in enumerate(
            validated_questions,
            start=1
        ):
            InterviewQuestion.objects.create(
                session=session,
                question_type=item['question_type'],
                question_text=item['question_text'],
                difficulty=item['difficulty'],
                display_order=index,
                expected_skill=item['expected_skill'],
                expected_tool=item['expected_tool'],
                competency_group=item['competency_group'],
            )

    return session.questions.order_by(
        'display_order',
        'id'
    )


@login_required
def interview_setup(request):
    """
    Create an AI-only interview session.

    The user selects a target role and one of their own projects.
    Question generation is always AI-powered.
    """

    user_projects = UserProject.objects.filter(
        user=request.user
    )

    if not user_projects.exists():
        messages.warning(
            request,
            'You must add at least one project before starting a project-based interview.'
        )
        return redirect('add_project')

    if request.method == 'POST':
        form = InterviewSetupForm(
            request.POST,
            user=request.user
        )

        if form.is_valid():
            interview_session = form.save(
                commit=False
            )

            selected_project = form.cleaned_data[
                'project'
            ]

            if selected_project.user != request.user:
                messages.error(
                    request,
                    'You cannot use another user’s project.'
                )
                return redirect(
                    'interview_setup'
                )

            interview_session.user = request.user
            interview_session.status = 'CREATED'

            # The Interview Coach is now AI-only.
            interview_session.question_generation_method = (
                'AI_POWERED'
            )

            interview_session.save()

            return redirect(
                'generate_ai_interview',
                session_id=interview_session.id
            )

    else:
        form = InterviewSetupForm(
            user=request.user
        )

    context = {
        'form': form,
        'project_count': user_projects.count(),
    }

    return render(
        request,
        'career_app/interview_setup.html',
        context
    )

@login_required
def generate_ai_interview(request, session_id):
    """
    Display a loading page before AI question generation.

    GET:
        Show the generating-questions screen.

    POST:
        Generate the questions and redirect to the interview.
    """

    session = get_object_or_404(
        InterviewSession.objects.select_related(
            'job_role',
            'project',
        ),
        id=session_id,
        user=request.user,
    )


    if session.questions.exists():
        session.status = 'IN_PROGRESS'

        session.save(
            update_fields=[
                'status'
            ]
        )

        return redirect(
            'interview_session',
            session_id=session.id,
        )


    if request.method == 'GET':
        return render(
            request,
            'career_app/generating_interview_questions.html',
            {
                'session': session,
            }
        )


    try:
        generate_ai_interview_questions(
            session
        )

    except Exception as error:
        logger.exception(
            'AI question generation failed '
            'for interview session %s.',
            session.id,
        )

        messages.error(
            request,
            'AI question generation failed. '
            'Please try again.'
        )

        return redirect(
            'interview_setup'
        )

    if not session.questions.exists():
        messages.error(
            request,
            'No interview questions could be generated.'
        )

        return redirect(
            'interview_setup'
        )

    session.status = 'IN_PROGRESS'

    session.save(
        update_fields=[
            'status'
        ]
    )

    messages.success(
        request,
        'Personalised AI interview questions generated successfully.'
    )

    return redirect(
        'interview_session',
        session_id=session.id,
    )


def evaluate_interview_session(session):
    """
    Evaluate every answer in the interview session using the AI evaluator.

    Rule-based and hybrid evaluation have been removed. If AI evaluation
    fails, the error is allowed to propagate so the session is not silently
    replaced with a different scoring method.
    """

    answers = list(
        InterviewAnswer.objects.filter(
            question__session=session
        ).select_related(
            'question',
            'question__expected_skill',
            'question__expected_tool',
            'question__competency_group',
            'question__session',
            'question__session__project',
            'question__session__job_role',
        ).prefetch_related(
            'question__session__project__skills_used',
            'question__session__project__tools_used',
        ).order_by(
            'question__display_order',
            'question__id',
        )
    )

    if not answers:
        raise ValueError(
            'No interview answers were found for this session.'
        )

    for answer in answers:
        evaluate_answer_with_ai(
            answer
        )

    average_score = InterviewAnswer.objects.filter(
        question__session=session,
        overall_score__isnull=False,
    ).aggregate(
        average_score=Avg('overall_score')
    )['average_score']

    session.overall_score = (
        round(average_score, 2)
        if average_score is not None
        else 0.0
    )

    session.status = 'COMPLETED'
    session.completed_at = timezone.now()
    session.evaluation_method = 'AI_POWERED'

    session.save(
        update_fields=[
            'overall_score',
            'status',
            'completed_at',
            'evaluation_method',
        ]
    )

    logger.info(
        'Interview session %s evaluated using AI_POWERED. '
        'Overall score: %s',
        session.id,
        session.overall_score,
    )

    return session

@login_required
def interview_session(request, session_id):
    session = get_object_or_404(
        InterviewSession.objects.select_related(
            "job_role",
            "project",
        ),
        id=session_id,
        user=request.user,
    )

    questions = list(
        InterviewQuestion.objects.filter(
            session=session
        ).select_related(
            "expected_skill",
            "expected_tool",
            "competency_group",
        ).order_by(
            "display_order",
            "id",
        )
    )

    total_questions = len(questions)

    if total_questions == 0:
        messages.error(
            request,
            "No interview questions were found for this session.",
        )
        return redirect("interview_setup")


    if (
        session.status == "COMPLETED"
        and session.evaluation_method
    ):
        return redirect(
            "interview_results",
            session_id=session.id,
        )

    try:
        requested_position = int(
            request.GET.get("question", 1)
        )
    except (TypeError, ValueError):
        requested_position = 1

    requested_position = max(
        1,
        min(requested_position, total_questions),
    )

    current_position = requested_position
    current_question = questions[current_position - 1]

    existing_answer = InterviewAnswer.objects.filter(
        question=current_question
    ).first()

    if request.method == "POST":
        question_id = request.POST.get("question_id")

        posted_question = get_object_or_404(
            InterviewQuestion,
            id=question_id,
            session=session,
        )

        existing_answer = InterviewAnswer.objects.filter(
            question=posted_question
        ).first()

        form = InterviewAnswerForm(
            request.POST,
            instance=existing_answer,
        )

        if form.is_valid():
            interview_answer = form.save(
                commit=False
            )
            interview_answer.question = posted_question
            interview_answer.save()

            posted_position = next(
                (
                    index
                    for index, question in enumerate(
                        questions,
                        start=1,
                    )
                    if question.id == posted_question.id
                ),
                current_position,
            )

            is_last_question = (
                posted_position == total_questions
            )


            if is_last_question:
                answered_question_ids = set(
                    InterviewAnswer.objects.filter(
                        question__session=session
                    ).exclude(
                        answer_text__isnull=True
                    ).exclude(
                        answer_text__exact=""
                    ).values_list(
                        "question_id",
                        flat=True,
                    )
                )

                first_unanswered_position = None

                for index, question in enumerate(
                    questions,
                    start=1,
                ):
                    if question.id not in answered_question_ids:
                        first_unanswered_position = index
                        break

                    saved_answer = InterviewAnswer.objects.filter(
                        question=question
                    ).first()

                    if (
                        saved_answer is None
                        or not saved_answer.answer_text.strip()
                    ):
                        first_unanswered_position = index
                        break

                if first_unanswered_position is not None:
                    messages.warning(
                        request,
                        "Please answer all interview questions "
                        "before finishing.",
                    )

                    interview_url = reverse(
                        "interview_session",
                        args=[session.id],
                    )

                    return redirect(
                        f"{interview_url}"
                        f"?question={first_unanswered_position}"
                    )


                return redirect(
                    "interview_evaluation_loading",
                    session_id=session.id,
                )


            next_position = posted_position + 1

            messages.success(
                request,
                "Answer saved successfully.",
            )

            interview_url = reverse(
                "interview_session",
                args=[session.id],
            )

            return redirect(
                f"{interview_url}"
                f"?question={next_position}"
            )

    else:
        form = InterviewAnswerForm(
            instance=existing_answer
        )

    answered_count = InterviewAnswer.objects.filter(
        question__session=session
    ).exclude(
        answer_text__isnull=True
    ).exclude(
        answer_text__exact=""
    ).count()

    progress_percentage = round(
        (
            answered_count
            / total_questions
        ) * 100
    )

    previous_position = (
        current_position - 1
        if current_position > 1
        else None
    )

    next_position = (
        current_position + 1
        if current_position < total_questions
        else None
    )

    context = {
        "session": session,
        "questions": questions,
        "current_question": current_question,
        "current_position": current_position,
        "previous_position": previous_position,
        "next_position": next_position,
        "total_questions": total_questions,
        "answered_count": answered_count,
        "progress_percentage": progress_percentage,
        "is_last_question": (
            current_position == total_questions
        ),
        "completed": (
            session.status == "COMPLETED"
        ),
        "form": form,
    }

    return render(
        request,
        "career_app/interview_session.html",
        context,
    )
@login_required
def interview_evaluation_loading(request, session_id):
    """
    Display the AI evaluation loading page before evaluation begins.

    The loading template automatically submits a POST request to
    complete_interview, so the user sees the loading screen while
    the AI evaluates the saved interview answers.
    """
    session = get_object_or_404(
        InterviewSession.objects.select_related(
            'job_role',
            'project',
        ),
        id=session_id,
        user=request.user,
    )

    if (
        session.status == 'COMPLETED'
        and session.evaluation_method == 'AI_POWERED'
    ):
        return redirect(
            'interview_results',
            session_id=session.id,
        )

    return render(
        request,
        'career_app/interview_evaluation_loading.html',
        {
            'session': session,
        }
    )


@login_required
@require_POST
@transaction.atomic
def complete_interview(request, session_id):
    """
    Complete and evaluate an interview.

    The user must answer every question before the interview can
    be completed.
    """

    session = get_object_or_404(
        InterviewSession.objects.select_related(
            'user',
            'job_role',
            'project',
        ),
        id=session_id,
        user=request.user
    )

    questions = session.questions.all().order_by(
        'display_order',
        'id'
    )

    if not questions.exists():
        messages.error(
            request,
            'This interview does not contain any questions.'
        )

        return redirect(
            'interview_setup'
        )

    answered_question_ids = set(
        InterviewAnswer.objects.filter(
            question__session=session
        ).values_list(
            'question_id',
            flat=True
        )
    )

    unanswered_questions = questions.exclude(
        id__in=answered_question_ids
    )

    if unanswered_questions.exists():
        first_unanswered = unanswered_questions.first()

        messages.warning(
            request,
            'Please answer all questions before completing the interview.'
        )

        interview_url = reverse(
            'interview_session',
            args=[session.id]
        )

        return redirect(
            f'{interview_url}?question={first_unanswered.display_order}'
        )

    empty_answers = InterviewAnswer.objects.filter(
        question__session=session,
        answer_text__regex=r'^\s*$'
    )

    if empty_answers.exists():
        first_empty_answer = empty_answers.select_related(
            'question'
        ).order_by(
            'question__display_order'
        ).first()

        messages.warning(
            request,
            'Please provide an answer for every interview question.'
        )

        interview_url = reverse(
            'interview_session',
            args=[session.id]
        )

        return redirect(
            f'{interview_url}'
            f'?question={first_empty_answer.question.display_order}'
        )

    try:
        evaluate_interview_session(session)

    except Exception as error:
        transaction.set_rollback(True)

        messages.error(
            request,
            f'Interview evaluation failed: {error}'
        )

        return redirect(
            'interview_session',
            session_id=session.id
        )

    messages.success(
        request,
        'Interview completed and evaluated successfully.'
    )

    return redirect(
        'interview_results',
        session_id=session.id
    )


@login_required
def interview_results(request, session_id):
    """
    Display the completed interview evaluation.
    """

    session = get_object_or_404(
        InterviewSession.objects.select_related(
            'user',
            'job_role',
            'project',
            'readiness_assessment',
            'bottleneck',
        ),
        id=session_id,
        user=request.user
    )

    answers = InterviewAnswer.objects.filter(
        question__session=session
    ).select_related(
        'question',
        'question__expected_skill',
        'question__expected_tool',
        'question__competency_group',
    ).order_by(
        'question__display_order',
        'question__id'
    )

    answered_count = answers.count()
    evaluated_count = answers.filter(
        evaluated_at__isnull=False
    ).count()

    context = {
        'session': session,
        'answers': answers,
        'answered_count': answered_count,
        'evaluated_count': evaluated_count,
    }

    return render(
        request,
        'career_app/interview_results.html',
        context
    )

@login_required
def interview_history(request):
    """
    Display all interview sessions created by the logged-in user.
    """

    sessions = InterviewSession.objects.filter(
        user=request.user
    ).select_related(
        'job_role',
        'project',
    ).annotate(
        answer_count=models.Count(
            'questions__answer',
            distinct=True
        ),
        question_count=models.Count(
            'questions',
            distinct=True
        ),
    ).order_by(
        '-created_at'
    )

    return render(
        request,
        'career_app/interview_history.html',
        {
            'sessions': sessions,
        }
    )
