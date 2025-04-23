import logging
import json
import re
import os
from openai import OpenAI
from django.conf import settings
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

logger = logging.getLogger(__name__)

class DeepseekAPIService:
    """Servicio para interactuar con la API de OpenRouter"""
    
    def __init__(self):
        # Obtener credenciales desde variables de entorno
        self.api_key = os.environ.get("OPENROUTER_API_KEY")
        self.base_url = os.environ.get("OPENROUTER_BASE_URL")
        self.default_model = os.environ.get("DEFAULT_MODEL", "anthropic/claude-3-haiku")
        self.default_temperature = float(os.environ.get("DEFAULT_TEMPERATURE", 0.2))
        self.default_max_tokens = int(os.environ.get("DEFAULT_MAX_TOKENS", 200))
        
        try:
            # Inicializar cliente OpenAI con OpenRouter
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            logger.info(f"Cliente OpenAI inicializado con OpenRouter, API KEY: {self.api_key[:10] if self.api_key else 'No disponible'}...")
        except Exception as e:
            logger.error(f"Error al inicializar cliente OpenAI: {str(e)}")
            self.client = None
    
    def clean_translation(self, text):
        """
        Limpia el texto traducido para eliminar prefijos y otros textos innecesarios
        
        Args:
            text (str): Texto traducido a limpiar
            
        Returns:
            str: Texto limpio
        """
        if not text:
            return ""
            
        # Patrones a eliminar
        patterns = [
            # Patrones específicos que has observado en las traducciones
            r"^La traducción del texto coreano '[^']+' al español(?: sería)?:\s*",
            r"^La traducción al español de '[^']+' es:\s*",
            r"^La traducción al español(?: sería)?:\s*",
            r"^Traducción al español:\s*",
            r"^Aquí está la traducción al español:\s*",
            r"^Gwenchanheusimyeon\s*",
            # Eliminar comillas y apóstrofes extra
            r"^[\"']|[\"']$",
            # Eliminar líneas en blanco al principio
            r"^\n+",
            # Mensajes de error o explicaciones
            r"^Lo siento, pero .*$",
        ]
        
        # Aplicar cada patrón
        cleaned_text = text
        for pattern in patterns:
            cleaned_text = re.sub(pattern, "", cleaned_text, flags=re.MULTILINE)
        
        # Eliminar líneas en blanco al principio y final
        cleaned_text = cleaned_text.strip()
        
        # En caso de que queden comillas
        if cleaned_text.startswith('"') and cleaned_text.endswith('"'):
            cleaned_text = cleaned_text[1:-1]
        
        # Si no hay texto después de la limpieza, devolver el texto original
        if not cleaned_text and text:
            return text
            
        return cleaned_text
    
    def translate_text(self, text, source_lang='auto', target_lang='es'):
        """
        Traduce texto utilizando la API de OpenRouter
        
        Args:
            text (str): Texto a traducir
            source_lang (str): Código de idioma de origen
            target_lang (str): Código de idioma de destino
            
        Returns:
            dict: Respuesta con la traducción
        """
        if not text:
            logger.warning("Se intentó traducir texto vacío")
            return {'translated_text': ''}
        
        if not self.client:
            logger.error("Cliente OpenAI no inicializado correctamente")
            return {'translated_text': f"Error: No se pudo traducir '{text}'"}
        
        try:
            # Crear prompt para la traducción - especificar que queremos SOLO la traducción
            prompt = f"""Traduce solo este texto del coreano al español sin agregar explicaciones ni comentarios:

"{text}"

Importante: Tu respuesta debe contener SOLO la traducción, sin frases introductorias como "La traducción es..." ni comillas."""
            
            # Realizar llamada a la API a través del cliente OpenAI
            logger.info(f"Enviando solicitud de traducción para: '{text}'")
            
            response = self.client.chat.completions.create(
                model=self.default_model,
                messages=[
                    {"role": "system", "content": "Eres un traductor preciso del coreano al español. Responde SOLO con la traducción, sin texto adicional."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.default_temperature,
                max_tokens=self.default_max_tokens
            )
            
            # Procesar respuesta
            if response and response.choices and len(response.choices) > 0:
                translated_text = response.choices[0].message.content
                
                # Limpiar y mejorar la traducción
                cleaned_text = self.clean_translation(translated_text)
                
                logger.info(f"Traducción: '{translated_text}' → Limpia: '{cleaned_text}'")
                return {
                    'translated_text': cleaned_text,
                    'source_language': source_lang,
                    'target_language': target_lang
                }
            else:
                logger.warning("Respuesta sin texto traducido")
                return {'translated_text': f"Error: No se pudo traducir '{text}'"}
                
        except Exception as e:
            logger.error(f"Error al traducir: {str(e)}")
            return {'translated_text': f"Error: {str(e)}"}
    
    def translate_manga_text(self, text_regions, source_lang='auto', target_lang='es'):
        """
        Traduce múltiples regiones de texto de un manga
        
        Args:
            text_regions (list): Lista de diccionarios con texto y coordenadas
            source_lang (str): Código de idioma de origen
            target_lang (str): Código de idioma de destino
            
        Returns:
            list: Lista de diccionarios con el texto traducido y las coordenadas originales
        """
        # Extraer texto de las regiones
        text_items = [(i, region.get('text', '')) for i, region in enumerate(text_regions) if region.get('text')]
        
        if not text_items:
            logger.warning("No hay textos para traducir")
            return text_regions
        
        # Caso especial para signos de puntuación
        special_cases = {
            "!?": "¡¿?!",
            "!": "¡!",
            "?": "¿?",
            ".": ".",
            "...": "...",
            "'": "'",
            "": ""
        }
        
        # Traducir cada región
        translated_regions = []
        for i, region in enumerate(text_regions):
            region_copy = region.copy()
            text = region.get('text', '')
            
            # Solo traducir si hay texto
            if text:
                # Caso especial para puntuación
                if text in special_cases:
                    region_copy['translated_text'] = special_cases[text]
                    logger.info(f"Caso especial para '{text}': '{special_cases[text]}'")
                else:
                    try:
                        # Intentar traducir con la API
                        translation_result = self.translate_text(text, source_lang, target_lang)
                        region_copy['translated_text'] = translation_result.get('translated_text', '')
                    except Exception as e:
                        logger.error(f"Error al traducir región {i}: {str(e)}")
                        region_copy['translated_text'] = text
            else:
                region_copy['translated_text'] = ''
            
            translated_regions.append(region_copy)
        
        logger.info(f"Se procesaron {len(translated_regions)} regiones de texto")
        return translated_regions