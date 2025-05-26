# 6. ADMIN (admin.py)
from django.contrib import admin
from .models import MessagePage, Message

@admin.register(MessagePage)
class MessagePageAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'created_at', 'is_public']
    list_filter = ['is_public', 'created_at']
    search_fields = ['title', 'user__username']

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['text', 'page', 'order', 'created_at']
    list_filter = ['page', 'created_at']
    search_fields = ['text']