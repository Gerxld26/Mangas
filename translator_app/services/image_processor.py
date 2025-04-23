import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import logging
from pathlib import Path
import tempfile

logger = logging.getLogger(__name__)

class ImageProcessor:
    def __init__(self):
        self.fonts = {}
        self._load_fonts()
    
    def remove_original_text(self, image_path, text_regions):
        try:
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"No se pudo leer la imagen en {image_path}")
            
            mask = np.zeros(image.shape[:2], dtype=np.uint8)
            
            for region in text_regions:
                if 'bbox' in region:
                    pts = []
                    for point in region['bbox']:
                        if isinstance(point, list) and len(point) == 2:
                            pts.append([int(point[0]), int(point[1])])
                    
                    if pts:
                        pts = np.array(pts, np.int32)
                        pts = pts.reshape((-1, 1, 2))
                        cv2.fillPoly(mask, [pts], 255)
                
                elif 'bbox_simple' in region:
                    bbox = region['bbox_simple']
                    if len(bbox) == 4:
                        x, y, w, h = [int(val) for val in bbox]
                        padding = 5
                        cv2.rectangle(mask, (x-padding, y-padding), (x + w + padding, y + h + padding), 255, -1)
            
            inpaint_radius = 10
            image_without_text = cv2.inpaint(image, mask, inpaint_radius, cv2.INPAINT_TELEA)
            
            return image_without_text
            
        except Exception as e:
            logger.error(f"Error al eliminar texto original: {str(e)}")
            return cv2.imread(image_path)
    
    def merge_close_regions(self, text_regions, distance_threshold=50):
        if not text_regions:
            return []
            
        sorted_regions = sorted(text_regions, key=lambda r: r.get('bbox_simple', [0, 0, 0, 0])[1])
        
        merged_regions = []
        current_group = [sorted_regions[0]]
        
        for i in range(1, len(sorted_regions)):
            current_region = sorted_regions[i]
            prev_region = current_group[-1]
            
            if 'bbox_simple' in current_region and 'bbox_simple' in prev_region:
                curr_x, curr_y, curr_w, curr_h = current_region['bbox_simple']
                prev_x, prev_y, prev_w, prev_h = prev_region['bbox_simple']
                
                vertical_distance = abs(curr_y - (prev_y + prev_h))
                horizontal_overlap = max(0, min(prev_x + prev_w, curr_x + curr_w) - max(prev_x, curr_x))
                
                prev_text = prev_region.get('translated_text', '').strip()
                curr_text = current_region.get('translated_text', '').strip()
                
                is_related = self._are_sentences_related(prev_text, curr_text)
                
                if (vertical_distance < distance_threshold and horizontal_overlap > 0) or is_related:
                    current_group.append(current_region)
                else:
                    if current_group:
                        merged_regions.append(self._combine_regions(current_group))
                    current_group = [current_region]
            else:
                if current_group:
                    merged_regions.append(self._combine_regions(current_group))
                current_group = [current_region]
        
        if current_group:
            merged_regions.append(self._combine_regions(current_group))
        
        return merged_regions
    
    def _are_sentences_related(self, sentence1, sentence2):
        if not sentence1 or not sentence2:
            return False
        
        ends_open = sentence1.endswith('...') or not any(sentence1.endswith(p) for p in '.!?;')
        
        starts_dependent = (sentence2[0].islower() if sentence2 else False)
        
        connectors = ['porque', 'por', 'ya que', 'debido', 'pues', 'si', 'cuando', 'y ', 'pero']
        has_connector = any(sentence2.lower().startswith(conn) for conn in connectors)
        
        is_short_phrase = len(sentence2.split()) <= 4
        
        no_verb_in_first = len(sentence1.split()) <= 3 and '.' not in sentence1
        
        if ends_open or starts_dependent or has_connector or (is_short_phrase and no_verb_in_first):
            return True
        
        return False
    
    def _combine_regions(self, regions):
        if not regions:
            return None
        
        if len(regions) == 1:
            return regions[0]
        
        combined = regions[0].copy()
        
        combined_text = " ".join([r.get('text', '') for r in regions if r.get('text')])
        combined_translated_text = " ".join([r.get('translated_text', '') for r in regions if r.get('translated_text')])
        
        combined['text'] = combined_text
        combined['translated_text'] = combined_translated_text
        
        min_x, min_y = float('inf'), float('inf')
        max_x, max_y = 0, 0
        
        for region in regions:
            if 'bbox_simple' in region:
                x, y, w, h = region['bbox_simple']
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x + w)
                max_y = max(max_y, y + h)
        
        combined['bbox_simple'] = [int(min_x), int(min_y), int(max_x - min_x), int(max_y - min_y)]
        
        return combined
    
    def _load_fonts(self):
        try:
            base_dir = Path(__file__).resolve().parent.parent
            fonts_dir = base_dir / 'static' / 'translator_app' / 'fonts'
            os.makedirs(fonts_dir, exist_ok=True)
            
            windows_fonts = {
                'es': 'C:\\Windows\\Fonts\\arial.ttf',
                'en': 'C:\\Windows\\Fonts\\arial.ttf',
                'ja': 'C:\\Windows\\Fonts\\msgothic.ttc',
                'ko': 'C:\\Windows\\Fonts\\malgun.ttf',
                'zh': 'C:\\Windows\\Fonts\\simsun.ttc',
            }
            
            linux_fonts = {
                'es': '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                'en': '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                'ja': '/usr/share/fonts/truetype/fonts-japanese-gothic.ttf',
                'ko': '/usr/share/fonts/truetype/nanum/NanumGothic.ttf',
                'zh': '/usr/share/fonts/truetype/arphic/uming.ttc',
            }
            
            for lang in ['es', 'en', 'ja', 'ko', 'zh']:
                win_font = windows_fonts.get(lang)
                if win_font and os.path.exists(win_font):
                    self.fonts[lang] = win_font
                    continue
                
                linux_font = linux_fonts.get(lang)
                if linux_font and os.path.exists(linux_font):
                    self.fonts[lang] = linux_font
                    continue
                
                self.fonts[lang] = None
            
            logger.info(f"Fuentes cargadas: {self.fonts}")
            
        except Exception as e:
            logger.error(f"Error al cargar fuentes: {str(e)}")
    
    def get_font(self, language, size=24):
        font_path = self.fonts.get(language, self.fonts.get('en'))
        
        if font_path and os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except Exception as e:
                logger.error(f"Error al cargar fuente {font_path}: {str(e)}")
        
        return ImageFont.load_default()
    
    def add_translated_text(self, image, text_regions, target_language='es'):
        try:
            image_copy = image.copy()
            pil_image = Image.fromarray(cv2.cvtColor(image_copy, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(pil_image)
            
            valid_regions = [r for r in text_regions if r.get('translated_text', '').strip()]
            
            if not valid_regions:
                logger.warning("No hay regiones válidas con texto traducido")
                height, width = image.shape[:2]
                error_font = self.get_font('es', 16)
                error_msg = "Error al procesar la imagen. Por favor, inténtelo de nuevo."
                
                draw.rectangle([width//4, height//4, 3*width//4, height//4 + 60], 
                              fill=(255, 255, 255), outline=(0, 0, 0))
                
                try:
                    text_bbox = draw.textbbox((0, 0), error_msg, font=error_font)
                    text_width = text_bbox[2] - text_bbox[0]
                except:
                    text_width = 300
                
                text_x = width//2 - text_width//2
                text_y = height//4 + 20
                
                draw.text((text_x, text_y), error_msg, fill=(0, 0, 0), font=error_font)
                
                result = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
                return result
            
            for region in valid_regions:
                translated_text = region.get('translated_text', '')
                
                if 'bbox_simple' in region:
                    x, y, width, height = [int(val) for val in region['bbox_simple']]
                elif 'bbox' in region:
                    points = region['bbox']
                    x_coords = [int(p[0]) for p in points]
                    y_coords = [int(p[1]) for p in points]
                    x = min(x_coords)
                    y = min(y_coords)
                    width = max(x_coords) - x
                    height = max(y_coords) - y
                else:
                    continue
                
                img_height, img_width = image.shape[:2]
                x = max(0, min(x, img_width - 1))
                y = max(0, min(y, img_height - 1))
                width = min(width, img_width - x)
                height = min(height, img_height - y)
                
                name_match = re.search(r'- ([A-Z][a-z]+ [A-Z][a-z]+)', translated_text)
                name_text = ""
                if name_match:
                    name_text = name_match.group(0)
                    translated_text = translated_text[:name_match.start()].strip()
                
                draw.rectangle([x, y, x+width, y+height], fill=(255, 255, 255), outline=(200, 200, 200))
                
                available_width = max(width - 10, 20)
                available_height = max(height - 10, 20)
                
                base_font_size = max(min(height // 3, width // 10), 12)
                font_size = base_font_size
                
                try:
                    font = self.get_font(target_language, font_size)
                except Exception as e:
                    logger.error(f"Error al cargar fuente: {str(e)}")
                    font = ImageFont.load_default()
                
                try:
                    lines = self._wrap_text_smart(translated_text, available_width, font)
                    
                    total_text_height = len(lines) * (font_size + 2)
                    if total_text_height > available_height and len(lines) > 1:
                        scale_factor = available_height / total_text_height
                        new_font_size = max(int(font_size * scale_factor), 10)
                        font = self.get_font(target_language, new_font_size)
                        font_size = new_font_size
                        lines = self._wrap_text_smart(translated_text, available_width, font)
                except Exception as e:
                    logger.error(f"Error en wrapping de texto: {str(e)}")
                    lines = [translated_text]
                
                line_height = font_size + 2
                total_text_height = len(lines) * line_height
                
                text_y = y + (height - total_text_height) // 2
                
                for line in lines:
                    try:
                        text_bbox = draw.textbbox((0, 0), line, font=font)
                        text_width = text_bbox[2] - text_bbox[0]
                    except:
                        try:
                            text_width = font.getsize(line)[0]
                        except:
                            text_width = len(line) * (font_size // 2)
                    
                    text_x = x + (width - text_width) // 2
                    
                    draw.text((text_x+1, text_y+1), line, fill=(200, 200, 200), font=font)
                    draw.text((text_x, text_y), line, fill=(0, 0, 0), font=font)
                    text_y += line_height
                
                if name_text:
                    try:
                        name_font_size = max(font_size - 2, 10)
                        name_font = self.get_font(target_language, name_font_size)
                        
                        try:
                            name_bbox = draw.textbbox((0, 0), name_text, font=name_font)
                            name_width = name_bbox[2] - name_bbox[0]
                        except:
                            try:
                                name_width = name_font.getsize(name_text)[0]
                            except:
                                name_width = len(name_text) * (name_font_size // 2)
                        
                        name_x = x + width - name_width - 5
                        name_y = y + height - name_font_size - 5
                        
                        draw.text((name_x, name_y), name_text, fill=(0, 0, 0), font=name_font)
                    except Exception as e:
                        logger.error(f"Error al añadir nombre: {str(e)}")
            
            result = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            return result
            
        except Exception as e:
            logger.error(f"Error al añadir texto traducido: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return image
    
    def _wrap_text_smart(self, text, max_width, font):
        import re
        
        if not text:
            return []
        
        # Intentar obtener medida de texto
        def get_text_width(text, font):
            try:
                from PIL import ImageDraw
                dummy_draw = ImageDraw.Draw(Image.new('RGB', (1, 1)))
                bbox = dummy_draw.textbbox((0, 0), text, font=font)
                return bbox[2] - bbox[0]
            except:
                # Fallback aproximado
                return len(text) * (font.size * 0.6)
        
        # División básica por puntuación
        punctuation_breaks = re.split(r'([.!?:])', text)
        sentences = []
        
        i = 0
        while i < len(punctuation_breaks):
            if i + 1 < len(punctuation_breaks) and punctuation_breaks[i+1] in '.!?:':
                sentences.append(punctuation_breaks[i] + punctuation_breaks[i+1])
                i += 2
            else:
                sentences.append(punctuation_breaks[i])
                i += 1
        
        sentences = [s for s in sentences if s.strip()]
        
        # Procesar cada frase y hacer wrapping
        lines = []
        for sentence in sentences:
            if get_text_width(sentence, font) <= max_width:
                lines.append(sentence)
                continue
            
            words = sentence.split()
            current_line = []
            current_width = 0
            
            for word in words:
                word_width = get_text_width(word + ' ', font)
                
                if current_width + word_width <= max_width:
                    current_line.append(word)
                    current_width += word_width
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                        current_line = [word]
                        current_width = word_width
                    else:
                        # Si una sola palabra es muy larga
                        lines.append(word)
            
            if current_line:
                lines.append(' '.join(current_line))
        
        return lines
    
    def process_manga_image(self, image_path, text_regions, target_language='es'):
        try:
            logger.info(f"Procesando imagen con {len(text_regions)} regiones de texto")
            
            if not text_regions:
                text_regions = self._create_default_regions(image_path)
                logger.info(f"Creando regiones de texto por defecto: {len(text_regions)}")
            
            valid_regions = []
            for region in text_regions:
                if not isinstance(region, dict):
                    logger.warning(f"Región no válida (no es dict): {type(region)}")
                    continue
                
                if 'bbox' not in region and 'bbox_simple' not in region:
                    logger.warning(f"Región sin coordenadas: {region.get('id')}")
                    continue
                
                if 'translated_text' not in region or not region['translated_text'].strip():
                    if 'text' in region and region['text'].strip():
                        region['translated_text'] = region['text']
                    else:
                        region['translated_text'] = "Texto de ejemplo"
                    
                valid_regions.append(region)
            
            if not valid_regions:
                raise ValueError("No hay regiones válidas para procesar la imagen")
            
            merged_regions = self.merge_close_regions(valid_regions)
            logger.info(f"Regiones combinadas: {len(valid_regions)} → {len(merged_regions)}")
            
            image_no_text = self.remove_original_text(image_path, valid_regions)
            
            debug_dir = os.path.dirname(os.path.dirname(image_path)) + '/results'
            os.makedirs(debug_dir, exist_ok=True)
            debug_path = os.path.join(debug_dir, 'debug_no_text.jpg')
            cv2.imwrite(debug_path, image_no_text)
            
            final_image = self.add_translated_text(image_no_text, merged_regions, target_language)
            
            output_path = self._get_output_path(image_path)
            cv2.imwrite(output_path, final_image)
            logger.info(f"Imagen final guardada en: {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error al procesar imagen de manga: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def _create_default_regions(self, image_path):
        try:
            image = cv2.imread(image_path)
            height, width = image.shape[:2]
            
            default_regions = []
            
            for bubble in self._detect_white_bubbles(image):
                x, y, w, h = bubble
                default_regions.append({
                    'id': f'auto_{len(default_regions)}',
                    'bbox_simple': [x, y, w, h],
                    'translated_text': 'Texto de ejemplo'
                })
            
            if not default_regions:
                default_regions.append({
                    'id': 'auto_0',
                    'bbox_simple': [width//4, height//4, width//2, height//6],
                    'translated_text': 'Texto de ejemplo'
                })
            
            return default_regions
        except Exception as e:
            logger.error(f"Error al crear regiones por defecto: {str(e)}")
            return [{
                'id': 'default_0',
                'bbox_simple': [50, 50, 300, 100],
                'translated_text': 'Texto de ejemplo'
            }]
    
    def _detect_white_bubbles(self, image):
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
            
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            bubbles = []
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > 1000 and area < 100000:
                    x, y, w, h = cv2.boundingRect(contour)
                    if w > 50 and h > 20 and w < image.shape[1] * 0.8 and h < image.shape[0] * 0.8:
                        bubbles.append([x, y, w, h])
            
            return bubbles
        except Exception as e:
            logger.error(f"Error al detectar burbujas: {str(e)}")
            return []
    
    def _get_output_path(self, original_path):
        dir_name = os.path.dirname(original_path)
        file_name = os.path.basename(original_path)
        name, ext = os.path.splitext(file_name)
        
        results_dir = os.path.join(os.path.dirname(dir_name), 'results')
        os.makedirs(results_dir, exist_ok=True)
        
        return os.path.join(results_dir, f"{name}_translated{ext}")
        
import re  # Añadir import de re que faltaba