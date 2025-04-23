import os
import easyocr
import cv2
import numpy as np
import logging
import json
from pathlib import Path
from django.conf import settings

logger = logging.getLogger(__name__)

class OCRService:
    def __init__(self):
        self.readers = {}
    
    def get_reader(self, language):
        if language not in self.readers:
            lang_map = {
                'ja': ['ja', 'en'],
                'ko': ['ko', 'en'],
                'zh': ['ch_sim', 'en'],
                'auto': ['ko', 'en'],
            }
            
            lang_list = lang_map.get(language, ['en', 'ko'])
            
            try:
                self.readers[language] = easyocr.Reader(
                    lang_list,
                    gpu=False,
                    download_enabled=True,
                )
                logger.info(f"Lector OCR inicializado para {language} con lang_list={lang_list}")
            except Exception as e:
                logger.error(f"Error al inicializar EasyOCR para {language}: {str(e)}")
                raise
                
        return self.readers[language]
    
    def _numpy_to_native(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, list):
            return [self._numpy_to_native(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: self._numpy_to_native(value) for key, value in obj.items()}
        else:
            return obj
    
    def detect_text_regions(self, image_path, language='auto'):
        try:
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"No se pudo leer la imagen en {image_path}")
            
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (5, 5), 0)
            
            debug_dir = os.path.dirname(os.path.dirname(image_path)) + '/results'
            os.makedirs(debug_dir, exist_ok=True)
            
            reader = self.get_reader(language)
            
            # Usar parámetros seguros que sabemos que funcionan
            results = reader.readtext(
                image, 
                detail=1,
                paragraph=False,  # Volvemos a False para evitar errores
                rotation_info=[0],
                width_ths=0.7,
                height_ths=0.7,
                contrast_ths=0.1,
                text_threshold=0.5,
            )
            
            text_regions = []
            for i, (bbox, text, prob) in enumerate(results):
                if prob > 0.3:
                    bbox_native = [[int(x), int(y)] for x, y in bbox]
                    
                    x_min = min(point[0] for point in bbox_native)
                    y_min = min(point[1] for point in bbox_native)
                    x_max = max(point[0] for point in bbox_native)
                    y_max = max(point[1] for point in bbox_native)
                    
                    width = x_max - x_min
                    height = y_max - y_min
                    
                    padding = 5
                    x_min = max(0, x_min - padding)
                    y_min = max(0, y_min - padding)
                    width = min(image.shape[1] - x_min, width + 2 * padding)
                    height = min(image.shape[0] - y_min, height + 2 * padding)
                    
                    region = {
                        'id': i,
                        'text': str(text),
                        'confidence': float(prob) * 100,
                        'bbox': bbox_native,
                        'bbox_simple': [int(x_min), int(y_min), int(width), int(height)],
                        'language_detected': str(language),
                    }
                    
                    try:
                        json.dumps(region)
                        text_regions.append(region)
                    except TypeError as e:
                        region = self._numpy_to_native(region)
                        text_regions.append(region)
            
            # Ordenar regiones por posición Y
            sorted_regions = sorted(text_regions, key=lambda r: r['bbox_simple'][1])
            
            # Aplicar nuestro propio algoritmo de agrupación en párrafos
            merged_regions = self._group_into_paragraphs(sorted_regions)
            
            # Convertir a tipos nativos para serialización
            merged_regions = self._numpy_to_native(merged_regions)
            
            try:
                json.dumps(merged_regions)
            except TypeError as e:
                logger.error(f"Error al serializar regiones: {e}")
                raise ValueError("No se pudieron serializar las regiones de texto a JSON")
            
            logger.info(f"Se detectaron {len(text_regions)} regiones de texto y se combinaron en {len(merged_regions)}")
            return merged_regions
            
        except Exception as e:
            logger.error(f"Error al detectar texto en la imagen: {str(e)}")
            raise
    
    def _group_into_paragraphs(self, regions, distance_threshold=50):
        """Agrupa regiones de texto en párrafos basados en proximidad y posición"""
        if not regions:
            return []
        
        paragraphs = []
        current_group = [regions[0]]
        
        for i in range(1, len(regions)):
            current = regions[i]
            prev = current_group[-1]
            
            # Extraer coordenadas
            curr_x, curr_y, curr_w, curr_h = current['bbox_simple']
            prev_x, prev_y, prev_w, prev_h = prev['bbox_simple']
            
            # Calcular distancia vertical y solapamiento horizontal
            vertical_distance = abs(curr_y - (prev_y + prev_h))
            horizontal_overlap = max(0, min(prev_x + prev_w, curr_x + curr_w) - max(prev_x, curr_x))
            
            # Verificar si deben combinarse
            should_combine = False
            
            # Si están cerca verticalmente y tienen algún solapamiento horizontal
            if vertical_distance < distance_threshold and horizontal_overlap > 0:
                should_combine = True
            
            # Verificar conectores lingüísticos (para casos como "porque", "y", etc.)
            curr_text = current.get('text', '').strip().lower()
            if curr_text.startswith(('porque', 'ya que', 'por', 'aunque', 'pero', 'y ', 'si', 'cuando')):
                should_combine = True
            
            if should_combine:
                current_group.append(current)
            else:
                # Finalizar grupo actual y comenzar uno nuevo
                paragraph = self._combine_paragraph(current_group)
                paragraphs.append(paragraph)
                current_group = [current]
        
        # Añadir el último grupo
        if current_group:
            paragraph = self._combine_paragraph(current_group)
            paragraphs.append(paragraph)
        
        return paragraphs
    
    def _combine_paragraph(self, regions):
        """Combina múltiples regiones en un solo párrafo"""
        if len(regions) == 1:
            return regions[0]
        
        # Copiar la primera región como base
        combined = regions[0].copy()
        
        # Combinar textos de todas las regiones
        texts = [r.get('text', '') for r in regions]
        combined_text = ' '.join(texts)
        combined['text'] = combined_text
        
        # Calcular bounding box combinado
        min_x = min(r['bbox_simple'][0] for r in regions)
        min_y = min(r['bbox_simple'][1] for r in regions)
        max_x = max(r['bbox_simple'][0] + r['bbox_simple'][2] for r in regions)
        max_y = max(r['bbox_simple'][1] + r['bbox_simple'][3] for r in regions)
        
        width = max_x - min_x
        height = max_y - min_y
        
        # Actualizar bbox simple
        combined['bbox_simple'] = [int(min_x), int(min_y), int(width), int(height)]
        
        # Actualizar id para reflejar combinación
        combined['id'] = f"{regions[0]['id']}-{regions[-1]['id']}"
        
        # Actualizar confianza (promedio)
        confidences = [r.get('confidence', 0) for r in regions]
        combined['confidence'] = sum(confidences) / len(confidences)
        
        return combined