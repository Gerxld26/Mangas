import logging
import re
import os
from openai import OpenAI
from django.conf import settings
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class DeepseekAPIService:
    def __init__(self):
        self.api_key = os.environ.get("OPENROUTER_API_KEY")
        self.base_url = os.environ.get("OPENROUTER_BASE_URL")
        self.default_model = os.environ.get("DEFAULT_MODEL", "anthropic/claude-3-haiku")
        self.default_temperature = float(os.environ.get("DEFAULT_TEMPERATURE", 0.2))
        self.default_max_tokens = int(os.environ.get("DEFAULT_MAX_TOKENS", 200))
        
        try:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            logger.info(f"Cliente OpenAI inicializado con OpenRouter, API KEY: {self.api_key[:10] if self.api_key else 'No disponible'}...")
        except Exception as e:
            logger.error(f"Error al inicializar cliente OpenAI: {str(e)}")
            self.client = None
    
    def clean_ocr_text(self, text):
        if not text:
            return ""
        
        # Eliminar artefactos específicos
        text = re.sub(r'^sa\s*\d+\s*wa\s*\d+\s*', '', text, flags=re.IGNORECASE)
        
        # Corregir errores comunes de OCR
        text = text.replace('thcsc', 'these')
        text = text.replace('bchind', 'behind')
        text = text.replace('Thcy', 'They')
        text = text.replace('andl', 'and')
        text = text.replace('scaredl', 'scared')
        text = text.replace('Ihat s', "That's")
        text = text.replace('inl', 'in')
        text = text.replace('idopting', 'adopting')
        text = text.replace('Lincla Bl 7ir', 'Linda Blair')
        
        # Limpiar texto general
        text = re.sub(r'[^\w\s\.\,\!\?\-]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    def clean_translation(self, text):
        if not text:
            return ""
            
        patterns = [
            r"^La traducción del texto coreano '[^']+' al español(?: sería)?:\s*",
            r"^La traducción al español de '[^']+' es:\s*",
            r"^La traducción al español(?: sería)?:\s*",
            r"^Traducción al español:\s*",
            r"^Aquí está la traducción al español:\s*",
            r"^Gwenchanheusimyeon\s*",
            r"^[\"']|[\"']$",
            r"^\n+",
            r"^Lo siento, pero .*$",
        ]
        
        cleaned_text = text
        for pattern in patterns:
            cleaned_text = re.sub(pattern, "", cleaned_text, flags=re.MULTILINE)
        
        cleaned_text = cleaned_text.strip()
        
        if cleaned_text.startswith('"') and cleaned_text.endswith('"'):
            cleaned_text = cleaned_text[1:-1]
        
        if not cleaned_text and text:
            return text
            
        return cleaned_text
    
    def preserve_proper_names(self, text):
        name_pattern = r'- ([A-Z][a-z]+ [A-Z][a-z]+)'
        matches = re.findall(name_pattern, text)
        return matches[0] if matches else None
    
    def translate_text(self, text, source_lang='auto', target_lang='es'):
        if not text:
            logger.warning("Se intentó traducir texto vacío")
            return {'translated_text': ''}
        
        if not self.client:
            logger.error("Cliente OpenAI no inicializado correctamente")
            return {'translated_text': f"Error: No se pudo traducir '{text}'"}
        
        try:
            text = self.clean_ocr_text(text)
            
            prompt = f"""Traduce literalmente este texto al español, conservando:
    - La estructura original de las frases
    - Todos los matices emocionales
    - Puntuación y estilo
    - Nombres propios

    Texto original: "{text}"

    Traducción:"""
            
            logger.info(f"Enviando solicitud de traducción para: '{text}'")
            
            response = self.client.chat.completions.create(
                model=self.default_model,
                messages=[
                    {
                        "role": "system", 
                        "content": "Eres un traductor preciso que mantiene la estructura y emoción del texto original."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=self.default_max_tokens
            )
            
            if response and response.choices and len(response.choices) > 0:
                translated_text = response.choices[0].message.content
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
        text_items = [(i, region.get('text', '')) for i, region in enumerate(text_regions) if region.get('text')]
        
        if not text_items:
            logger.warning("No hay textos para traducir")
            return text_regions
        
        special_cases = {
            "!?": "¡¿?!",
            "!": "¡!",
            "?": "¿?",
            ".": ".",
            "...": "...",
            "'": "'",
            "": ""
        }
        
        context = " ".join([region.get('text', '') for region in text_regions if region.get('text')])
        
        translated_regions = []
        for i, region in enumerate(text_regions):
            region_copy = region.copy()
            text = region.get('text', '')
            
            if text:
                if text in special_cases:
                    region_copy['translated_text'] = special_cases[text]
                    logger.info(f"Caso especial para '{text}': '{special_cases[text]}'")
                else:
                    try:
                        if i > 0 and i < len(text_regions) - 1:
                            prev_text = text_regions[i-1].get('translated_text', '')
                            context_prompt = f"Contexto previo: {prev_text}\n\nTexto a traducir: {text}"
                            translation_result = self.translate_text(context_prompt, source_lang, target_lang)
                        else:
                            translation_result = self.translate_text(text, source_lang, target_lang)
                        
                        region_copy['translated_text'] = translation_result.get('translated_text', '')
                    except Exception as e:
                        logger.error(f"Error al traducir región {i}: {str(e)}")
                        region_copy['translated_text'] = text
            else:
                region_copy['translated_text'] = ''
            
            translated_regions.append(region_copy)
        
        translated_regions = self.post_process_translations(translated_regions)
        
        logger.info(f"Se procesaron {len(translated_regions)} regiones de texto")
        return translated_regions
        
    def post_process_translations(self, regions):
        for i in range(len(regions)):
            if 'translated_text' in regions[i]:
                text = regions[i]['translated_text']
                
                text = text.replace("bares", "barrotes")
                
                text = text.replace(" ,", ",").replace(" .", ".")
                
                text = re.sub(r'(\s*)¿', r' ¿', text)
                text = re.sub(r'(\s*)¡', r' ¡', text)
                
                if "- " in regions[i].get('text', '') and "- " not in text:
                    original_name = re.search(r'- ([A-Za-z ]+)$', regions[i]['text'])
                    if original_name:
                        text = re.sub(r'(?:- )?([a-zA-Z]+)$', f"- {original_name.group(1)}", text)
                
                regions[i]['translated_text'] = text
                
        return regions