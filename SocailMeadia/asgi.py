"""
ASGI config for SocailMeadia project.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SocailMeadia.settings')
django.setup()

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import userauth.routing

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(
        URLRouter(userauth.routing.websocket_urlpatterns)
    ),
})
