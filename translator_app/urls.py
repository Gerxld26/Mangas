from django.urls import path
from . import views

urlpatterns = [
    # Páginas principales (existentes)
    path('', views.HomeView.as_view(), name='home'),
    path('translations/', views.MangaTranslationListView.as_view(), name='translation_list'),
    path('translations/<int:pk>/', views.MangaTranslationDetailView.as_view(), name='translation_detail'),
    path('translate/', views.MangaTranslationCreateView.as_view(), name='translation_create'),
    
    # Nueva ruta para el editor
    path('translations/<int:pk>/edit/', views.MangaTranslationEditorView.as_view(), name='translation_editor'),
    
    # API endpoints (existentes)
    path('api/translate/', views.translate_page, name='api_translate'),
    path('api/translations/<int:pk>/status/', views.get_translation_status, name='api_translation_status'),
    
    # Nuevos endpoints API para el editor
    path('api/translations/<int:pk>/update_regions/', views.update_translation_regions, name='api_update_regions'),
    path('api/translations/<int:pk>/regenerate/', views.regenerate_translation_image, name='api_regenerate_image'),
    path('api/translate_text/', views.translate_text, name='api_translate_text'),
]