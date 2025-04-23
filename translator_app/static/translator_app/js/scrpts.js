document.addEventListener('DOMContentLoaded', function() {
    // Código para inicializar componentes JavaScript
    console.log('Manga Translator JS initialized');
    
    // Función para actualizar el estado de una traducción
    function updateTranslationStatus(translationId) {
        if (!translationId) return;
        
        fetch(`/api/translations/${translationId}/status/`)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'completed' && data.translated_image) {
                    // Recargar la página para mostrar la imagen traducida
                    window.location.reload();
                } else if (data.status === 'processing') {
                    // Volver a verificar después de 3 segundos
                    setTimeout(() => updateTranslationStatus(translationId), 3000);
                }
            })
            .catch(error => console.error('Error al verificar estado:', error));
    }
    
    // Verificar si hay un ID de traducción en la página (para la vista de detalle)
    const translationDetailElement = document.getElementById('translation-detail');
    if (translationDetailElement) {
        const translationId = translationDetailElement.dataset.translationId;
        const translationStatus = translationDetailElement.dataset.translationStatus;
        
        if (translationStatus === 'processing') {
            // Iniciar la verificación periódica del estado
            updateTranslationStatus(translationId);
        }
    }
});