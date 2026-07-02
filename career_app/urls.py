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
path('add-learning-resource/', views.add_learning_resource, name='add_learning_resource'),

path('view-learning-resources/', views.view_learning_resources, name='view_learning_resources'),
path('learning-roadmap/<int:result_id>/', views.learning_roadmap, name='learning_roadmap'),
path('create-profile/', views.create_profile, name='create_profile'),
path('view-profile/', views.view_profile, name='view_profile'),
path('edit-profile/', views.edit_profile, name='edit_profile'),
path('readiness-assessment/', views.readiness_assessment, name='readiness_assessment'),
path('readiness-result/<int:assessment_id>/', views.readiness_result, name='readiness_result'),
path('add-industry-tool/', views.add_industry_tool, name='add_industry_tool'),
path('view-industry-tools/', views.view_industry_tools, name='view_industry_tools'),
path('assign-tool-to-role/', views.assign_tool_to_role, name='assign_tool_to_role'),
path('view-role-tools/', views.view_role_tools, name='view_role_tools'),
path(
    'bottleneck-detection/',
    views.bottleneck_detection,
    name='bottleneck_detection'
),

path(
    'bottleneck-result/<int:bottleneck_id>/',
    views.bottleneck_result,
    name='bottleneck_result'
),

path(
    'add-project/',
    views.add_project,
    name='add_project'
),

path(
    'view-projects/',
    views.view_projects,
    name='view_projects'
),
path(
    'delete-project/<int:project_id>/',
    views.delete_project,
    name='delete_project'
),

path(
    'career-transition-analysis/',
    views.career_transition_analysis,
    name='career_transition_analysis'
),

path(
    'career-transition-result/<int:analysis_id>/',
    views.career_transition_result,
    name='career_transition_result'
),
path('import-dataset/', views.import_dataset, name='import_dataset'),
path(
    'add-competency-group/',
    views.add_competency_group,
    name='add_competency_group'
),

path(
    'view-competency-groups/',
    views.view_competency_groups,
    name='view_competency_groups'
),

path(
    'add-competency-group-members/',
    views.add_competency_group_members,
    name='add_competency_group_members'
),
]