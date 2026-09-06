from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from userauth import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('upload/', views.upload, name='upload'),
    path('find-users/', views.find_users, name='find_users'),
    path('connect/<int:user_id>/', views.connect, name='connect'),
    path('like/<uuid:post_id>/', views.like_post, name='like_post'),
    # Comments
    path('comment/<uuid:post_id>/', views.add_comment, name='add_comment'),
    path('comment/delete/<int:comment_id>/', views.delete_comment, name='delete_comment'),
    # Share
    path('share/<uuid:post_id>/', views.share_post, name='share_post'),
    # Delete Post
    path('post/delete/<uuid:post_id>/', views.delete_post, name='delete_post'),
    # Notifications
    path('notifications/', views.notifications_view, name='notifications'),
    # Direct Messages
    path('messages/', views.inbox, name='inbox'),
    path('messages/<int:user_id>/', views.conversation, name='conversation'),
    # Group Messages
    path('messages/group/create/', views.create_group, name='create_group'),
    path('messages/group/<uuid:group_id>/', views.group_conversation, name='group_conversation'),
    path('post/edit/<uuid:post_id>/', views.edit_post, name='edit_post'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('meetings/', views.meetings_dashboard, name='meetings_dashboard'),
    path('meetings/<int:meeting_id>/', views.meeting_detail, name='meeting_detail'),
    path('meetings/save/', views.save_meeting_transcript, name='save_meeting_transcript'),
    path('profile/<str:username>/', views.profile, name='profile'),
    path('messages/merge-call/', views.merge_call, name='merge_call'),
    path('settings/', views.user_settings, name='user_settings'),
    path('block/<str:username>/', views.block_user, name='block_user'),
    path('unblock/<str:username>/', views.unblock_user, name='unblock_user'),
    path('settings/delete-request/', views.request_account_deletion, name='request_account_deletion'),
    path('settings/delete-verify/', views.verify_account_deletion, name='verify_account_deletion'),
    path('settings/ping-time/', views.ping_screen_time, name='ping_screen_time'),
    # Password Reset URLs
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='userauth/password_reset.html',
        email_template_name='userauth/password_reset_email.html',
        subject_template_name='userauth/password_reset_subject.txt',
        success_url='/password_reset/done/'
    ), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='userauth/password_reset_done.html'
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='userauth/password_reset_confirm.html',
        success_url='/reset/done/'
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='userauth/password_reset_complete.html'
    ), name='password_reset_complete'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
