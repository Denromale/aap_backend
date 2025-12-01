from django.urls import path
from . import views

urlpatterns = [
    # Корень сайта – логин
    path('', views.login_view, name='login'),

    # Главная после входа
    path('home/', views.home, name='home'),

    # Личный кабинет / список клиентов
    path('dashboard/', views.dashboard, name='dashboard'),

    # Клиенты
    path('clients/add/', views.client_create, name='client_create'),
    path('clients/<int:pk>/details/', views.client_detail, name='client_detail'),
    path('clients/<int:pk>/edit/', views.client_edit, name='client_edit'),
    path('clients/<int:pk>/delete/', views.client_delete, name='client_delete'),
    path('clients/<int:pk>/team/', views.client_team, name='client_team'),

    # Запити
    path('requests/', views.requests_view, name='requests'),

    # База документів
    path('documents/', views.documents_view, name='documents'),
    path('documents/<int:doc_id>/update/', views.document_update_type, name='document_update_type'),
    path('documents/<int:pk>/delete/', views.document_delete, name='document_delete'),

    # Выход
    path('logout/', views.logout_view, name='logout'),
]
