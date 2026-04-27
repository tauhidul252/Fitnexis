from django.shortcuts import render

def home(request):
    return render(request, 'home.html')

def login_view(request):
    return render(request, 'login.html')

def signup_view(request):
    return render(request, 'signup.html')

def forgot_password_view(request):
    return render(request, 'forgot_password.html')
