from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from userauth import views

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
    path('profile/<str:username>/', views.profile, name='profile'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
