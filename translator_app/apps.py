from django.apps import AppConfig
import os
import logging
import sys

class TranslatorAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'translator_app'
    
    def ready(self):
        """
        Configuración inicial cuando se inicia la aplicación
        """
        if 'runserver' in sys.argv:
            # Configurar logging
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.StreamHandler(sys.stdout)
                ]
            )
            
            # Configurar Tesseract si es necesario
            try:
                from django.conf import settings
                import pytesseract
                
                # Configurar ruta de Tesseract si está definida
                if hasattr(settings, 'TESSERACT_CMD') and settings.TESSERACT_CMD:
                    pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
                    logging.info(f"Tesseract configurado en: {settings.TESSERACT_CMD}")
            except Exception as e:
                logging.warning(f"No se pudo configurar Tesseract: {str(e)}")
            
            # Crear directorios de medios si no existen
            media_root = getattr(settings, 'MEDIA_ROOT', 'media')
            uploads_dir = os.path.join(media_root, 'uploads')
            results_dir = os.path.join(media_root, 'results')
            
            os.makedirs(uploads_dir, exist_ok=True)
            os.makedirs(results_dir, exist_ok=True)
            logging.info(f"Directorios de medios creados en: {media_root}")