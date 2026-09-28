# tavern/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.tavern_home, name='tavern_home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('chapter/create/', views.create_chapter, name='create_chapter'),
    path('chapter/<int:chapter_id>/chat/', views.chat_stream_api, name='chat_stream_api'),
    path('chapter/<int:chapter_id>/delete/', views.delete_chapter, name='delete_chapter'),
    path('chapter/<int:chapter_id>/memory/', views.update_memory_api, name='update_memory_api'),
    path('global_memory/update/', views.update_global_memory_api, name='update_global_memory_api'),
    path('lora/create/', views.create_lora_api, name='create_lora_api'),
    ]