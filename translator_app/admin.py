from django.contrib import admin
from .models import MangaPage

@admin.register(MangaPage)
class MangaPageAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'source_language', 'target_language', 'status', 'created_at')
    list_filter = ('status', 'source_language', 'target_language', 'created_at')
    search_fields = ('title',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Información Básica', {
            'fields': ('title', 'original_image', 'translated_image')
        }),
        ('Idiomas', {
            'fields': ('source_language', 'target_language')
        }),
        ('Estado', {
            'fields': ('status',)
        }),
        ('Datos de traducción', {
            'fields': ('detected_text', 'translated_text'),
            'classes': ('collapse',)
        }),
        ('Metadatos', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )