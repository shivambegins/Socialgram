import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import Message


class ChatConsumer(AsyncWebsocketConsumer):
    """Real-time chat between two users."""

    async def connect(self):
        self.me = self.scope['user']
        self.partner_id = self.scope['url_route']['kwargs']['user_id']
        # Deterministic room name (same for both directions)
        ids = sorted([self.me.id, int(self.partner_id)])
        self.room = f"chat_{ids[0]}_{ids[1]}"
        await self.channel_layer.group_add(self.room, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.room, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        text = data.get('text', '').strip()
        if not text:
            return
        # Persist message
        partner = await database_sync_to_async(User.objects.get)(id=self.partner_id)
        msg = await database_sync_to_async(Message.objects.create)(
            sender=self.me, recipient=partner, text=text
        )
        await self.channel_layer.group_send(self.room, {
            'type': 'chat_message',
            'text': text,
            'sender_id': self.me.id,
            'sender': self.me.username,
            'time': msg.created_at.strftime('%I:%M %p'),
        })

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat',
            'text': event['text'],
            'sender_id': event['sender_id'],
            'sender': event['sender'],
            'time': event['time'],
        }))


class CallConsumer(AsyncWebsocketConsumer):
    """WebRTC signaling relay for voice and video calls."""

    async def connect(self):
        self.me = self.scope['user']
        self.partner_id = self.scope['url_route']['kwargs']['user_id']
        ids = sorted([self.me.id, int(self.partner_id)])
        self.room = f"call_{ids[0]}_{ids[1]}"
        await self.channel_layer.group_add(self.room, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.room, self.channel_name)
        # Notify partner when someone leaves
        await self.channel_layer.group_send(self.room, {
            'type': 'call_signal',
            'signal': {'type': 'call-ended'},
            'sender_id': self.me.id,
        })

    async def receive(self, text_data):
        data = json.loads(text_data)
        # Forward any WebRTC signal (offer, answer, ice-candidate, call-ended, call-rejected)
        await self.channel_layer.group_send(self.room, {
            'type': 'call_signal',
            'signal': data,
            'sender_id': self.me.id,
        })

    async def call_signal(self, event):
        # Only forward to the OTHER person in the room
        if event['sender_id'] != self.me.id:
            await self.send(text_data=json.dumps(event['signal']))

from .models import MessageGroup, GroupMessage, GroupMember

class GroupChatConsumer(AsyncWebsocketConsumer):
    """Real-time group chat."""

    async def connect(self):
        self.me = self.scope['user']
        self.group_id = self.scope['url_route']['kwargs']['group_id']
        self.room = f"group_chat_{self.group_id}"
        
        # Check membership
        is_member = await database_sync_to_async(
            GroupMember.objects.filter(group_id=self.group_id, user=self.me).exists
        )()
        if not is_member:
            await self.close()
            return
            
        await self.channel_layer.group_add(self.room, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.room, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        text = data.get('text', '').strip()
        if not text:
            return
            
        # Persist message
        grp = await database_sync_to_async(MessageGroup.objects.get)(id=self.group_id)
        msg = await database_sync_to_async(GroupMessage.objects.create)(
            group=grp, sender=self.me, text=text
        )
        await self.channel_layer.group_send(self.room, {
            'type': 'group_chat_message',
            'text': text,
            'sender_id': self.me.id,
            'sender': self.me.username,
            'time': msg.created_at.strftime('%I:%M %p'),
        })

    async def group_chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat',
            'text': event['text'],
            'sender_id': event['sender_id'],
            'sender': event['sender'],
            'time': event['time'],
        }))

class GroupCallConsumer(AsyncWebsocketConsumer):
    """WebRTC signaling relay for Full Mesh multi-party group calls."""

    async def connect(self):
        self.me = self.scope['user']
        self.group_id = self.scope['url_route']['kwargs']['group_id']
        self.room = f"group_call_{self.group_id}"
        
        is_member = await database_sync_to_async(
            GroupMember.objects.filter(group_id=self.group_id, user=self.me).exists
        )()
        if not is_member:
            await self.close()
            return
            
        await self.channel_layer.group_add(self.room, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.room, self.channel_name)
        # Notify others that this peer left
        await self.channel_layer.group_send(self.room, {
            'type': 'call_signal',
            'signal': {'type': 'peer-left', 'peer_id': self.me.id},
            'sender_id': self.me.id,
        })

    async def receive(self, text_data):
        data = json.loads(text_data)
        
        # Append sender_id so receivers know who the signal is from
        data['sender_id'] = self.me.id
        
        # If signal is targeted at a specific peer, pass target_id
        await self.channel_layer.group_send(self.room, {
            'type': 'call_signal',
            'signal': data,
            'sender_id': self.me.id,
            'target_id': data.get('target_id')
        })

    async def call_signal(self, event):
        # Don't send back to self
        if event['sender_id'] == self.me.id:
            return
            
        # If target_id is specified, only send to that peer
        target = event.get('target_id')
        if target and target != self.me.id:
            return
            
        await self.send(text_data=json.dumps(event['signal']))
