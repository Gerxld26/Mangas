from django import forms
from .models import MangaPage

class MangaTranslationForm(forms.ModelForm):
    """Formulario para subir una página de manga y seleccionar opciones de traducción"""
    
    class Meta:
        model = MangaPage
        fields = ['title', 'original_image', 'source_language', 'target_language']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Título (opcional)'}),
            'original_image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'source_language': forms.Select(attrs={'class': 'form-select'}),
            'target_language': forms.Select(attrs={'class': 'form-select'}),
        }
        
    def clean_original_image(self):
        """Valida que la imagen sea de un formato aceptado"""
        image = self.cleaned_data.get('original_image')
        if image:
            # Comprobar extensión
            ext = image.name.split('.')[-1].lower()
            if ext not in ['jpg', 'jpeg', 'png', 'webp']:
                raise forms.ValidationError(
                    "Formato de imagen no soportado. Por favor, sube una imagen en formato JPG, PNG o WebP."
                )
            
            # Comprobar tamaño (máximo 10MB)
            if image.size > 10 * 1024 * 1024:
                raise forms.ValidationError(
                    "La imagen es demasiado grande. El tamaño máximo permitido es 10MB."
                )
                
        return image