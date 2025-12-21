from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # --- Auth ---
    path("", views.home, name="home"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    path("password_reset/", auth_views.PasswordResetView.as_view(), name="password_reset"),
    path("password_reset/done/", auth_views.PasswordResetDoneView.as_view(), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("reset/done/", auth_views.PasswordResetCompleteView.as_view(), name="password_reset_complete"),

    # --- Dashboard / News ---
    path("dashboard/", views.dashboard, name="dashboard"),
    path("news/<int:pk>/", views.news_detail, name="news_detail"),

    # --- Clients ---
    path("clients/add/", views.client_create, name="client_create"),
    path("clients/<int:pk>/details/", views.client_detail, name="client_detail"),
    path("clients/<int:pk>/edit/", views.client_edit, name="client_edit"),
    path("clients/<int:pk>/delete/", views.client_delete, name="client_delete"),
    path("clients/<int:pk>/team/", views.client_team, name="client_team"),
    path("clients/<int:pk>/complete/", views.client_complete, name="client_complete"),

    path("projects/archive/", views.projects_archive, name="projects_archive"),

    # --- Active client ---
    path("set-active-client/", views.set_active_client, name="set_active_client"),

    # --- Requests ---
    path("requests/", views.requests_view, name="requests"),

    # --- Documents ---
    path("documents/", views.documents_view, name="documents"),
    path("documents/<int:doc_id>/update/", views.document_update_type, name="document_update_type"),
    path("documents/<int:pk>/delete/", views.document_delete, name="document_delete"),
    path("documents/<int:doc_id>/download/", views.document_download, name="document_download"),
    path("documents/download/", views.documents_download_zip, name="documents_download_zip"),

    # --- Audit ---
    path("audit/step/<int:step_order>/", views.audit_step_view, name="audit_step"),
    path(
        "audit/step/<int:step_order>/action/<slug:key>/",
        views.audit_step_action_run,
        name="audit_step_action_run",
    ),

    # --- Audit files ---
    path("audit/procedure-file/upload/", views.procedure_file_upload, name="procedure_file_upload"),
    path("procedure-file/<int:pk>/delete/", views.procedure_file_delete, name="procedure_file_delete"),

    # --- Step 1.5 (legacy) ---
    path(
        "audit/step15/independence/",
        views.step15_generate_independence,
        name="step15_generate_independence",
    ),
    path(
        "audit/step15/order/",
        views.step15_generate_order__legacy,
        name="step15_generate_order_legacy",
    ),

    # --- Metrics ---
    path("metrics/", views.metrics_view, name="metrics"),

    # --- Legacy client steps ---
    path("client/step-1/", views.client_step_1, name="client_step_1"),
    path("client/step-2/", views.client_step_2, name="client_step_2"),
]
