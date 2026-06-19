from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from django.conf import settings

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),

    path('login/', auth_views.LoginView.as_view(
        template_name='career_app/login.html',
        next_page='dashboard_redirect'
    ), name='login'),

    path('logout/', views.logout_view, name='logout'),

    path('dashboard-redirect/', views.dashboard_redirect, name='dashboard_redirect'),
    path('dashboard/', views.user_dashboard, name='user_dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('super-admin-dashboard/', views.super_admin_dashboard, name='super_admin_dashboard'),
    path('generate-admin-invite/', views.generate_admin_invite, name='generate_admin_invite'),
    path('admin-request/', views.admin_request, name='admin_request'),
    path('view-admin-requests/', views.view_admin_requests, name='view_admin_requests'),
    path('approve-admin-request/<int:request_id>/', views.approve_admin_request, name='approve_admin_request'),
    path('reject-admin-request/<int:request_id>/', views.reject_admin_request, name='reject_admin_request'),
    path('password-reset/', auth_views.PasswordResetView.as_view(
    template_name='career_app/password_reset.html',
    email_template_name='career_app/password_reset_email.html',
    success_url='/password-reset/done/',
    extra_email_context={
        'domain': '127.0.0.1:8000',
        'protocol': 'http',
    }
), name='password_reset'),

path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
    template_name='career_app/password_reset_done.html'
), name='password_reset_done'),

path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
    template_name='career_app/password_reset_confirm.html',
    success_url='/password-reset-complete/'
), name='password_reset_confirm'),

path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
    template_name='career_app/password_reset_complete.html'
), name='password_reset_complete'),
path('add-job-role/', views.add_job_role, name='add_job_role'),
path('view-job-roles/', views.view_job_roles, name='view_job_roles'),

path('add-skill/', views.add_skill, name='add_skill'),
path('view-skills/', views.view_skills, name='view_skills'),

path('assign-skill-to-role/', views.assign_skill_to_role, name='assign_skill_to_role'),
path('view-role-skills/', views.view_role_skills, name='view_role_skills'),
path('career-match/', views.career_match, name='career_match'),
path('career-match-result/<int:result_id>/', views.career_match_result, name='career_match_result'),
path(
    'add-learning-resource/',
    views.add_learning_resource,
    name='add_learning_resource'
),

path(
    'view-learning-resources/',
    views.view_learning_resources,
    name='view_learning_resources'
),
path(
    'learning-roadmap/<int:result_id>/',
    views.learning_roadmap,
    name='learning_roadmap'
),
path('create-profile/', views.create_profile, name='create_profile'),
path('view-profile/', views.view_profile, name='view_profile'),
path('edit-profile/', views.edit_profile, name='edit_profile'),
]