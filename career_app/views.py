from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from .forms import RegisterForm
from django.contrib import messages
from django.contrib.auth.models import User
from django.utils.crypto import get_random_string
from .models import AdminInviteCode, AdminRequest
from .forms import AdminRequestForm
from .forms import RegisterForm, AdminRequestForm, JobRoleForm, SkillForm, JobRoleSkillForm
from .models import AdminInviteCode, AdminRequest, JobRole, Skill, JobRoleSkill
from .forms import CareerMatchForm
from .models import CareerMatchResult
from .models import LearningResource
from .forms import LearningResourceForm
from .models import LearningResource
from .forms import UserProfileForm
from .models import UserProfile
from .utils import extract_text_from_resume, is_valid_resume, extract_skills_from_text
from .models import Skill
from .forms import ReadinessAssessmentForm
from .models import ReadinessAssessment
from .forms import IndustryToolForm, JobRoleToolForm
from .models import IndustryTool, JobRoleTool
from .models import IndustryTool, JobRoleTool
from .forms import (
    UserProfileForm,
    CareerMatchForm,
    ReadinessAssessmentForm
)
from .forms import BottleneckForm
from .models import EmployabilityBottleneck
from .models import CareerTransitionAnalysis
from .forms import CareerTransitionForm
from django.conf import settings
from .models import UserProject
from .forms import UserProjectForm


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

    if request.method == 'POST':
        if form.is_valid():
            profile = UserProfile.objects.filter(user=request.user).first()

            if not profile:
                return redirect('create_profile')

            result = form.save(commit=False)
            result.user = request.user
            result.save()

            user_skills = (
                profile.extracted_skills.all() | profile.manual_skills.all()
            ).distinct()

            result.selected_skills.set(user_skills)

            required_skills = Skill.objects.filter(
                jobroleskill__job_role=result.job_role
            ).distinct()

            if required_skills.count() == 0:
                result.match_score = 0
                result.save()
                result.matched_skills.clear()
                result.missing_skills.clear()
                return redirect('career_match_result', result_id=result.id)

            matched_skills = user_skills.filter(
                id__in=required_skills.values_list('id', flat=True)
            )

            missing_skills = required_skills.exclude(
                id__in=user_skills.values_list('id', flat=True)
            )

            match_score = (
                matched_skills.count() / required_skills.count()
            ) * 100

            result.match_score = round(match_score, 2)
            result.save()

            result.matched_skills.set(matched_skills)
            result.missing_skills.set(missing_skills)

            return redirect('career_match_result', result_id=result.id)

    return render(request, 'career_app/career_match.html', {'form': form})
@login_required
def career_match_result(request, result_id):
    result = CareerMatchResult.objects.get(id=result_id, user=request.user)

    missing_skills = result.missing_skills.all()

    resources = LearningResource.objects.filter(
        skill__in=missing_skills
    ).select_related('skill')

    return render(request, 'career_app/career_match_result.html', {
        'result': result,
        'resources': resources
    })
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
def learning_roadmap(request, result_id):

    result = CareerMatchResult.objects.get(
        id=result_id,
        user=request.user
    )

    missing_skills = result.missing_skills.all()

    roadmap_steps = []

    step_number = 1

    for skill in missing_skills:
        roadmap_steps.append(
            f"Step {step_number}: Learn {skill.skill_name}"
        )
        step_number += 1

    roadmap_steps.append(
        f"Step {step_number}: Build a project related to {result.job_role.role_name}"
    )

    return render(
        request,
        'career_app/learning_roadmap.html',
        {
            'result': result,
            'roadmap_steps': roadmap_steps
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

@login_required
def readiness_assessment(request):
    form = ReadinessAssessmentForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            assessment = form.save(commit=False)
            assessment.user = request.user

            job_role = assessment.job_role

            required_skills = Skill.objects.filter(
                jobroleskill__job_role=job_role
            ).distinct()

            required_tools = IndustryTool.objects.filter(
                jobroletool__job_role=job_role
            ).distinct()

            profile = UserProfile.objects.filter(user=request.user).first()

            if profile:
                user_skills = (
                    profile.extracted_skills.all() | profile.manual_skills.all()
                ).distinct()
                user_tools = profile.manual_tools.all()
            else:
                user_skills = Skill.objects.none()
                user_tools = IndustryTool.objects.none()

            matched_skills = user_skills.filter(
                id__in=required_skills.values_list('id', flat=True)
            )

            missing_skills = required_skills.exclude(
                id__in=user_skills.values_list('id', flat=True)
            )

            matched_tools = user_tools.filter(
                id__in=required_tools.values_list('id', flat=True)
            )

            missing_tools = required_tools.exclude(
                id__in=user_tools.values_list('id', flat=True)
            )

            if required_skills.count() > 0:
                academic_score = (
                    matched_skills.count() / required_skills.count()
                ) * 100
            else:
                academic_score = 0

            if required_tools.count() > 0:
                industry_score = (
                    matched_tools.count() / required_tools.count()
                ) * 100
            else:
                industry_score = 0

            overall_score = (academic_score * 0.6) + (industry_score * 0.4)

            assessment.academic_score = round(academic_score, 2)
            assessment.industry_score = round(industry_score, 2)
            assessment.overall_readiness_score = round(overall_score, 2)

            matched_skill_names = [skill.skill_name for skill in matched_skills]
            missing_skill_names = [skill.skill_name for skill in missing_skills]

            matched_tool_names = [tool.tool_name for tool in matched_tools]
            missing_tool_names = [tool.tool_name for tool in missing_tools]

            assessment.strengths = (
                "Matched Skills: " + ", ".join(matched_skill_names) +
                "\n\nMatched Tools: " + ", ".join(matched_tool_names)
            )

            assessment.weaknesses = (
                "Missing Skills: " + ", ".join(missing_skill_names) +
                "\nMissing Tools: " + ", ".join(missing_tool_names)
            )

            if overall_score >= 75:
                assessment.recommendation = (
                    "You are close to industry-ready for this role. "
                    "Focus on portfolio projects and interview preparation."
                )
            elif overall_score >= 50:
                assessment.recommendation = (
                    "You have a moderate readiness level. Improve missing skills, "
                    "tools, and build practical projects."
                )
            else:
                assessment.recommendation = (
                    "Your readiness is low for this role. Start with foundational "
                    "skills and required industry tools before applying."
                )

            assessment.save()

            return redirect(
                'readiness_result',
                assessment_id=assessment.id
            )

    return render(
        request,
        'career_app/readiness_assessment.html',
        {'form': form}
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


@login_required
def bottleneck_detection(request):
    form = BottleneckForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            job_role = form.cleaned_data['job_role']

            assessment = ReadinessAssessment.objects.filter(
                user=request.user,
                job_role=job_role
            ).order_by('-created_at').first()

            if not assessment:
                return redirect('readiness_assessment')

            projects = UserProject.objects.filter(user=request.user)
            project_count = projects.count()

            required_skills = Skill.objects.filter(
                jobroleskill__job_role=job_role
            ).distinct()

            required_tools = IndustryTool.objects.filter(
                jobroletool__job_role=job_role
            ).distinct()

            required_skill_ids = set(required_skills.values_list('id', flat=True))
            required_tool_ids = set(required_tools.values_list('id', flat=True))

            project_skill_ids = set()
            project_tool_ids = set()

            for project in projects:
                project_skill_ids.update(
                    project.skills_used.values_list('id', flat=True)
                )
                project_tool_ids.update(
                    project.tools_used.values_list('id', flat=True)
                )

            relevant_project_skills = project_skill_ids.intersection(required_skill_ids)
            relevant_project_tools = project_tool_ids.intersection(required_tool_ids)

            missing_project_skill_ids = required_skill_ids.difference(project_skill_ids)
            missing_project_tool_ids = required_tool_ids.difference(project_tool_ids)

            total_required_items = len(required_skill_ids) + len(required_tool_ids)
            total_relevant_items = len(relevant_project_skills) + len(relevant_project_tools)

            if total_required_items > 0:
                project_relevance_score = round(
                    (total_relevant_items / total_required_items) * 100
                )
            else:
                project_relevance_score = 0

            if len(required_skill_ids) > 0:
                project_skill_coverage = round(
                    (len(relevant_project_skills) / len(required_skill_ids)) * 100
                )
            else:
                project_skill_coverage = 0

            if len(required_tool_ids) > 0:
                project_tool_coverage = round(
                    (len(relevant_project_tools) / len(required_tool_ids)) * 100
                )
            else:
                project_tool_coverage = 0

            missing_project_skills = Skill.objects.filter(
                id__in=missing_project_skill_ids
            )

            missing_project_tools = IndustryTool.objects.filter(
                id__in=missing_project_tool_ids
            )

            missing_skill_names = ", ".join(
                missing_project_skills.values_list("skill_name", flat=True)
            )

            missing_tool_names = ", ".join(
                missing_project_tools.values_list("tool_name", flat=True)[:5]
            )

            bottleneck = EmployabilityBottleneck()
            bottleneck.user = request.user
            bottleneck.job_role = job_role
            bottleneck.readiness_assessment = assessment

            if assessment.academic_score < 50:
                bottleneck.main_bottleneck = "Skill Deficiency"
                bottleneck.explanation = (
                    f"Your academic readiness score is {assessment.academic_score}%, "
                    f"which means your core skill foundation for {job_role.role_name} is weak."
                )
                bottleneck.recommendation = (
                    "First improve the missing core skills for this role before focusing on projects."
                )

            elif assessment.industry_score < 50:
                bottleneck.main_bottleneck = "Industry Tool Deficiency"
                bottleneck.explanation = (
                    f"Your industry tool readiness score is {assessment.industry_score}%, "
                    f"which means you are missing important tools required for {job_role.role_name}."
                )
                bottleneck.recommendation = (
                    "Learn the missing tools and use them inside practical projects."
                )

            elif project_count == 0:
                bottleneck.main_bottleneck = "Lack of Practical Projects"
                bottleneck.explanation = (
                    "You have not added any projects to prove practical experience."
                )
                bottleneck.recommendation = (
                    f"Add at least one {job_role.role_name} project and map the skills/tools used."
                )

            elif project_skill_coverage < 50:
                bottleneck.main_bottleneck = "Weak Project Skill Evidence"
                bottleneck.explanation = (
                    f"You added {project_count} project(s), but they only prove "
                    f"{project_skill_coverage}% of the required skills for {job_role.role_name}."
                )
                bottleneck.recommendation = (
                    f"Strengthen your projects using missing role skills such as: "
                    f"{missing_skill_names if missing_skill_names else 'more target-role skills'}."
                )

            elif project_tool_coverage < 50:
                bottleneck.main_bottleneck = "Weak Project Tool Evidence"
                bottleneck.explanation = (
                    f"You added {project_count} project(s), but they only show "
                    f"{project_tool_coverage}% of the required tools for {job_role.role_name}."
                )
                bottleneck.recommendation = (
                    f"Update your projects to include tools such as: "
                    f"{missing_tool_names if missing_tool_names else 'more industry tools'}."
                )

            elif project_relevance_score < 70:
                bottleneck.main_bottleneck = "Weak Project Relevance"
                bottleneck.explanation = (
                    f"You added {project_count} project(s), but their combined relevance score is only "
                    f"{project_relevance_score}% for {job_role.role_name}."
                )
                bottleneck.recommendation = (
                    "Build one stronger role-specific project instead of adding many weak or unrelated projects."
                )

            elif assessment.overall_readiness_score < 75:
                bottleneck.main_bottleneck = "Moderate Readiness"
                bottleneck.explanation = (
                    f"Your projects are relevant, but your overall readiness score is "
                    f"{assessment.overall_readiness_score}%, which is still below industry-ready level."
                )
                bottleneck.recommendation = (
                    "Improve your weakest readiness area and polish your best project into portfolio quality."
                )

            else:
                bottleneck.main_bottleneck = "No Major Bottleneck"
                bottleneck.explanation = (
                    f"You appear ready for {job_role.role_name} based on your current skills, tools, and projects."
                )
                bottleneck.recommendation = (
                    "Focus on interview preparation, portfolio polishing, and job applications."
                )

            bottleneck.save()

            return redirect(
                'bottleneck_result',
                bottleneck_id=bottleneck.id
            )

    return render(
        request,
        'career_app/bottleneck_detection.html',
        {'form': form}
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

        matched_skills = user_skills.filter(
            id__in=target_required_skills.values_list('id', flat=True)
        )

        missing_skills = target_required_skills.exclude(
            id__in=user_skills.values_list('id', flat=True)
        )

        matched_tools = user_tools.filter(
            id__in=target_required_tools.values_list('id', flat=True)
        )

        missing_tools = target_required_tools.exclude(
            id__in=user_tools.values_list('id', flat=True)
        )

        skill_match_score = (
            matched_skills.count() / target_required_skills.count()
        ) * 100 if target_required_skills.count() > 0 else 0

        tool_match_score = (
            matched_tools.count() / target_required_tools.count()
        ) * 100 if target_required_tools.count() > 0 else 0

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
            'career_transition_result',
            analysis_id=analysis.id
        )

    return render(
        request,
        'career_app/career_transition_analysis.html',
        {'form': form}
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