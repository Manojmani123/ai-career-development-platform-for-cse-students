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


from django.conf import settings

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

    if form.is_valid():
        form.save()
        return redirect('view_role_skills')

    return render(request, 'career_app/assign_skill_to_role.html', {'form': form})


@login_required
def view_role_skills(request):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    role_skills = JobRoleSkill.objects.select_related('job_role', 'skill').all()
    return render(request, 'career_app/view_role_skills.html', {'role_skills': role_skills})


