from django.urls import path

from . import views

urlpatterns = [
    path("", views.home_redirect, name="home"),
    path("wizard/<int:step>/", views.wizard_step, name="wizard_step"),
    path("wizard/reset/", views.wizard_reset, name="wizard_reset"),
    path("wizard/review/", views.wizard_review, name="wizard_review"),
    path("wizard/history/", views.wizard_history, name="wizard_history"),
    path("wizard/result/<str:batch_id>/", views.wizard_result, name="wizard_result"),
    path("export/", views.export_excel, name="export_excel"),
]
