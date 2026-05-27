from django.contrib import admin
from django.urls import include, path
from django.urls import re_path
from django.views.generic import TemplateView


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("ingest.urls")),
    re_path(r"^(?!static/|api/|admin/).*$", TemplateView.as_view(template_name="index.html")),
]
