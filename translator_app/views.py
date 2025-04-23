import os
import json
import logging
import numpy as np
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import JsonResponse
from django.conf import settings
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView, ListView, DetailView, CreateView
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile

from .models import MangaPage
from .forms import MangaTranslationForm
from .services.ocr_service import OCRService
from .services.deepseek_api import DeepseekAPIService
from .services.image_processor import ImageProcessor

logger = logging.getLogger(__name__)

# Función de ayuda para convertir tipos NumPy a tipos nativos de Python
def numpy_to_python_types(obj):
    """Convierte cualquier tipo NumPy en tipos nativos de Python para serialización JSON"""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, list):
        return [numpy_to_python_types(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: numpy_to_python_types(value) for key, value in obj.items()}
    else:
        return obj

# Vistas basadas en clases
class HomeView(TemplateView):
    """Vista de la página de inicio"""
    template_name = 'translator_app/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = MangaTranslationForm()
        # Obtener algunas traducciones recientes para mostrar como ejemplos
        context['recent_translations'] = MangaPage.objects.filter(
            status='completed',
            translated_image__isnull=False
        ).order_by('-created_at')[:6]
        return context
    
class MangaTranslationEditorView(DetailView):
    """Vista para editar una traducción"""
    model = MangaPage
    template_name = 'translator_app/translation_editor.html'
    context_object_name = 'translation'

class MangaTranslationListView(ListView):
    """Vista de lista de todas las traducciones"""
    model = MangaPage
    template_name = 'translator_app/translation_list.html'
    context_object_name = 'translations'
    paginate_by = 12
    
    def get_queryset(self):
        return MangaPage.objects.all().order_by('-created_at')

class MangaTranslationDetailView(DetailView):
    """Vista detallada de una traducción"""
    model = MangaPage
    template_name = 'translator_app/translation_detail.html'
    context_object_name = 'translation'

class MangaTranslationCreateView(CreateView):
    """Vista para crear una nueva traducción"""
    model = MangaPage
    form_class = MangaTranslationForm
    template_name = 'translator_app/translation_form.html'
    
    def form_valid(self, form):
        # Guardar la instancia del modelo
        self.object = form.save(commit=False)
        self.object.status = 'pending'
        self.object.save()
        
        # Iniciar el proceso de traducción
        try:
            # Procesamiento asíncrono (en un entorno real, esto debería hacerse con celery o similar)
            process_manga_translation(self.object.id)
            messages.success(self.request, "¡Imagen subida con éxito! La traducción está en proceso.")
        except Exception as e:
            logger.error(f"Error al iniciar el proceso de traducción: {str(e)}")
            self.object.status = 'failed'
            self.object.save()
            messages.error(self.request, f"Error al procesar la traducción: {str(e)}")
        
        return redirect(reverse('translation_detail', kwargs={'pk': self.object.id}))

# Funciones auxiliares
def process_manga_translation(manga_page_id):
    """
    Procesa la traducción de una página de manga
    
    Args:
        manga_page_id (int): ID de la página de manga a procesar
    """
    # Obtener la página de manga
    manga_page = get_object_or_404(MangaPage, id=manga_page_id)
    
    # Actualizar estado a 'procesando'
    manga_page.status = 'processing'
    manga_page.save()
    
    try:
        # 1. Obtener ruta a la imagen original
        image_path = manga_page.original_image.path
        
        # 2. Detectar texto en la imagen
        ocr_service = OCRService()
        text_regions = ocr_service.detect_text_regions(
            image_path, 
            manga_page.source_language
        )
        
        # Convertir a tipos nativos de Python para serialización JSON
        text_regions = numpy_to_python_types(text_regions)
        
        # Verificar que sea serializable antes de guardar
        try:
            json_text = json.dumps(text_regions)
            # Guardar texto detectado
            manga_page.detected_text = text_regions
            manga_page.save()
        except TypeError as e:
            logger.error(f"Error al serializar texto detectado: {str(e)}")
            # Si no es serializable, intentar convertir manualmente
            serializable_regions = []
            for region in text_regions:
                clean_region = {
                    'id': int(region.get('id', 0)),
                    'text': str(region.get('text', '')),
                    'confidence': float(region.get('confidence', 0.0)),
                    'bbox': [[int(x), int(y)] for x, y in region.get('bbox', [])],
                    'bbox_simple': [int(x) for x in region.get('bbox_simple', [0, 0, 0, 0])],
                    'language_detected': str(region.get('language_detected', 'unknown')),
                }
                serializable_regions.append(clean_region)
            
            manga_page.detected_text = serializable_regions
            manga_page.save()
            text_regions = serializable_regions
        
        # 3. Traducir el texto detectado
        if text_regions:
            deepseek_service = DeepseekAPIService()
            translated_regions = deepseek_service.translate_manga_text(
                text_regions,
                manga_page.source_language,
                manga_page.target_language
            )
            
            # Convertir a tipos nativos para serialización
            translated_regions = numpy_to_python_types(translated_regions)
            
            # Guardar texto traducido
            manga_page.translated_text = translated_regions
            manga_page.save()
            
            # 4. Procesar la imagen
            image_processor = ImageProcessor()
            output_path = image_processor.process_manga_image(
                image_path,
                translated_regions,
                manga_page.target_language
            )
            
            # 5. Guardar la imagen traducida en el modelo
            with open(output_path, 'rb') as f:
                manga_page.translated_image.save(
                    os.path.basename(output_path),
                    ContentFile(f.read()),
                    save=True
                )
            
            # Actualizar estado a 'completado'
            manga_page.status = 'completed'
            manga_page.save()
            
            # Eliminar el archivo temporal si existe
            if os.path.exists(output_path):
                os.remove(output_path)
        else:
            # No se detectó texto
            logger.warning("No se detectó texto en la imagen")
            manga_page.status = 'failed'
            manga_page.save()
            raise ValueError("No se detectó texto en la imagen")
    
    except Exception as e:
        logger.error(f"Error al procesar la traducción: {str(e)}")
        manga_page.status = 'failed'
        manga_page.save()
        raise

# API endpoints
@csrf_exempt
@require_POST
def translate_page(request):
    """Endpoint de API para traducir una página de manga"""
    try:
        # Verificar si hay un archivo en la solicitud
        if 'image' not in request.FILES:
            return JsonResponse({'error': 'No se proporcionó ninguna imagen'}, status=400)
        
        # Crear un formulario con los datos de la solicitud
        form = MangaTranslationForm(request.POST, request.FILES)
        
        if form.is_valid():
            # Guardar el modelo
            manga_page = form.save(commit=False)
            manga_page.status = 'pending'
            manga_page.save()
            
            # Iniciar el proceso de traducción
            try:
                process_manga_translation(manga_page.id)
                return JsonResponse({
                    'id': manga_page.id,
                    'status': manga_page.status,
                    'original_image': manga_page.original_image.url,
                    'translated_image': manga_page.translated_image.url if manga_page.translated_image else None,
                })
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=500)
        else:
            # Devolver errores de validación
            return JsonResponse({'errors': form.errors}, status=400)
    
    except Exception as e:
        logger.error(f"Error en el endpoint de traducción: {str(e)}")
        return JsonResponse({'error': f"Error interno del servidor: {str(e)}"}, status=500)

def get_translation_status(request, pk):
    """Endpoint para verificar el estado de una traducción"""
    try:
        manga_page = get_object_or_404(MangaPage, id=pk)
        data = {
            'id': manga_page.id,
            'status': manga_page.status,
            'created_at': manga_page.created_at.isoformat(),
            'updated_at': manga_page.updated_at.isoformat(),
        }
        
        # Incluir URLs de imágenes si están disponibles
        if manga_page.original_image:
            data['original_image'] = manga_page.original_image.url
        
        if manga_page.translated_image:
            data['translated_image'] = manga_page.translated_image.url
        
        return JsonResponse(data)
    
    except Exception as e:
        logger.error(f"Error al obtener estado de traducción: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
    

@csrf_exempt
@require_POST
def update_translation_regions(request, pk):
    """Endpoint para actualizar las regiones de texto de una traducción"""
    try:
        manga_page = get_object_or_404(MangaPage, id=pk)
        
        data = json.loads(request.body)
        regions = data.get('regions', [])
        
        # Actualizar regiones de texto
        manga_page.translated_text = regions
        manga_page.save()
        
        return JsonResponse({'success': True})
    except Exception as e:
        logger.error(f"Error al actualizar regiones: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})

@csrf_exempt
@require_POST
def regenerate_translation_image(request, pk):
    """Endpoint para regenerar la imagen traducida"""
    try:
        manga_page = get_object_or_404(MangaPage, id=pk)
        
        data = json.loads(request.body)
        regions = data.get('regions', [])
        
        # Actualizar regiones de texto
        manga_page.translated_text = regions
        manga_page.save()
        
        # Procesar la imagen
        image_processor = ImageProcessor()
        output_path = image_processor.process_manga_image(
            manga_page.original_image.path,
            regions,
            manga_page.target_language
        )
        
        # Guardar la imagen traducida en el modelo
        with open(output_path, 'rb') as f:
            manga_page.translated_image.save(
                os.path.basename(output_path),
                ContentFile(f.read()),
                save=True
            )
        
        # Eliminar el archivo temporal si existe
        if os.path.exists(output_path):
            os.remove(output_path)
        
        return JsonResponse({'success': True})
    except Exception as e:
        logger.error(f"Error al regenerar imagen: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})
    
@csrf_exempt
@require_POST
def retranslate_all_texts(request, pk):
    """Endpoint para volver a traducir todos los textos de una traducción"""
    try:
        manga_page = get_object_or_404(MangaPage, id=pk)
        
        # Obtener servicio de traducción
        deepseek_service = DeepseekAPIService()
        
        # Obtener regiones traducidas
        regions = manga_page.translated_text
        
        if not regions:
            return JsonResponse({'success': False, 'error': 'No hay textos para traducir'})
        
        # Volver a traducir cada texto
        for region in regions:
            if region.get('text'):
                # Traducir el texto original
                translation_result = deepseek_service.translate_text(
                    region['text'],
                    manga_page.source_language,
                    manga_page.target_language
                )
                region['translated_text'] = translation_result.get('translated_text', region['text'])
        
        # Guardar las regiones actualizadas
        manga_page.translated_text = regions
        manga_page.save()
        
        # Regenerar la imagen
        image_processor = ImageProcessor()
        output_path = image_processor.process_manga_image(
            manga_page.original_image.path,
            regions,
            manga_page.target_language
        )
        
        # Guardar la imagen traducida en el modelo
        with open(output_path, 'rb') as f:
            manga_page.translated_image.save(
                os.path.basename(output_path),
                ContentFile(f.read()),
                save=True
            )
        
        return JsonResponse({'success': True})
    except Exception as e:
        logger.error(f"Error al retraducir textos: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})
    
@csrf_exempt
@require_POST
def translate_text(request):
    """Endpoint para traducir un texto individual"""
    try:
        data = json.loads(request.body)
        text = data.get('text', '')
        source_lang = data.get('source_language', 'auto')
        target_lang = data.get('target_language', 'es')
        
        if not text:
            return JsonResponse({'error': 'No se proporcionó texto para traducir'})
        
        # Traducir texto
        deepseek_service = DeepseekAPIService()
        result = deepseek_service.translate_text(text, source_lang, target_lang)
        
        return JsonResponse(result)
    except Exception as e:
        logger.error(f"Error al traducir texto: {str(e)}")
        return JsonResponse({'error': str(e)})