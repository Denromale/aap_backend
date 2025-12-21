from .permissions import is_manager
from .models import Client

def aap_globals(request):
    active_client = None

    try:
        client_id = request.session.get("active_client_id")
        org = getattr(request, "organization", None)

        if client_id and org:
            active_client = Client.objects.filter(
                id=client_id,
                organization=org
            ).first()
    except Exception:
        active_client = None

    return {
        "is_manager": is_manager(request.user) if request.user.is_authenticated else False,
        "active_client": active_client,
    }
