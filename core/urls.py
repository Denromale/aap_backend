from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),              # главная
    path('login/', views.login_view, name='login'), # логин
    path('logout/', views.logout_view, name='logout'),

    path('dashboard/', views.dashboard, name='dashboard'),
    path("news/<int:pk>/", views.news_detail, name="news_detail"),

    path('clients/add/', views.client_create, name='client_create'),
    path('clients/<int:pk>/details/', views.client_detail, name='client_detail'),
    path('clients/<int:pk>/edit/', views.client_edit, name='client_edit'),
    path('clients/<int:pk>/delete/', views.client_delete, name='client_delete'),
    path('clients/<int:pk>/team/', views.client_team, name='client_team'),

    path('requests/', views.requests_view, name='requests'),

    path('documents/', views.documents_view, name='documents'),
    path('documents/<int:doc_id>/update/', views.document_update_type, name='document_update_type'),
    path('documents/<int:pk>/delete/', views.document_delete, name='document_delete'),

    path("set-active-client/", views.set_active_client, name="set_active_client"),
    path("password_reset/",auth_views.PasswordResetView.as_view(),name="password_reset",    ),
    path(        "password_reset/done/",        auth_views.PasswordResetDoneView.as_view(),        name="password_reset_done",    ),
    path(        "reset/<uidb64>/<token>/",        auth_views.PasswordResetConfirmView.as_view(),        name="password_reset_confirm",    ),
    path(        "reset/done/",        auth_views.PasswordResetCompleteView.as_view(),        name="password_reset_complete",    ),
    path("metrics/", views.metrics_view, name="metrics"),
    path("clients/<int:pk>/complete/", views.client_complete, name="client_complete"),
    path("projects/archive/", views.projects_archive, name="projects_archive"),
    path("client/step-1/", views.client_step_1, name="client_step_1"),
    path("client/step-2/", views.client_step_2, name="client_step_2"),
    path("procedure-file/<int:pk>/delete/", views.procedure_file_delete, name="procedure_file_delete"),


]


