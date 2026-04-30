"""
URL configuration for fitnexis project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from django.shortcuts import render
from django.views.generic import RedirectView
from core.views import home, login_view, signup_view, logout_view, forgot_password_view, dashboard, member_dashboard, trainer_dashboard, admin_dashboard, error_404

urlpatterns = [
    path('admin/logout/', RedirectView.as_view(url='/logout/', permanent=True)),
    path('', home, name='home'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('signup/', signup_view, name='signup'),
    path('forgot-password/', forgot_password_view, name='forgot_password'),
    path('dashboard/', dashboard, name='dashboard'),
    path('dashboard/member/', member_dashboard, name='member_dashboard'),
    path('dashboard/trainer/', trainer_dashboard, name='trainer_dashboard'),
    path('dashboard/admin/', admin_dashboard, name='admin_dashboard'),
    path('404/', lambda r: render(r, '404.html'), name='test_404'),
]

handler404 = 'core.views.error_404'
