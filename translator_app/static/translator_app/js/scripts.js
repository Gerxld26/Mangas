document.addEventListener('DOMContentLoaded', function() {
    console.log('Manga Translator JS initialized');
    
    function updateTranslationStatus(translationId) {
        if (!translationId) return;
        
        fetch(`/api/translations/${translationId}/status/`)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'completed' && data.translated_image) {
                    window.location.reload();
                } else if (data.status === 'processing') {
                    setTimeout(() => updateTranslationStatus(translationId), 3000);
                }
            })
            .catch(error => console.error('Error al verificar estado:', error));
    }
    
    const translationDetailElement = document.getElementById('translation-detail');
    if (translationDetailElement) {
        const translationId = translationDetailElement.dataset.translationId;
        const translationStatus = translationDetailElement.dataset.translationStatus;
        
        if (translationStatus === 'processing') {
            updateTranslationStatus(translationId);
        }
    }
});