from django.shortcuts import render, redirect
from django.contrib.auth import login
from .forms import CustomRegisterForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import FriendRequest
from django.db import models
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from geopy.distance import geodesic
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from geopy.geocoders import Nominatim
from .models import LocationHistory
import json
def home(request):
    return render(request, 'index.html')

def register(request):
    if request.method == 'POST':
        form = CustomRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('login')
    else:
        form = CustomRegisterForm()
    return render(request, 'register.html', {'form': form})

@login_required
def dashboard(request):
    user = request.user

    # 1. All users except self
    all_users = User.objects.exclude(id=user.id)

    # 2. Block logic
    blocked_users = FriendRequest.objects.filter(from_user=user, status='blocked').values_list('to_user_id', flat=True)
    blocked_by_users = FriendRequest.objects.filter(to_user=user, status='blocked').values_list('from_user_id', flat=True)

    # 3. Friend relationships
    friends = FriendRequest.objects.filter(
        Q(from_user=user) | Q(to_user=user),
        status='accepted'
    )

    friend_ids = set()
    for f in friends:
        friend_ids.add(f.from_user.id)
        friend_ids.add(f.to_user.id)

    # 4. Sent/received requests
    sent_requests = FriendRequest.objects.filter(from_user=user).exclude(status='rejected')
    sent_to_ids = sent_requests.values_list('to_user_id', flat=True)

    received_requests = FriendRequest.objects.filter(to_user=user, status='pending')
    received_from_ids = received_requests.values_list('from_user_id', flat=True)

    # 5. Suggestions (cleaned)
    suggestions = all_users.exclude(
        Q(id__in=friend_ids) |
        Q(id__in=sent_to_ids) |
        Q(id__in=received_from_ids) |
        Q(id__in=blocked_users) |
        Q(id__in=blocked_by_users) |
        Q(is_superuser=True)
    )

    # 6. Friend Distances
    friend_distances = []
    if hasattr(user, 'profile') and user.profile.latitude and user.profile.longitude:
        for f in friends:
            other = f.to_user if f.from_user == user else f.from_user
            if hasattr(other, 'profile') and other.profile.latitude and other.profile.longitude:
                distance = geodesic(
                    (user.profile.latitude, user.profile.longitude),
                    (other.profile.latitude, other.profile.longitude)
                ).km
                friend_distances.append((other.username, round(distance, 2)))

    return render(request, 'dashboard.html', {
        'users': suggestions,
        'sent_requests': sent_requests,
        'received_requests': received_requests,
        'friends': friends,
        'blocked_users': User.objects.filter(id__in=blocked_users),
        'friend_distances': friend_distances
    })

@login_required
def send_friend_request(request, user_id):
    to_user = User.objects.get(id=user_id)
    # Check if already friends or blocked
    existing = FriendRequest.objects.filter(
        (
            Q(from_user=request.user, to_user=to_user) |
            Q(from_user=to_user, to_user=request.user)
        ) &
        Q(status__in=['accepted', 'blocked'])
    ).exists()
    if not existing:
        FriendRequest.objects.get_or_create(from_user=request.user, to_user=to_user, defaults={'status': 'pending'})
    return redirect('dashboard')

@login_required
def accept_friend_request(request, request_id):
    f_request = FriendRequest.objects.get(id=request_id, to_user=request.user)
    f_request.status = 'accepted'
    f_request.save()
    return redirect('dashboard')

@login_required
def reject_friend_request(request, request_id):
    f_request = FriendRequest.objects.get(id=request_id, to_user=request.user)
    f_request.status = 'rejected'
    f_request.save()
    return redirect('dashboard')

@login_required
def unfriend(request, user_id):
    FriendRequest.objects.filter(
        Q(from_user=request.user, to_user__id=user_id, status='accepted') |
        Q(from_user__id=user_id, to_user=request.user, status='accepted')
    ).delete()
    return redirect('dashboard')

@login_required
def block_user(request, user_id):
    # Either create or update a friend request and mark as blocked
    obj, created = FriendRequest.objects.get_or_create(
        from_user=request.user,
        to_user_id=user_id,
        defaults={'status': 'blocked'}
    )
    if not created:
        obj.status = 'blocked'
        obj.save()
    return redirect('dashboard')

@login_required
def unblock_user(request, user_id):
    FriendRequest.objects.filter(from_user=request.user, to_user_id=user_id, status='blocked').delete()
    return redirect('dashboard')


@csrf_exempt  # Allows POST from JS
@login_required
def update_location_ajax(request):
    if request.method == 'POST':
        lat = request.POST.get('latitude')
        lon = request.POST.get('longitude')

        if lat and lon:
            profile = request.user.profile
            profile.latitude = lat
            profile.longitude = lon
            profile.save()
            return JsonResponse({'status': 'success'})
        else:
            return JsonResponse({'status': 'invalid data'}, status=400)
    return JsonResponse({'status': 'only POST allowed'}, status=405)

@csrf_exempt
@login_required
def update_location(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        lat = data.get('latitude')
        lng = data.get('longitude')

        geolocator = Nominatim(user_agent="proxipal")
        location = geolocator.reverse(f"{lat}, {lng}", language="en")

        if location:
            address = location.address
            profile = request.user.profile
            profile.latitude = lat
            profile.longitude = lng
            profile.address = address
            profile.save()
            return JsonResponse({'status': 'success', 'address': address})
        else:
            return JsonResponse({'status': 'error', 'message': 'Could not reverse geocode'}, status=400)


@login_required
def track_friend(request, friend_id):
    friend = get_object_or_404(User, id=friend_id)

    # Ensure the users are friends
    is_friend = FriendRequest.objects.filter(
        Q(from_user=request.user, to_user=friend) | Q(from_user=friend, to_user=request.user),
        status='accepted'
    ).exists()
    if not is_friend:
        return render(request, 'error.html', {'message': 'Not friends with this user.'})

    user_profile = request.user.profile
    friend_profile = friend.profile

    # Get current coordinates (use default 0.0 if missing)
    user_lat = user_profile.latitude or 0.0
    user_lon = user_profile.longitude or 0.0
    friend_lat = friend_profile.latitude or 0.0
    friend_lon = friend_profile.longitude or 0.0

    # Calculate distance
    distance = None
    if all([user_lat, user_lon, friend_lat, friend_lon]):
        distance = round(geodesic((user_lat, user_lon), (friend_lat, friend_lon)).km, 2)

    # Get friend's location history (latest 20 entries)
    location_history = LocationHistory.objects.filter(user=friend).order_by('-timestamp')[:20]

    return render(request, 'track_friend.html', {
        'friend': friend,
        'distance': distance,
        'user_lat': user_lat,
        'user_lon': user_lon,
        'friend_lat': friend_lat,
        'friend_lon': friend_lon,
        'location_history': location_history if location_history.exists() else [],
    })