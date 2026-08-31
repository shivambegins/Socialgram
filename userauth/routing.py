from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r"^ws/chat/(?P<user_id>\d+)/$", consumers.ChatConsumer.as_asgi()),
    re_path(r"^ws/call/(?P<user_id>\d+)/$", consumers.CallConsumer.as_asgi()),
    re_path(r"^ws/group_chat/(?P<group_id>[a-f0-9\-]+)/$", consumers.GroupChatConsumer.as_asgi()),
    re_path(r"^ws/group_call/(?P<group_id>[a-f0-9\-]+)/$", consumers.GroupCallConsumer.as_asgi()),
    re_path(r"^ws/notifications/$", consumers.NotificationConsumer.as_asgi()),
]
