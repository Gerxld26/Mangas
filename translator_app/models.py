from django.db import models
import os
import uuid

def get_upload_path(instance, filename):
    """Genera un path único para guardar la imagen subida"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('uploads', filename)

def get_result_path(instance, filename):
    """Genera un path único para guardar la imagen traducida"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('results', filename)

class MangaPage(models.Model):
    """Modelo para almacenar la página de manga y su traducción"""
    
    SOURCE_LANGUAGE_CHOICES = [
        ('ja', 'Japonés'),
        ('ko', 'Coreano'),
        ('zh', 'Chino'),
        ('auto', 'Detectar automáticamente'),
    ]
    
    TARGET_LANGUAGE_CHOICES = [
        ('es', 'Español'),
        ('en', 'Inglés'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('processing', 'Procesando'),
        ('completed', 'Completado'),
        ('failed', 'Fallido'),
    ]
    
    title = models.CharField(max_length=255, blank=True, verbose_name="Título")
    original_image = models.ImageField(upload_to=get_upload_path, verbose_name="Imagen Original")
    translated_image = models.ImageField(upload_to=get_result_path, blank=True, null=True, verbose_name="Imagen Traducida")
    
    source_language = models.CharField(
        max_length=10, 
        choices=SOURCE_LANGUAGE_CHOICES,
        default='auto',
        verbose_name="Idioma de origen"
    )
    
    target_language = models.CharField(
        max_length=10, 
        choices=TARGET_LANGUAGE_CHOICES,
        default='es',
        verbose_name="Idioma de destino"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Estado"
    )
    
    detected_text = models.JSONField(blank=True, null=True, verbose_name="Texto detectado")
    translated_text = models.JSONField(blank=True, null=True, verbose_name="Texto traducido")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Última actualización")
    
    def __str__(self):
        return f"{self.title or 'Sin título'} - {self.get_status_display()}"
    
    class Meta:
        verbose_name = "Página de Manga"
        verbose_name_plural = "Páginas de Manga"
        ordering = ['-created_at']