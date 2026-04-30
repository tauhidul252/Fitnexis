from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import MembershipPlan, GymClass, Booking, Attendance, FitnessProgress, Payment, Offer

def home(request):
    return render(request, 'home.html')

from django.contrib.auth import login, authenticate, logout
from .forms import SignupForm
from django.contrib import messages

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid username or password.")
    return render(request, 'login.html')

def signup_view(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = SignupForm()
    return render(request, 'signup.html', {'form': form})

def forgot_password_view(request):
    return render(request, 'forgot_password.html')

@login_required
def dashboard(request):
    role = request.user.profile.role
    if role == 'admin':
        return redirect('admin_dashboard')
    elif role == 'trainer':
        return redirect('trainer_dashboard')
    else:
        return redirect('member_dashboard')

@login_required
def member_dashboard(request):
    user = request.user
    progress = FitnessProgress.objects.filter(user=user).order_by('-date')[:5]
    bookings = Booking.objects.filter(user=user)
    attendance = Attendance.objects.filter(user=user).order_by('-date')[:10]
    plans = MembershipPlan.objects.all()
    context = {
        'progress': progress,
        'bookings': bookings,
        'attendance': attendance,
        'plans': plans,
    }
    return render(request, 'dashboard_member.html', context)

@login_required
def trainer_dashboard(request):
    user = request.user
    classes = GymClass.objects.filter(trainer=user)
    # Get all members booked for this trainer's classes
    bookings = Booking.objects.filter(gym_class__trainer=user)
    context = {
        'classes': classes,
        'bookings': bookings,
    }
    return render(request, 'dashboard_trainer.html', context)

@login_required
def admin_dashboard(request):
    plans = MembershipPlan.objects.all()
    payments = Payment.objects.all().order_by('-timestamp')[:10]
    offers = Offer.objects.all()
    context = {
        'plans': plans,
        'payments': payments,
        'offers': offers,
    }
    return render(request, 'dashboard_admin.html', context)
