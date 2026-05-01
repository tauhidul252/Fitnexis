from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import Subscription, MembershipPlan, GymClass, Booking, Attendance, FitnessProgress, Payment, Offer

def home(request):
    classes = GymClass.objects.all()[:3]
    trainers = User.objects.filter(profile__role='trainer')[:3]
    schedule = GymClass.objects.all().order_by('schedule_time')[:5]
    
    context = {
        'classes': classes,
        'trainers': trainers,
        'schedule': schedule,
    }
    return render(request, 'home.html', context)

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

def logout_view(request):
    logout(request)
    return redirect('home')

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

from django.utils import timezone
from datetime import timedelta

@login_required
def member_dashboard(request):
    user = request.user
    progress = FitnessProgress.objects.filter(user=user).order_by('-date')[:5]
    
    # Only show future bookings
    bookings = Booking.objects.filter(user=user, gym_class__schedule_time__gte=timezone.now()).order_by('gym_class__schedule_time')
    
    # Calculate attendance % (last 30 days)
    last_30_days = timezone.now().date() - timedelta(days=30)
    attendance_count = Attendance.objects.filter(user=user, date__gte=last_30_days, is_present=True).count()
    # Simple logic: assume 20 possible gym days in 30 days for 100%
    attendance_pct = min(int((attendance_count / 20) * 100), 100)
    
    # Current Plan
    active_sub = Subscription.objects.filter(user=user, is_active=True).first()
    
    # Next Class
    next_booking = bookings.first()
    
    # Available Classes to book
    available_classes = GymClass.objects.filter(schedule_time__gte=timezone.now()).exclude(booking__user=user)[:6]

    context = {
        'progress': progress,
        'bookings': bookings,
        'attendance_pct': attendance_pct,
        'active_sub': active_sub,
        'next_booking': next_booking,
        'available_classes': available_classes,
    }
    return render(request, 'dashboard_member.html', context)

@login_required
def book_class(request, class_id):
    from .models import GymClass, Booking
    gym_class = GymClass.objects.get(id=class_id)
    # Check capacity
    current_bookings = Booking.objects.filter(gym_class=gym_class).count()
    if current_bookings < gym_class.capacity:
        Booking.objects.get_or_create(user=request.user, gym_class=gym_class)
        messages.success(request, f"Successfully booked {gym_class.title}!")
    else:
        messages.error(request, "This class is full.")
    return redirect('member_dashboard')

@login_required
def update_progress(request):
    if request.method == 'POST':
        weight = request.POST.get('weight')
        notes = request.POST.get('notes')
        FitnessProgress.objects.create(user=request.user, weight=weight, notes=notes)
        messages.success(request, "Progress updated!")
    return redirect('member_dashboard')

@login_required
def trainer_dashboard(request):
    user = request.user
    classes = GymClass.objects.filter(trainer=user).order_by('schedule_time')
    
    # Unique members who booked this trainer's classes
    assigned_members_count = Booking.objects.filter(gym_class__trainer=user).values('user').distinct().count()
    
    # Next session
    next_session = classes.filter(schedule_time__gte=timezone.now()).first()
    
    # Today's classes and their bookings
    today = timezone.now().date()
    todays_classes = classes.filter(schedule_time__date=today)
    todays_bookings = Booking.objects.filter(gym_class__in=todays_classes)
    
    context = {
        'classes': classes,
        'assigned_members_count': assigned_members_count,
        'next_session': next_session,
        'todays_bookings': todays_bookings,
    }
    return render(request, 'dashboard_trainer.html', context)

@login_required
def mark_attendance(request, booking_id):
    if request.user.profile.role != 'trainer':
        messages.error(request, "Only trainers can mark attendance.")
        return redirect('dashboard')
        
    booking = Booking.objects.get(id=booking_id)
    Attendance.objects.get_or_create(
        user=booking.user,
        date=timezone.now().date(),
        is_present=True
    )
    messages.success(request, f"Attendance marked for {booking.user.username}")
    return redirect('trainer_dashboard')

@login_required
def add_class(request):
    from .models import GymClass
    if request.user.profile.role != 'trainer':
        messages.error(request, "Only trainers can add classes.")
        return redirect('dashboard')
        
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        schedule_time = request.POST.get('schedule_time')
        capacity = request.POST.get('capacity', 20)
        
        GymClass.objects.create(
            title=title,
            description=description,
            schedule_time=schedule_time,
            capacity=capacity,
            trainer=request.user
        )
        messages.success(request, f"Class '{title}' created successfully!")
    return redirect('trainer_dashboard')

@login_required
def admin_dashboard(request):
    from django.db.models import Sum
    plans = MembershipPlan.objects.all()
    payments = Payment.objects.all().order_by('-timestamp')[:10]
    offers = Offer.objects.all()
    
    # Total revenue
    total_revenue = Payment.objects.aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Active members
    active_members_count = Subscription.objects.filter(is_active=True).values('user').distinct().count()
    
    # Recent activity
    recent_payments_count = Payment.objects.filter(timestamp__date=timezone.now().date()).count()
    
    context = {
        'plans': plans,
        'payments': payments,
        'offers': offers,
        'total_revenue': total_revenue,
        'active_members_count': active_members_count,
        'recent_payments_count': recent_payments_count,
    }
    return render(request, 'dashboard_admin.html', context)

@login_required
def add_plan(request):
    from .models import MembershipPlan
    if request.user.profile.role != 'admin':
        messages.error(request, "Only admins can add plans.")
        return redirect('dashboard')
        
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        price = request.POST.get('price')
        duration_months = request.POST.get('duration_months', 1)
        
        MembershipPlan.objects.create(
            title=title,
            description=description,
            price=price,
            duration_months=duration_months
        )
        messages.success(request, f"Plan '{title}' created successfully!")
    return redirect('admin_dashboard')

@login_required
def edit_plan(request, plan_id):
    from .models import MembershipPlan
    if request.user.profile.role != 'admin':
        messages.error(request, "Only admins can edit plans.")
        return redirect('dashboard')
        
    plan = MembershipPlan.objects.get(id=plan_id)
    if request.method == 'POST':
        plan.title = request.POST.get('title')
        plan.description = request.POST.get('description')
        plan.price = request.POST.get('price')
        plan.duration_months = request.POST.get('duration_months')
        plan.save()
        messages.success(request, f"Plan '{plan.title}' updated successfully!")
    return redirect('admin_dashboard')

@login_required
def delete_plan(request, plan_id):
    from .models import MembershipPlan
    if request.user.profile.role != 'admin':
        messages.error(request, "Only admins can delete plans.")
        return redirect('dashboard')
        
    plan = MembershipPlan.objects.get(id=plan_id)
    title = plan.title
    plan.delete()
    messages.success(request, f"Plan '{title}' deleted successfully!")
    return redirect('admin_dashboard')

def error_404(request, exception):
    return render(request, '404.html', status=404)
