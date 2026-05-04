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


# ─────────────────────────────────────────────
#  MANAGE MEMBERS
# ─────────────────────────────────────────────

@login_required
def manage_members(request):
    if request.user.profile.role != 'admin':
        messages.error(request, "Access denied.")
        return redirect('dashboard')

    from django.db.models import Count
    members = User.objects.filter(profile__role='member').select_related('profile').prefetch_related(
        'subscription_set__plan', 'attendance_set', 'booking_set'
    )

    # AI insight per member
    member_data = []
    for m in members:
        att_count = m.attendance_set.filter(is_present=True).count()
        bookings   = m.booking_set.count()
        active_sub = m.subscription_set.filter(is_active=True).first()

        # Simple rule-based AI insight
        if att_count == 0:
            insight = "⚠️ No attendance recorded. Consider a re-engagement email."
            risk    = "high"
        elif att_count < 5:
            insight = "📉 Low attendance. Recommend a personal trainer check-in."
            risk    = "medium"
        elif bookings == 0:
            insight = "📅 Active but not booking classes. Suggest group sessions."
            risk    = "low"
        else:
            insight = "✅ Engaged member. Great retention candidate."
            risk    = "good"

        member_data.append({
            'user'       : m,
            'att_count'  : att_count,
            'bookings'   : bookings,
            'active_sub' : active_sub,
            'insight'    : insight,
            'risk'       : risk,
        })

    plans = MembershipPlan.objects.all()
    context = {
        'member_data': member_data,
        'plans'      : plans,
        'total_members': len(member_data),
        'at_risk'    : sum(1 for m in member_data if m['risk'] == 'high'),
    }
    return render(request, 'manage_members.html', context)


@login_required
def add_member(request):
    if request.user.profile.role != 'admin':
        return redirect('dashboard')
    if request.method == 'POST':
        username  = request.POST.get('username')
        email     = request.POST.get('email')
        password  = request.POST.get('password')
        phone     = request.POST.get('phone', '')
        if User.objects.filter(username=username).exists():
            messages.error(request, f"Username '{username}' already exists.")
        else:
            user = User.objects.create_user(username=username, email=email, password=password)
            user.profile.role  = 'member'
            user.profile.phone = phone
            user.profile.save()
            messages.success(request, f"Member '{username}' added successfully!")
    return redirect('manage_members')


@login_required
def edit_member(request, member_id):
    if request.user.profile.role != 'admin':
        return redirect('dashboard')
    member = User.objects.get(id=member_id)
    if request.method == 'POST':
        member.email            = request.POST.get('email', member.email)
        member.first_name       = request.POST.get('first_name', member.first_name)
        member.last_name        = request.POST.get('last_name', member.last_name)
        member.profile.phone    = request.POST.get('phone', member.profile.phone)
        member.profile.address  = request.POST.get('address', member.profile.address)
        member.save()
        member.profile.save()
        messages.success(request, f"Member '{member.username}' updated.")
    return redirect('manage_members')


@login_required
def delete_member(request, member_id):
    if request.user.profile.role != 'admin':
        return redirect('dashboard')
    user = User.objects.get(id=member_id)
    uname = user.username
    user.delete()
    messages.success(request, f"Member '{uname}' deleted.")
    return redirect('manage_members')


# ─────────────────────────────────────────────
#  MANAGE TRAINERS
# ─────────────────────────────────────────────

@login_required
def manage_trainers(request):
    if request.user.profile.role != 'admin':
        messages.error(request, "Access denied.")
        return redirect('dashboard')

    trainers = User.objects.filter(profile__role='trainer').select_related('profile')

    trainer_data = []
    for t in trainers:
        classes      = GymClass.objects.filter(trainer=t)
        classes_count = classes.count()
        members_count = Booking.objects.filter(gym_class__trainer=t).values('user').distinct().count()
        total_bookings = Booking.objects.filter(gym_class__trainer=t).count()

        # AI performance insight
        if classes_count == 0:
            insight     = "⚠️ No classes assigned. Assign classes to activate trainer."
            performance = "inactive"
        elif members_count == 0:
            insight     = "📭 Classes created but no bookings yet. Promote to members."
            performance = "low"
        elif total_bookings < 5:
            insight     = "📈 Growing presence. Encourage marketing of their sessions."
            performance = "medium"
        elif members_count >= 10:
            insight     = "🌟 Top performer! High member engagement and retention."
            performance = "top"
        else:
            insight     = "✅ Consistent performance. Good class attendance rates."
            performance = "good"

        trainer_data.append({
            'user'         : t,
            'classes_count': classes_count,
            'members_count': members_count,
            'total_bookings': total_bookings,
            'insight'      : insight,
            'performance'  : performance,
            'classes'      : classes,
        })

    context = {
        'trainer_data' : trainer_data,
        'total_trainers': len(trainer_data),
        'top_performers': sum(1 for t in trainer_data if t['performance'] == 'top'),
    }
    return render(request, 'manage_trainers.html', context)


@login_required
def add_trainer(request):
    if request.user.profile.role != 'admin':
        return redirect('dashboard')
    if request.method == 'POST':
        username = request.POST.get('username')
        email    = request.POST.get('email')
        password = request.POST.get('password')
        bio      = request.POST.get('bio', '')
        if User.objects.filter(username=username).exists():
            messages.error(request, f"Username '{username}' already exists.")
        else:
            user = User.objects.create_user(username=username, email=email, password=password)
            user.profile.role = 'trainer'
            user.profile.bio  = bio
            user.profile.save()
            messages.success(request, f"Trainer '{username}' added successfully!")
    return redirect('manage_trainers')


@login_required
def edit_trainer(request, trainer_id):
    if request.user.profile.role != 'admin':
        return redirect('dashboard')
    trainer = User.objects.get(id=trainer_id)
    if request.method == 'POST':
        trainer.email          = request.POST.get('email', trainer.email)
        trainer.first_name     = request.POST.get('first_name', trainer.first_name)
        trainer.last_name      = request.POST.get('last_name', trainer.last_name)
        trainer.profile.bio    = request.POST.get('bio', trainer.profile.bio)
        trainer.profile.phone  = request.POST.get('phone', trainer.profile.phone)
        trainer.save()
        trainer.profile.save()
        messages.success(request, f"Trainer '{trainer.username}' updated.")
    return redirect('manage_trainers')


@login_required
def delete_trainer(request, trainer_id):
    if request.user.profile.role != 'admin':
        return redirect('dashboard')
    user = User.objects.get(id=trainer_id)
    uname = user.username
    user.delete()
    messages.success(request, f"Trainer '{uname}' deleted.")
    return redirect('manage_trainers')


# ─────────────────────────────────────────────
#  AI CHAT API  (no external key needed)
# ─────────────────────────────────────────────

from django.http import JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt

@login_required
def ai_chat(request):
    """Rule-based AI assistant that answers questions about gym data."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    data = json.loads(request.body)
    query = data.get('message', '').lower().strip()

    # ── gather live stats ──
    total_members  = User.objects.filter(profile__role='member').count()
    total_trainers = User.objects.filter(profile__role='trainer').count()
    total_classes  = GymClass.objects.count()
    total_bookings = Booking.objects.count()
    total_revenue  = Payment.objects.aggregate(__import__('django.db.models', fromlist=['Sum']).Sum('amount'))['amount__sum'] or 0
    active_subs    = Subscription.objects.filter(is_active=True).count()
    at_risk        = User.objects.filter(profile__role='member').exclude(
        attendance__is_present=True
    ).distinct().count()

    # ── rule-based NLU ──
    reply = ""

    if any(w in query for w in ['member', 'members', 'সদস্য']):
        if any(w in query for w in ['how many', 'total', 'count', 'কতজন', 'কত']):
            reply = f"📊 There are currently **{total_members} members** registered in the system. Of these, **{active_subs} have active subscriptions**."
        elif any(w in query for w in ['risk', 'inactive', 'churn', 'ঝুঁকি']):
            reply = f"⚠️ **{at_risk} members** have no attendance records and may be at risk of churning. I recommend sending them a re-engagement email or offering a discount."
        elif any(w in query for w in ['active', 'subscription', 'plan']):
            reply = f"✅ **{active_subs} members** currently have active subscriptions. That's {round((active_subs/total_members*100) if total_members else 0)}% of your total member base."
        else:
            reply = f"👥 Member summary: **{total_members} total**, **{active_subs} active subscriptions**, **{at_risk} at-risk** (no attendance)."

    elif any(w in query for w in ['trainer', 'trainers', 'প্রশিক্ষক']):
        if any(w in query for w in ['how many', 'total', 'count', 'কতজন']):
            reply = f"🏋️ You have **{total_trainers} trainers** on staff managing **{total_classes} classes** with a combined **{total_bookings} bookings**."
        elif any(w in query for w in ['best', 'top', 'perform', 'সেরা']):
            top_trainer = User.objects.filter(profile__role='trainer').annotate(
                bc=__import__('django.db.models', fromlist=['Count']).Count('classes_taught__booking')
            ).order_by('-bc').first()
            if top_trainer:
                bc = Booking.objects.filter(gym_class__trainer=top_trainer).count()
                reply = f"🌟 Your top-performing trainer is **{top_trainer.get_full_name() or top_trainer.username}** with **{bc} total bookings** across their classes."
            else:
                reply = "No trainer data available yet."
        else:
            reply = f"🏋️ Trainer overview: **{total_trainers} trainers**, managing **{total_classes} classes**, with **{total_bookings} total bookings**."

    elif any(w in query for w in ['revenue', 'money', 'income', 'আয়', 'রাজস্ব']):
        reply = f"💰 Total lifetime revenue is **${total_revenue:,.2f}**. You have **{active_subs} active subscriptions** currently generating recurring income."

    elif any(w in query for w in ['class', 'classes', 'ক্লাস']):
        most_booked = GymClass.objects.annotate(
            bc=__import__('django.db.models', fromlist=['Count']).Count('booking')
        ).order_by('-bc').first()
        if most_booked:
            reply = f"📅 You have **{total_classes} classes** in total. The most popular is **'{most_booked.title}'** with **{most_booked.bc} bookings**."
        else:
            reply = f"📅 There are **{total_classes} classes** currently scheduled."

    elif any(w in query for w in ['attendance', 'উপস্থিতি']):
        total_att = Attendance.objects.filter(is_present=True).count()
        reply = f"📋 There are **{total_att} total attendance records** across all members. Members with zero attendance: **{at_risk}**."

    elif any(w in query for w in ['summary', 'overview', 'report', 'সারসংক্ষেপ', 'সারাংশ']):
        reply = (
            f"📈 **Fitnexis AI Summary**\n\n"
            f"• 👥 Members: **{total_members}** ({active_subs} active subscriptions)\n"
            f"• 🏋️ Trainers: **{total_trainers}**\n"
            f"• 📅 Classes: **{total_classes}** ({total_bookings} total bookings)\n"
            f"• 💰 Revenue: **${total_revenue:,.2f}**\n"
            f"• ⚠️ At-risk members: **{at_risk}**\n\n"
            f"Overall gym health looks {'🟢 good' if at_risk < total_members * 0.3 else '🔴 needs attention'}."
        )

    elif any(w in query for w in ['help', 'what can you', 'সাহায্য', 'কি করতে পারো']):
        reply = (
            "🤖 I'm the **Fitnexis AI Assistant**. You can ask me:\n\n"
            "• *How many members do we have?*\n"
            "• *Who is the top trainer?*\n"
            "• *What is our total revenue?*\n"
            "• *Which class is most booked?*\n"
            "• *How many at-risk members are there?*\n"
            "• *Give me a full summary*"
        )

    else:
        reply = (
            "🤔 I'm not sure about that. Try asking:\n"
            "• 'How many members do we have?'\n"
            "• 'Who is the top trainer?'\n"
            "• 'Give me a summary'\n"
            "• 'What is our revenue?'"
        )

    return JsonResponse({'reply': reply})
