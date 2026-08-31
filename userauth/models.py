from django.utils import timezone
import uuid
from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    id_user = models.IntegerField(primary_key=True, default=0)
    bio = models.TextField(blank=True, default='')
    profileimg = models.ImageField(upload_to='profile_images', blank=True, null=True, default='blank_profile-pictures.png')
    coverimg = models.ImageField(upload_to='cover_images', blank=True, null=True, default='blank-cover.png')
    location = models.TextField(max_length=100, blank=True, default='')
    view_count = models.IntegerField(default=0)

    def __str__(self):
        return self.user.username


class Post(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='posts_images', blank=True, null=True, default='blank_posts.png')
    caption = models.TextField(max_length=100, blank=True, default='')
    created_AT = models.DateTimeField(auto_now_add=True)
    no_likes = models.IntegerField(default=0)

    def __str__(self):
        return self.user.username


class Connection(models.Model):
    from_user = models.ForeignKey(User, related_name='connections_sent', on_delete=models.CASCADE)
    to_user = models.ForeignKey(User, related_name='connections_received', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('from_user', 'to_user')

    def __str__(self):
        return f"{self.from_user.username} → {self.to_user.username}"


class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')


class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, related_name='comments', on_delete=models.CASCADE)
    text = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.username} on {self.post.id}: {self.text[:40]}"


class Notification(models.Model):
    NOTIF_TYPES = [
        ('like',    'Liked your post'),
        ('comment', 'Commented on your post'),
        ('follow',  'Started following you'),
        ('share',   'Shared your post'),
    ]
    recipient = models.ForeignKey(User, related_name='notifications', on_delete=models.CASCADE)
    sender    = models.ForeignKey(User, related_name='sent_notifications', on_delete=models.CASCADE)
    notif_type = models.CharField(max_length=10, choices=NOTIF_TYPES)
    post      = models.ForeignKey(Post, null=True, blank=True, on_delete=models.CASCADE)
    is_read   = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.sender.username} → {self.recipient.username} ({self.notif_type})"


class Message(models.Model):
    sender    = models.ForeignKey(User, related_name='sent_messages', on_delete=models.CASCADE)
    recipient = models.ForeignKey(User, related_name='received_messages', on_delete=models.CASCADE)
    text      = models.TextField(max_length=1000)
    is_read   = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender.username} → {self.recipient.username}: {self.text[:40]}"


class Share(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, related_name='shares', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')

    def __str__(self):
        return f"{self.user.username} shared {self.post.id}"


class PostView(models.Model):
    user      = models.ForeignKey(User, on_delete=models.CASCADE)
    post      = models.ForeignKey(Post, related_name='views', on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')

    def __str__(self):
        return f"{self.user.username} viewed {self.post.id}"
# ── Group Messaging ───────────────────────────────────────────────────────────

class MessageGroup(models.Model):
    import uuid
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    admin = models.ForeignKey(User, on_delete=models.CASCADE, related_name='administered_groups')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class GroupMember(models.Model):
    group = models.ForeignKey(MessageGroup, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('group', 'user')

class GroupMessage(models.Model):
    group = models.ForeignKey(MessageGroup, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

class BlockedUser(models.Model):
    blocker = models.ForeignKey(User, related_name='blocking', on_delete=models.CASCADE)
    blocked = models.ForeignKey(User, related_name='blocked_by', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('blocker', 'blocked')

    def __str__(self):
        return f'{self.blocker.username} blocks {self.blocked.username}'

class OTPToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    purpose = models.CharField(max_length=50, default='delete_account')

    def __str__(self):
        return f'{self.user.username} - {self.token}'


class DailyScreenTime(models.Model):
    from django.utils import timezone
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    time_seconds = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ('user', 'date')

    def __str__(self):
        return f'{self.user.username} - {self.date} - {self.time_seconds}s'


class MemorableMoment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='moments')
    file = models.FileField(upload_to='moments_files')
    caption = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.username}'s moment"


