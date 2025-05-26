# ENHANCED URLS (urls.py - Enhanced)
from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('create/', views.create_page, name='create_page'),
    path('edit/<uuid:page_id>/', views.edit_page, name='edit_page'),
    path('view/<uuid:page_id>/', views.view_page, name='view_page'),
    path('analytics/<uuid:page_id>/', views.page_analytics, name='page_analytics'),
    
    # duplicate a page window.location.href = `{% url 'duplicate_page' page.id %}`;
    path('duplicate/<uuid:page_id>/', views.duplicate_page, name='duplicate_page'),
    path('delete/<uuid:page_id>/', views.delete_page, name='delete_page'),
    
    # API endpoints
    path('api/add-message/<uuid:page_id>/', views.add_message, name='add_message'),
    path('api/delete-message/<int:message_id>/', views.delete_message, name='delete_message'),
    path('api/copy-messages/', views.copy_messages, name='copy_messages'),
    path('api/update-message/<int:message_id>/', views.update_message, name='update_message'),
    path('api/reorder-messages/<uuid:page_id>/', views.reorder_messages, name='reorder_messages'),
    path('api/update-message/<int:message_id>/', views.update_message, name='update_message'),
    
    path('preview/<uuid:page_id>/', views.preview_page, name='preview_page'),
]