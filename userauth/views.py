from django.contrib.auth.models import AbstractUser
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Max
from django.views.decorators.http import require_POST
from django.conf import settings
from django.core.cache import cache
import requests
from .models import Profile, Post, Connection, Like, Comment, Notification, Message, Share, PostView, MessageGroup, GroupMember, GroupMessage
# Create your views here.
def signup(request):
    if request.method == 'POST':
        try:
            fnm = request.POST.get('fnm')
            emailid = request.POST.get('emailid')
            pwd = request.POST.get('pwd')

            my_user = User.objects.create_user(username=fnm, password=pwd, email=emailid)
            Profile.objects.create(user=my_user, id_user=my_user.id)

            return redirect('/login')   # no login() call — force them to log in fresh

        except IntegrityError:
            invalid = "User already exists"
            return render(request, 'userauth/signup.html', {'invalid': invalid})

    return render(request, 'userauth/signup.html')

def login_view(request):
    error = None
    if request.method == 'POST':
        fnm = request.POST.get('fnm')
        pwd = request.POST.get('pwd')
        user = authenticate(request, username=fnm, password=pwd)
        if user is not None:
            login(request, user)
            return redirect('/')
        else:
            error = "Invalid username or password"
    return render(request, 'userauth/login.html', {'error': error})
def logout_view(request):
    logout(request)
    return redirect('/login')
@login_required
def upload(request):
    if request.method == 'POST':
        image = request.FILES.get('image-upload')
        caption = request.POST.get('captions')
        Post.objects.create(user=request.user, image=image, caption=caption)
        return redirect('/')
    return redirect('/')


@login_required
def home(request):
    posts = Post.objects.select_related('user').prefetch_related(
        'like_set__user', 'comments__user', 'shares'
    ).order_by('-created_AT')
    liked_ids   = set(Like.objects.filter(user=request.user).values_list('post_id', flat=True))
    shared_ids  = set(Share.objects.filter(user=request.user).values_list('post_id', flat=True))
    connected_ids = set(Connection.objects.filter(from_user=request.user).values_list('to_user_id', flat=True))
    suggestions = get_suggested_users(request.user)
    news        = get_trending_news()
    unread_notif_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    # Record PostViews in bulk (ignore already-viewed)
    viewed_ids = set(PostView.objects.filter(user=request.user).values_list('post_id', flat=True))
    new_views  = [PostView(user=request.user, post=p) for p in posts if p.id not in viewed_ids]
    if new_views:
        PostView.objects.bulk_create(new_views, ignore_conflicts=True)
    # Get recent conversations
    partners_sent = Message.objects.filter(sender=request.user).values_list('recipient_id', flat=True)
    partners_recv = Message.objects.filter(recipient=request.user).values_list('sender_id', flat=True)
    partner_ids   = set(partners_sent) | set(partners_recv)
    partners = User.objects.filter(id__in=partner_ids).select_related('profile')
    
    conversations = []
    for partner in partners:
        last_msg = (
            Message.objects
            .filter(
                Q(sender=request.user, recipient=partner) |
                Q(sender=partner, recipient=request.user)
            )
            .order_by('-created_at')
            .first()
        )
        unread = Message.objects.filter(sender=partner, recipient=request.user, is_read=False).count()
        conversations.append({'partner': partner, 'last_msg': last_msg, 'unread': unread})
    conversations.sort(key=lambda c: c['last_msg'].created_at if c['last_msg'] else 0, reverse=True)

    return render(request, 'main.html', {
        'posts': posts,
        'liked_ids': liked_ids,
        'shared_ids': shared_ids,
        'connected_ids': connected_ids,
        'suggestions': suggestions,
        'news': news,
        'unread_notif_count': unread_notif_count,
        'conversations': conversations,
    })

@login_required
def find_users(request):
    query = request.GET.get('q', '').strip()
    connected_ids = set(Connection.objects.filter(from_user=request.user).values_list('to_user_id', flat=True))
    users_qs = (User.objects
                .exclude(id=request.user.id)
                .select_related('profile'))
    if query:
        users_qs = users_qs.filter(Q(username__icontains=query))
    # Build (user, mutual_count) pairs
    mutual_qs = (
        Connection.objects
        .filter(from_user_id__in=connected_ids, to_user__in=users_qs)
        .values('to_user_id')
        .annotate(cnt=Count('id'))
    )
    mutual_map = {row['to_user_id']: row['cnt'] for row in mutual_qs}
    users = [(u, mutual_map.get(u.id, 0)) for u in users_qs]
    return render(request, 'find_users.html', {
        'users': users,
        'connected_ids': connected_ids,
        'query': query,
    })

@login_required
def connect(request, user_id):
    target = get_object_or_404(User, id=user_id)
    _, created = Connection.objects.get_or_create(from_user=request.user, to_user=target)
    if created:
        Notification.objects.create(
            recipient=target, sender=request.user, notif_type='follow'
        )
    return redirect(request.META.get('HTTP_REFERER', '/'))

@login_required
def like_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    like, created = Like.objects.get_or_create(user=request.user, post=post)
    if not created:
        like.delete()
        post.no_likes = max(0, post.no_likes - 1)
    else:
        post.no_likes += 1
        if post.user != request.user:
            Notification.objects.create(
                recipient=post.user, sender=request.user, notif_type='like', post=post
            )
    post.save()
    return redirect(request.META.get('HTTP_REFERER', '/'))


def get_trending_news():
    news = cache.get('trending_news')
    if news is None:
        try:
            resp = requests.get(
                'https://newsapi.org/v2/top-headlines',
                params={
                    'apiKey': settings.CURRENTS_API_KEY,
                    'category': 'technology',
                    'language': 'en',
                    'pageSize': 5,
                },
                timeout=5,
            )
            data = resp.json()
            news = data.get('articles', [])[:5]
        except Exception:
            news = []
        cache.set('trending_news', news, 60 * 30)
    return news

def get_suggested_users(user, limit=5):
    """
    Returns a list of (User, mutual_count) tuples ordered by mutual connections.
    Falls back to same-location users, then random members.
    mutual_count is 0 for fallback entries.
    """
    connected_ids = set(
        Connection.objects.filter(from_user=user).values_list('to_user_id', flat=True)
    )
    excluded_ids = connected_ids | {user.id}
    # Tier 1: mutual connections
    mutual_rows = (
        Connection.objects
        .filter(from_user_id__in=connected_ids)
        .exclude(to_user_id__in=excluded_ids)
        .values('to_user_id')
        .annotate(mutual_count=Count('to_user_id'))
        .order_by('-mutual_count')[:limit]
    )
    mutual_map = {row['to_user_id']: row['mutual_count'] for row in mutual_rows}
    suggested_ids = list(mutual_map.keys())
    tier1_users = list(User.objects.filter(id__in=suggested_ids).select_related('profile'))
    tier1_users.sort(key=lambda u: suggested_ids.index(u.id))
    suggestions = [(u, mutual_map[u.id]) for u in tier1_users]
    # Tier 2: same location
    if len(suggestions) < limit:
        try:
            location = user.profile.location
        except Profile.DoesNotExist:
            location = ''
        if location:
            seen_ids = excluded_ids | {u.id for u, _ in suggestions}
            more = (User.objects
                    .filter(profile__location=location)
                    .exclude(id__in=seen_ids)
                    .select_related('profile')[:limit - len(suggestions)])
            suggestions += [(u, 0) for u in more]
    # Tier 3: anyone else
    if len(suggestions) < limit:
        seen_ids = excluded_ids | {u.id for u, _ in suggestions}
        more = (User.objects
                .exclude(id__in=seen_ids)
                .select_related('profile')
                .order_by('?')[:limit - len(suggestions)])
        suggestions += [(u, 0) for u in more]
    return suggestions


# ── Comments ──────────────────────────────────────────────────────────────────

@login_required
@require_POST
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    text = request.POST.get('text', '').strip()
    if text:
        comment = Comment.objects.create(user=request.user, post=post, text=text)
        if post.user != request.user:
            Notification.objects.create(
                recipient=post.user, sender=request.user,
                notif_type='comment', post=post
            )
    return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required
@require_POST
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id, user=request.user)
    comment.delete()
    return redirect(request.META.get('HTTP_REFERER', '/'))


# ── Share ─────────────────────────────────────────────────────────────────────

@login_required
def share_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    _, created = Share.objects.get_or_create(user=request.user, post=post)
    if created and post.user != request.user:
        Notification.objects.create(
            recipient=post.user, sender=request.user,
            notif_type='share', post=post
        )
    return redirect(request.META.get('HTTP_REFERER', '/'))


# ── Delete Post ───────────────────────────────────────────────────────────────

@login_required
@require_POST
def delete_post(request, post_id):
    partners_sent = Message.objects.filter(sender=request.user).values_list('recipient_id', flat=True)
    partners_recv = Message.objects.filter(recipient=request.user).values_list('sender_id', flat=True)
    partner_ids   = set(partners_sent) | set(partners_recv)
    partners = User.objects.filter(id__in=partner_ids).select_related('profile')
    
    conversations = []
    for partner in partners:
        last_msg = (
            Message.objects
            .filter(
                Q(sender=request.user, recipient=partner) |
                Q(sender=partner, recipient=request.user)
            )
            .order_by('-created_at')
            .first()
        )
        unread = Message.objects.filter(sender=partner, recipient=request.user, is_read=False).count()
        conversations.append({'partner': partner, 'last_msg': last_msg, 'unread': unread})
    conversations.sort(key=lambda c: c['last_msg'].created_at if c['last_msg'] else 0, reverse=True)

    return render(request, 'main.html', {
        'posts': posts,
        'liked_ids': liked_ids,
        'shared_ids': shared_ids,
        'connected_ids': connected_ids,
        'suggestions': suggestions,
        'news': news,
        'unread_notif_count': unread_notif_count,
        'conversations': conversations,
    })

@login_required
def find_users(request):
    query = request.GET.get('q', '').strip()
    connected_ids = set(Connection.objects.filter(from_user=request.user).values_list('to_user_id', flat=True))
    users_qs = (User.objects
                .exclude(id=request.user.id)
                .select_related('profile'))
    if query:
        users_qs = users_qs.filter(Q(username__icontains=query))
    # Build (user, mutual_count) pairs
    mutual_qs = (
        Connection.objects
        .filter(from_user_id__in=connected_ids, to_user__in=users_qs)
        .values('to_user_id')
        .annotate(cnt=Count('id'))
    )
    mutual_map = {row['to_user_id']: row['cnt'] for row in mutual_qs}
    users = [(u, mutual_map.get(u.id, 0)) for u in users_qs]
    return render(request, 'find_users.html', {
        'users': users,
        'connected_ids': connected_ids,
        'query': query,
    })

@login_required
def connect(request, user_id):
    target = get_object_or_404(User, id=user_id)
    _, created = Connection.objects.get_or_create(from_user=request.user, to_user=target)
    if created:
        Notification.objects.create(
            recipient=target, sender=request.user, notif_type='follow'
        )
    return redirect(request.META.get('HTTP_REFERER', '/'))

@login_required
def like_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    like, created = Like.objects.get_or_create(user=request.user, post=post)
    if not created:
        like.delete()
        post.no_likes = max(0, post.no_likes - 1)
    else:
        post.no_likes += 1
        if post.user != request.user:
            Notification.objects.create(
                recipient=post.user, sender=request.user, notif_type='like', post=post
            )
    post.save()
    return redirect(request.META.get('HTTP_REFERER', '/'))


def get_trending_news():
    news = cache.get('trending_news')
    if news is None:
        try:
            resp = requests.get(
                'https://newsapi.org/v2/top-headlines',
                params={
                    'apiKey': settings.CURRENTS_API_KEY,
                    'category': 'technology',
                    'language': 'en',
                    'pageSize': 5,
                },
                timeout=5,
            )
            data = resp.json()
            news = data.get('articles', [])[:5]
        except Exception:
            news = []
        cache.set('trending_news', news, 60 * 30)
    return news

def get_suggested_users(user, limit=5):
    """
    Returns a list of (User, mutual_count) tuples ordered by mutual connections.
    Falls back to same-location users, then random members.
    mutual_count is 0 for fallback entries.
    """
    connected_ids = set(
        Connection.objects.filter(from_user=user).values_list('to_user_id', flat=True)
    )
    excluded_ids = connected_ids | {user.id}
    # Tier 1: mutual connections
    mutual_rows = (
        Connection.objects
        .filter(from_user_id__in=connected_ids)
        .exclude(to_user_id__in=excluded_ids)
        .values('to_user_id')
        .annotate(mutual_count=Count('to_user_id'))
        .order_by('-mutual_count')[:limit]
    )
    mutual_map = {row['to_user_id']: row['mutual_count'] for row in mutual_rows}
    suggested_ids = list(mutual_map.keys())
    tier1_users = list(User.objects.filter(id__in=suggested_ids).select_related('profile'))
    tier1_users.sort(key=lambda u: suggested_ids.index(u.id))
    suggestions = [(u, mutual_map[u.id]) for u in tier1_users]
    # Tier 2: same location
    if len(suggestions) < limit:
        try:
            location = user.profile.location
        except Profile.DoesNotExist:
            location = ''
        if location:
            seen_ids = excluded_ids | {u.id for u, _ in suggestions}
            more = (User.objects
                    .filter(profile__location=location)
                    .exclude(id__in=seen_ids)
                    .select_related('profile')[:limit - len(suggestions)])
            suggestions += [(u, 0) for u in more]
    # Tier 3: anyone else
    if len(suggestions) < limit:
        seen_ids = excluded_ids | {u.id for u, _ in suggestions}
        more = (User.objects
                .exclude(id__in=seen_ids)
                .select_related('profile')
                .order_by('?')[:limit - len(suggestions)])
        suggestions += [(u, 0) for u in more]
    return suggestions


# ── Comments ──────────────────────────────────────────────────────────────────

@login_required
@require_POST
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    text = request.POST.get('text', '').strip()
    if text:
        comment = Comment.objects.create(user=request.user, post=post, text=text)
        if post.user != request.user:
            Notification.objects.create(
                recipient=post.user, sender=request.user,
                notif_type='comment', post=post
            )
    return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required
@require_POST
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id, user=request.user)
    comment.delete()
    return redirect(request.META.get('HTTP_REFERER', '/'))


# ── Share ─────────────────────────────────────────────────────────────────────

@login_required
def share_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    _, created = Share.objects.get_or_create(user=request.user, post=post)
    if created and post.user != request.user:
        Notification.objects.create(
            recipient=post.user, sender=request.user,
            notif_type='share', post=post
        )
    return redirect(request.META.get('HTTP_REFERER', '/'))


# ── Delete Post ───────────────────────────────────────────────────────────────

@login_required
@require_POST
def delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id, user=request.user)
    post.delete()
    return redirect('/')


# ── Notifications ─────────────────────────────────────────────────────────────

@login_required
def notifications_view(request):
    notifs = Notification.objects.filter(recipient=request.user).select_related('sender', 'post')
    notifs.filter(is_read=False).update(is_read=True)
    return render(request, 'notifications.html', {'notifs': notifs})


# ── Direct Messages ───────────────────────────────────────────────────────────

@login_required
def inbox(request):
    """Show one row per conversation partner, with latest message preview."""
    user = request.user
    # All user IDs this user has exchanged messages with
    partners_sent = Message.objects.filter(sender=user).values_list('recipient_id', flat=True)
    partners_recv = Message.objects.filter(recipient=user).values_list('sender_id', flat=True)
    partner_ids   = set(partners_sent) | set(partners_recv)
    partners = User.objects.filter(id__in=partner_ids).select_related('profile')
    
    # Build conversation previews
    conversations = []
    for partner in partners:
        last_msg = (
            Message.objects
            .filter(
                Q(sender=user, recipient=partner) |
                Q(sender=partner, recipient=user)
            )
            .order_by('-created_at')
            .first()
        )
        unread = Message.objects.filter(sender=partner, recipient=user, is_read=False).count()
        conversations.append({'partner': partner, 'last_msg': last_msg, 'unread': unread, 'is_group': False})
        
    # Fetch group conversations
    groups = MessageGroup.objects.filter(members__user=user)
    for grp in groups:
        last_msg = grp.messages.order_by('-created_at').first()
        conversations.append({
            'is_group': True,
            'group': grp,
            'partner': grp,  # alias for templating consistency
            'last_msg': last_msg,
            'unread': 0
        })

    conversations.sort(key=lambda c: c['last_msg'].created_at if c['last_msg'] else c.get('group', getattr(c.get('partner'), 'date_joined', None)).created_at if c.get('is_group') else 0, reverse=True)
    
    all_users = User.objects.exclude(id=user.id)
    return render(request, 'inbox.html', {'conversations': conversations, 'all_users': all_users})


@login_required
def conversation(request, user_id):
    partner  = get_object_or_404(User, id=user_id)
    messages = Message.objects.filter(
        Q(sender=request.user, recipient=partner) |
        Q(sender=partner, recipient=request.user)
    ).order_by('created_at')
    # Mark received messages as read
    messages.filter(sender=partner, recipient=request.user, is_read=False).update(is_read=True)
    if request.method == 'POST':
        text = request.POST.get('text', '').strip()
        if text:
            Message.objects.create(sender=request.user, recipient=partner, text=text)
        return redirect('conversation', user_id=partner.id)
    return render(request, 'conversation.html', {'partner': partner, 'messages': messages})
# ── Groups ────────────────────────────────────────────────────────────────────

@login_required
def create_group(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        member_ids = request.POST.getlist('members')
        if name and member_ids:
            grp = MessageGroup.objects.create(name=name, admin=request.user)
            GroupMember.objects.create(group=grp, user=request.user)
            for uid in member_ids:
                if int(uid) != request.user.id:
                    GroupMember.objects.create(group=grp, user_id=uid)
            return redirect('group_conversation', group_id=grp.id)
    return redirect('inbox')

@login_required
def group_conversation(request, group_id):
    grp = get_object_or_404(MessageGroup, id=group_id)
    if not GroupMember.objects.filter(group=grp, user=request.user).exists():
        return redirect('inbox')
        
    messages = grp.messages.select_related('sender').all()
    members = grp.members.select_related('user__profile').all()
    
    return render(request, 'group_conversation.html', {
        'group': grp,
        'messages': messages,
        'members': members,
    })

@login_required
def edit_post(request, post_id):
    post = get_object_or_404(Post, id=post_id, user=request.user)
    if request.method == 'POST':
        caption = request.POST.get('caption', '')
        if caption:
            post.caption = caption
            post.save()
    return redirect(request.META.get('HTTP_REFERER', 'home'))

@login_required
def profile(request, username):
    user = get_object_or_404(User, username=username)
    posts = Post.objects.filter(user=user).order_by('-created_AT')
    connected_ids = set(Connection.objects.filter(from_user=request.user).values_list('to_user_id', flat=True))
    
    return render(request, 'profile.html', {
        'profile_user': user,
        'posts': posts,
        'connected_ids': connected_ids
    })
