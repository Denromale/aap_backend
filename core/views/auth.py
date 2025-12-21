from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from core.models import News

# ---------- HOME ----------

@login_required
def home(request):
    """
    Главная страница AAP с новостями.
    Пока новости общие для всех организаций.
    """
    news_list = News.objects.filter(is_published=True).order_by("-created_at")[:5]
    return render(request, "core/home.html", {"news_list": news_list})

def login_view(request):
    """
    Простой логин через username/password + галочка 'Запомнить'.
    Если галочка НЕ отмечена — сессия живёт до закрытия браузера.
    Если отмечена — используется стандартный срок жизни сессии
    (SESSION_COOKIE_AGE в settings.py).
    """
    error = None

    if request.method == "POST":
        username = request.POST.get("username") or ""
        password = request.POST.get("password") or ""
        remember_me = request.POST.get("remember_me")  # 'on' если отмечено, None если нет

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)

            # если галочка НЕ стоит — сессия до закрытия браузера
            if not remember_me:
                request.session.set_expiry(0)

            return redirect("home")
        else:
            error = "Невірний логін або пароль"

    return render(request, "core/login.html", {"error": error})

# ---------- AUTH ----------

def logout_view(request):
    logout(request)
    return redirect("login")
