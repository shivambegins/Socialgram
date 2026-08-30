from django import template
import re
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.urls import reverse

register = template.Library()

@register.filter
def urlize_tags(text):
    if not text:
        return ''
    text = escape(text)
    
    def replace_tag(match):
        username = match.group(1)
        url = reverse('profile', args=[username])
        return f'<a href="{url}" style="color:var(--cyan); font-weight:600; text-decoration:none;">@{username}</a>'
        
    return mark_safe(re.sub(r'@(\w+)', replace_tag, text))
