from django.contrib.auth.models import User
from django.db import models

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)  # ✅ Newly added


    def __str__(self):
        return self.user.username

class Friendship(models.Model):
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friendships_sent')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friendships_received')
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.from_user} ➜ {self.to_user}"
    
class FriendRequest(models.Model):
    from_user = models.ForeignKey(User, related_name='sent_requests', on_delete=models.CASCADE)
    to_user = models.ForeignKey(User, related_name='received_requests', on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=[
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('blocked', 'Blocked')
    ], default='pending')
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('from_user', 'to_user')

    def __str__(self):
        return f"{self.from_user} → {self.to_user} ({self.status})"

class LocationHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    latitude = models.FloatField()
    longitude = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} @ {self.timestamp}"

