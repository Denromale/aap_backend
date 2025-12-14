from django.shortcuts import redirect
from django.urls import reverse
from .models import Client

def get_active_client(request):
    client_id = request.session.get("active_client_id")
    if not client_id:
        return None

    try:
        return Client.objects.get(pk=client_id, organization=request.organization)
    except Client.DoesNotExist:
        request.session.pop("active_client_id", None)
        return None

def require_active_client(request):
    client = get_active_client(request)
    if client:
        return client, None
    return None, redirect(reverse("dashboard"))
