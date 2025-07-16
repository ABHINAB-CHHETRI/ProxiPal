from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),

    # Auth routes
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('register/', views.register, name='register'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('send-request/<int:user_id>/', views.send_friend_request, name='send_friend_request'),
    path('accept-request/<int:request_id>/', views.accept_friend_request, name='accept_friend_request'),
    path('reject-request/<int:request_id>/', views.reject_friend_request, name='reject_friend_request'),
    path('unfriend/<int:user_id>/', views.unfriend, name='unfriend'),
    path('block/<int:user_id>/', views.block_user, name='block_user'),
    path('unblock/<int:user_id>/', views.unblock_user, name='unblock_user'),
    path('ajax/update-location/', views.update_location_ajax, name='update_location_ajax'),
    path('track/<int:friend_id>/', views.track_friend, name='track_friend'),


]
