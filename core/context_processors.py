from .decorators import is_manager

def aap_globals(request):
    return {
        "is_manager": is_manager(request.user) if request.user.is_authenticated else False
    }
