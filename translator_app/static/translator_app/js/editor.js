document.addEventListener('DOMContentLoaded', function() {
    const translationId = translationData.id;
    let translatedRegions = translationData.regions;
    let originalRegions = JSON.parse(JSON.stringify(translationData.regions));
    
    const imageWrapper = document.getElementById('image-wrapper');
    const editorImage = document.getElementById('editor-image');
    const imageContainer = document.getElementById('image-container');
    const bubbleContainer = document.getElementById('bubble-container');
    const bubbleList = document.getElementById('bubble-list');
    const bubbleCount = document.getElementById('bubble-count');
    const bubbleEditor = document.getElementById('bubble-editor');
    const noSelection = document.getElementById('no-selection');
    const originalText = document.getElementById('original-text');
    const translatedText = document.getElementById('translated-text');
    const fontSize = document.getElementById('font-size');
    const fontFamily = document.getElementById('font-family');
    const fontPreview = document.getElementById('font-preview');
    const toggleBubbles = document.getElementById('toggle-bubbles');
    const canvasSpinner = document.getElementById('canvas-spinner');
    
    const workingCanvas = document.getElementById('working-canvas');
    const workingContext = workingCanvas.getContext('2d', { willReadFrequently: true });
    const hiddenCanvas = document.getElementById('hidden-canvas');
    const hiddenContext = hiddenCanvas.getContext('2d', { willReadFrequently: true });
    
    let selectedBubble = null;
    let bubblesVisible = true;
    let dragActive = false;
    let dragStartX = 0;
    let dragStartY = 0;
    let originalBubbleX = 0;
    let originalBubbleY = 0;
    let originalImageWidth = 0;
    let originalImageHeight = 0;
    let currentImageWidth = 0;
    let scaleRatio = 1;
    let zoomMode = 'normal';
    let isVerticalImage = false;
    
    if (editorImage.complete) {
        initializeEditor();
    } else {
        editorImage.onload = initializeEditor;
    }
    
    function initializeEditor() {
        showLoading(true);
        
        originalImageWidth = editorImage.naturalWidth;
        originalImageHeight = editorImage.naturalHeight;
        
        workingCanvas.width = originalImageWidth;
        workingCanvas.height = originalImageHeight;
        hiddenCanvas.width = originalImageWidth;
        hiddenCanvas.height = originalImageHeight;
        
        workingContext.drawImage(editorImage, 0, 0, originalImageWidth, originalImageHeight);
        
        currentImageWidth = workingCanvas.clientWidth;
        scaleRatio = currentImageWidth / originalImageWidth;
        
        checkImageDimensions();
        ensureImageVisibility();
        
        createBubbles();
        
        updateBubbleList();
        updateBubbleCount();
        
        setupZoomControls();
        
        window.addEventListener('resize', handleResize);
        
        setupScrolling();
        
        showLoading(false);
        
        saveToHistory();
    }
    
    function ensureImageVisibility() {
        if (!imageContainer || !imageWrapper) return;
        
        if (isVerticalImage) {
            const containerHeight = Math.min(originalImageHeight * scaleRatio, window.innerHeight * 0.75);
            imageContainer.style.height = `${containerHeight}px`;
            imageContainer.style.overflowY = 'auto';
            imageContainer.style.overflowX = 'hidden';
            
            imageWrapper.style.width = `${workingCanvas.clientWidth}px`;
            imageWrapper.style.maxHeight = 'none';
            imageWrapper.style.minHeight = 'auto';
        } else {
            imageContainer.style.height = 'auto';
            imageContainer.style.maxHeight = '75vh';
            imageWrapper.style.width = 'auto';
        }
        
        imageWrapper.style.display = 'block';
        
        imageContainer.offsetHeight;
    }

    function showLoading(show) {
        if (show) {
            canvasSpinner.classList.remove('d-none');
        } else {
            canvasSpinner.classList.add('d-none');
        }
    }   
    
    function checkImageDimensions() {
        const ratio = originalImageHeight / originalImageWidth;
        
        isVerticalImage = ratio > 3;
        
        if (isVerticalImage) {
            if (imageContainer) {
                imageContainer.classList.add('vertical-image');
            }
            
            if (ratio > 5) {
                addVerticalNavigation();
            }
        }
    }
    
    function setupZoomControls() {
        const zoomControls = document.createElement('div');
        zoomControls.className = 'zoom-controls';
        
        const zoomToggleBtn = document.createElement('button');
        zoomToggleBtn.className = 'btn btn-sm btn-light zoom-toggle';
        zoomToggleBtn.innerHTML = '<i class="fas fa-search-plus"></i>';
        zoomToggleBtn.title = 'Cambiar zoom';
        zoomToggleBtn.addEventListener('click', toggleZoom);
        
        const zoomLevelDisplay = document.createElement('span');
        zoomLevelDisplay.className = 'zoom-level ms-2 me-2';
        zoomLevelDisplay.id = 'zoom-level-display';
        zoomLevelDisplay.textContent = '100%';
        
        zoomControls.appendChild(zoomToggleBtn);
        zoomControls.appendChild(zoomLevelDisplay);
        
        const cardHeader = document.querySelector('.card-header');
        if (cardHeader) {
            cardHeader.appendChild(zoomControls);
        }
        
        updateZoomDisplay();
        
        workingCanvas.addEventListener('click', function(e) {
            if (!dragActive && !e.target.closest('.text-bubble')) {
                toggleZoom();
            }
        });
    }
    
    function toggleZoom() {
        if (zoomMode === 'normal') {
            setZoomMode('zoomed');
        } else {
            setZoomMode('normal');
        }
        
        setTimeout(ensureImageVisibility, 50);
    }
    
    function setZoomMode(mode) {
        zoomMode = mode;
        
        let zoomFactor = (mode === 'zoomed') ? 2.0 : 1.0;
        
        if (isVerticalImage && mode === 'zoomed') {
            zoomFactor = 1.5;
        }
        
        imageWrapper.style.transform = `scale(${zoomFactor})`;
        
        if (mode === 'zoomed') {
            imageWrapper.classList.add('image-zoomed');
            document.querySelector('.zoom-toggle').innerHTML = '<i class="fas fa-search-minus"></i>';
        } else {
            imageWrapper.classList.remove('image-zoomed');
            document.querySelector('.zoom-toggle').innerHTML = '<i class="fas fa-search-plus"></i>';
        }
        
        updateZoomDisplay(zoomFactor);
        updateAllBubblePositions();
        showImageInfo();
        
        if (selectedBubble && mode === 'zoomed') {
            setTimeout(() => scrollToBubble(selectedBubble), 100);
        }
    }
    
    function updateZoomDisplay(zoomFactor) {
        const zoomDisplay = document.getElementById('zoom-level-display');
        if (zoomDisplay) {
            const zoomLevel = zoomFactor || (zoomMode === 'zoomed' ? 2.0 : 1.0);
            zoomDisplay.textContent = `${Math.round(zoomLevel * 100)}%`;
        }
    }
    
    function showImageInfo() {
        const imageInfoElement = document.getElementById('image-info');
        if (imageInfoElement) {
            const zoomPercent = zoomMode === 'zoomed' ? 200 : 100;
            imageInfoElement.textContent = `${originalImageWidth} × ${originalImageHeight}px (Zoom: ${zoomPercent}%)`;
        }
    }
    
    function setupScrolling() {
        if (!imageContainer) return;
        
        imageContainer.addEventListener('wheel', function(e) {
            if (isVerticalImage && zoomMode === 'zoomed') {
                e.preventDefault();
                imageContainer.scrollTop += e.deltaY;
            }
        }, { passive: false });
        
        let touchStartY = 0;
        let touchStartScrollTop = 0;
        
        imageContainer.addEventListener('touchstart', function(e) {
            touchStartY = e.touches[0].clientY;
            touchStartScrollTop = imageContainer.scrollTop;
        }, { passive: true });
        
        imageContainer.addEventListener('touchmove', function(e) {
            if (isVerticalImage && zoomMode === 'zoomed') {
                const touchY = e.touches[0].clientY;
                const deltaY = touchStartY - touchY;
                imageContainer.scrollTop = touchStartScrollTop + deltaY;
            }
        }, { passive: true });
    }
    
    function addVerticalNavigation() {
        if (!document.querySelector('.vertical-nav') && imageContainer) {
            const navContainer = document.createElement('div');
            navContainer.className = 'vertical-nav';
            
            const topBtn = document.createElement('button');
            topBtn.innerHTML = '<i class="fas fa-chevron-up"></i>';
            topBtn.title = 'Ir al inicio';
            topBtn.addEventListener('click', function() {
                imageContainer.scrollTo({
                    top: 0,
                    behavior: 'smooth'
                });
            });
            
            const bottomBtn = document.createElement('button');
            bottomBtn.innerHTML = '<i class="fas fa-chevron-down"></i>';
            bottomBtn.title = 'Ir al final';
            bottomBtn.addEventListener('click', function() {
                imageContainer.scrollTo({
                    top: imageContainer.scrollHeight,
                    behavior: 'smooth'
                });
            });
            
            navContainer.appendChild(topBtn);
            navContainer.appendChild(bottomBtn);
            
            document.body.appendChild(navContainer);
            
            addPositionIndicator();
        }
    }
    
    function addPositionIndicator() {
        if (!document.querySelector('.position-indicator') && imageContainer) {
            const indicator = document.createElement('div');
            indicator.className = 'position-indicator';
            indicator.textContent = 'Posición: 0%';
            document.body.appendChild(indicator);
            
            imageContainer.addEventListener('scroll', function() {
                const scrollTotal = imageContainer.scrollHeight - imageContainer.clientHeight;
                const scrolled = imageContainer.scrollTop;
                const percentage = Math.round((scrolled / scrollTotal) * 100);
                
                indicator.textContent = `Posición: ${percentage}%`;
            });
        }
    }
    
    function handleResize() {
        const newWidth = workingCanvas.clientWidth;
        
        if (newWidth !== currentImageWidth) {
            currentImageWidth = newWidth;
            scaleRatio = currentImageWidth / originalImageWidth;
            
            updateAllBubblePositions();
            showImageInfo();
            ensureImageVisibility();
        }
    }
    
    function updateAllBubblePositions() {
        const bubbles = document.querySelectorAll('.text-bubble');
        const zoomFactor = zoomMode === 'zoomed' ? (isVerticalImage ? 1.5 : 2.0) : 1.0;
        
        bubbles.forEach(bubble => {
            const index = parseInt(bubble.dataset.index);
            const [origX, origY, origWidth, origHeight] = translatedRegions[index].bbox_simple;
            
            const scaledX = origX * scaleRatio * zoomFactor;
            const scaledY = origY * scaleRatio * zoomFactor;
            const scaledWidth = origWidth * scaleRatio * zoomFactor;
            const scaledHeight = origHeight * scaleRatio * zoomFactor;
            
            bubble.style.left = `${scaledX}px`;
            bubble.style.top = `${scaledY}px`;
            bubble.style.width = `${scaledWidth}px`;
            bubble.style.height = `${scaledHeight}px`;
            
            if (translatedRegions[index].font_size) {
                const origFontSize = translatedRegions[index].font_size;
                bubble.style.fontSize = `${origFontSize * scaleRatio * zoomFactor}px`;
            }
        });
    }
    
    function createBubbles() {
        const existingBubbles = document.querySelectorAll('.text-bubble');
        existingBubbles.forEach(bubble => bubble.remove());
        
        translatedRegions.forEach((region, index) => {
            if (!region.bbox_simple || !region.translated_text) return;
            
            const [origX, origY, origWidth, origHeight] = region.bbox_simple;
            const zoomFactor = zoomMode === 'zoomed' ? (isVerticalImage ? 1.5 : 2.0) : 1.0;
            
            const scaledX = origX * scaleRatio * zoomFactor;
            const scaledY = origY * scaleRatio * zoomFactor;
            const scaledWidth = origWidth * scaleRatio * zoomFactor;
            const scaledHeight = origHeight * scaleRatio * zoomFactor;
            
            const bubble = document.createElement('div');
            bubble.className = 'text-bubble';
            bubble.dataset.index = index;
            
            bubble.style.left = `${scaledX}px`;
            bubble.style.top = `${scaledY}px`;
            bubble.style.width = `${scaledWidth}px`;
            bubble.style.height = `${scaledHeight}px`;
            
            if (region.font_size) {
                const scaledFontSize = region.font_size * scaleRatio * zoomFactor;
                bubble.style.fontSize = `${scaledFontSize}px`;
            }
            if (region.font_family) {
                bubble.style.fontFamily = region.font_family;
            }
            if (region.text_align) {
                bubble.style.textAlign = region.text_align;
            }
            
            const textElement = document.createElement('p');
            textElement.textContent = region.translated_text;
            bubble.appendChild(textElement);
            
            const resizeHandle = document.createElement('div');
            resizeHandle.className = 'resize-handle';
            bubble.appendChild(resizeHandle);
            
            bubble.addEventListener('mousedown', onBubbleMouseDown);
            bubble.addEventListener('click', onBubbleClick);
            resizeHandle.addEventListener('mousedown', onResizeHandleMouseDown);
            
            bubbleContainer.appendChild(bubble);
        });
    }
    
    function updateBubbleList() {
        bubbleList.innerHTML = '';
        
        if (translatedRegions.length === 0) {
            const emptyMessage = document.createElement('div');
            emptyMessage.className = 'text-center text-muted p-3';
            emptyMessage.innerHTML = '<i class="fas fa-info-circle me-2"></i>No se ha detectado texto';
            bubbleList.appendChild(emptyMessage);
            return;
        }
        
        translatedRegions.forEach((region, index) => {
            if (!region.text && !region.translated_text) return;
            
            const bubbleItem = document.createElement('div');
            bubbleItem.className = 'bubble-item';
            if (selectedBubble && parseInt(selectedBubble.dataset.index) === index) {
                bubbleItem.classList.add('active');
            }
            
            let displayText = region.translated_text || region.text || `Burbuja ${index + 1}`;
            if (displayText.length > 30) {
                displayText = displayText.substring(0, 27) + '...';
            }
            
            bubbleItem.textContent = displayText;
            bubbleItem.title = region.text || '';
            bubbleItem.dataset.index = index;
            
            bubbleItem.addEventListener('click', () => {
                const bubbles = document.querySelectorAll('.text-bubble');
                const targetBubble = Array.from(bubbles).find(b => parseInt(b.dataset.index) === index);
                if (targetBubble) {
                    selectBubble(targetBubble);
                    scrollToBubble(targetBubble);
                }
            });
            
            bubbleList.appendChild(bubbleItem);
        });
    }
    
    function scrollToBubble(bubble) {
        if (!imageContainer || (!isVerticalImage && zoomMode !== 'zoomed')) return;
        
        const bubbleRect = bubble.getBoundingClientRect();
        const containerRect = imageContainer.getBoundingClientRect();
        
        if (bubbleRect.top < containerRect.top || bubbleRect.bottom > containerRect.bottom) {
            const y = parseInt(bubble.style.top) || 0;
            const height = parseInt(bubble.style.height) || 0;
            
            const centerY = y - (imageContainer.clientHeight / 2) + (height / 2);
            
            imageContainer.scrollTo({
                top: Math.max(0, centerY),
                behavior: 'smooth'
            });
        }
    }
    
    function updateBubbleCount() {
        const count = translatedRegions.filter(r => r.text || r.translated_text).length;
        bubbleCount.textContent = count;
    }
    
    function selectBubble(bubble) {
        if (selectedBubble) {
            selectedBubble.classList.remove('selected');
        }
        
        selectedBubble = bubble;
        if (selectedBubble) {
            selectedBubble.classList.add('selected');
            
            const index = parseInt(selectedBubble.dataset.index);
            const region = translatedRegions[index];
            
            originalText.textContent = region.text || '(No text detected)';
            translatedText.value = region.translated_text || '';
            
            const currentFontSize = region.font_size || 16;
            fontSize.value = currentFontSize;
            
            if (fontFamily && fontPreview) {
                const currentFont = region.font_family || 'Arial, sans-serif';
                fontFamily.value = currentFont;
                fontPreview.style.fontFamily = currentFont;
                fontPreview.textContent = region.translated_text || 'Vista previa de la fuente';
            }
            
            const textAlign = region.text_align || 'center';
            const alignBtns = document.querySelectorAll('.btn-group .btn');
            alignBtns.forEach(btn => btn.classList.remove('active'));
            const activeAlignBtn = document.getElementById(`align-${textAlign}`);
            if (activeAlignBtn) {
                activeAlignBtn.classList.add('active');
            }
            
            bubbleEditor.classList.remove('d-none');
            noSelection.classList.add('d-none');
            
            const items = bubbleList.querySelectorAll('.bubble-item');
            items.forEach(item => item.classList.remove('active'));
            const activeItem = bubbleList.querySelector(`.bubble-item[data-index="${index}"]`);
            if (activeItem) activeItem.classList.add('active');
            
            if (zoomMode === 'zoomed') {
                scrollToBubble(selectedBubble);
            }
        } else {
            bubbleEditor.classList.add('d-none');
            noSelection.classList.remove('d-none');
        }
    }
    
    function onBubbleClick(event) {
        event.stopPropagation();
        selectBubble(event.currentTarget);
    }
    
    function onBubbleMouseDown(event) {
        if (event.target.classList.contains('resize-handle')) return;
        
        const bubble = event.currentTarget;
        dragActive = true;
        dragStartX = event.clientX;
        dragStartY = event.clientY;
        originalBubbleX = parseInt(bubble.style.left) || 0;
        originalBubbleY = parseInt(bubble.style.top) || 0;
        
        selectBubble(bubble);
        
        document.body.classList.add('dragging-active');
        bubble.classList.add('dragging');
        
        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);
        
        event.preventDefault();
        event.stopPropagation();
    }
    
    function onMouseMove(event) {
        if (!dragActive || !selectedBubble) return;
        
        const deltaX = event.clientX - dragStartX;
        const deltaY = event.clientY - dragStartY;
        
        selectedBubble.style.left = `${originalBubbleX + deltaX}px`;
        selectedBubble.style.top = `${originalBubbleY + deltaY}px`;
        
        if (isVerticalImage && imageContainer) {
            const containerRect = imageContainer.getBoundingClientRect();
            const bubbleRect = selectedBubble.getBoundingClientRect();
            
            if (bubbleRect.top < containerRect.top + 50) {
                imageContainer.scrollBy({
                    top: -10,
                    behavior: 'auto'
                });
            }
            
            if (bubbleRect.bottom > containerRect.bottom - 50) {
                imageContainer.scrollBy({
                    top: 10,
                    behavior: 'auto'
                });
            }
        }
    }
    
    function onMouseUp(event) {
        if (!dragActive) return;
        
        if (selectedBubble) {
            const index = parseInt(selectedBubble.dataset.index);
            
            const currentX = parseInt(selectedBubble.style.left) || 0;
            const currentY = parseInt(selectedBubble.style.top) || 0;
            const currentWidth = parseInt(selectedBubble.style.width) || 100;
            const currentHeight = parseInt(selectedBubble.style.height) || 50;
            
            const zoomFactor = zoomMode === 'zoomed' ? (isVerticalImage ? 1.5 : 2.0) : 1.0;
            const originalX = currentX / (scaleRatio * zoomFactor);
            const originalY = currentY / (scaleRatio * zoomFactor);
            const originalWidth = currentWidth / (scaleRatio * zoomFactor);
            const originalHeight = currentHeight / (scaleRatio * zoomFactor);
            
            translatedRegions[index].bbox_simple = [originalX, originalY, originalWidth, originalHeight];
            
            selectedBubble.classList.remove('dragging');
            saveToHistory();
        }
        
        document.body.classList.remove('dragging-active');
        dragActive = false;
        
        document.removeEventListener('mousemove', onMouseMove);
        document.removeEventListener('mouseup', onMouseUp);
    }
    
    function onResizeHandleMouseDown(event) {
        event.stopPropagation();
        
        const bubble = event.target.parentElement;
        const startWidth = parseInt(bubble.style.width) || 100;
        const startHeight = parseInt(bubble.style.height) || 50;
        const startX = event.clientX;
        const startY = event.clientY;
        
        function onResizeMouseMove(e) {
            const deltaX = e.clientX - startX;
            const deltaY = e.clientY - startY;
            
            const zoomFactor = zoomMode === 'zoomed' ? (isVerticalImage ? 1.5 : 2.0) : 1.0;
            const minWidth = 60 * zoomFactor;
            const minHeight = 30 * zoomFactor;
            
            bubble.style.width = `${Math.max(minWidth, startWidth + deltaX)}px`;
            bubble.style.height = `${Math.max(minHeight, startHeight + deltaY)}px`;
        }
        
        function onResizeMouseUp() {
            const index = parseInt(bubble.dataset.index);
            
            const currentX = parseInt(bubble.style.left) || 0;
            const currentY = parseInt(bubble.style.top) || 0;
            const currentWidth = parseInt(bubble.style.width) || 100;
            const currentHeight = parseInt(bubble.style.height) || 50;
            
            const zoomFactor = zoomMode === 'zoomed' ? (isVerticalImage ? 1.5 : 2.0) : 1.0;
            const originalX = currentX / (scaleRatio * zoomFactor);
            const originalY = currentY / (scaleRatio * zoomFactor);
            const originalWidth = currentWidth / (scaleRatio * zoomFactor);
            const originalHeight = currentHeight / (scaleRatio * zoomFactor);
            
            translatedRegions[index].bbox_simple = [originalX, originalY, originalWidth, originalHeight];
            
            saveToHistory();
            
            document.removeEventListener('mousemove', onResizeMouseMove);
            document.removeEventListener('mouseup', onResizeMouseUp);
        }
        
        document.addEventListener('mousemove', onResizeMouseMove);
        document.addEventListener('mouseup', onResizeMouseUp);
        
        event.preventDefault();
    }
    
    if (translatedText) {
        translatedText.addEventListener('input', function() {
            if (!selectedBubble) return;
            
            const index = parseInt(selectedBubble.dataset.index);
            const textElement = selectedBubble.querySelector('p');
            
            textElement.textContent = this.value;
            translatedRegions[index].translated_text = this.value;
            
            if (fontPreview) {
                fontPreview.textContent = this.value || 'Vista previa de la fuente';
            }
            
            updateBubbleList();
        });
    }
    
    if (fontSize) {
        fontSize.addEventListener('input', function() {
            if (!selectedBubble) return;
            
            const newSize = parseInt(this.value) || 16;
            
            const zoomFactor = zoomMode === 'zoomed' ? (isVerticalImage ? 1.5 : 2.0) : 1.0;
            const scaledSize = newSize * scaleRatio * zoomFactor;
            selectedBubble.style.fontSize = `${scaledSize}px`;
            
            const index = parseInt(selectedBubble.dataset.index);
            translatedRegions[index].font_size = newSize;
        });
    }
    
    if (fontFamily) {
        fontFamily.addEventListener('change', function() {
            if (!selectedBubble) return;
            
            const font = this.value;
            selectedBubble.style.fontFamily = font;
            
            if (fontPreview) {
                fontPreview.style.fontFamily = font;
            }
            
            const index = parseInt(selectedBubble.dataset.index);
            translatedRegions[index].font_family = font;
        });
    }
    
    if (toggleBubbles) {
        toggleBubbles.addEventListener('click', function() {
            bubblesVisible = !bubblesVisible;
            const bubbles = document.querySelectorAll('.text-bubble');
            
            bubbles.forEach(bubble => {
                bubble.style.display = bubblesVisible ? 'flex' : 'none';
            });
            
            this.innerHTML = bubblesVisible ?
                '<i class="fas fa-eye-slash"></i> Ocultar burbujas' :
                '<i class="fas fa-eye"></i> Mostrar burbujas';
        });
    }
    
    document.querySelectorAll('#align-left, #align-center, #align-right').forEach(btn => {
        if (btn) {
            btn.addEventListener('click', function() {
                if (!selectedBubble) return;
                
                const alignBtns = document.querySelectorAll('.btn-group .btn');
                alignBtns.forEach(b => b.classList.remove('active'));
                this.classList.add('active');
                
                const alignment = this.id.replace('align-', '');
                selectedBubble.style.textAlign = alignment;
                
                const index = parseInt(selectedBubble.dataset.index);
                translatedRegions[index].text_align = alignment;
            });
        }
    });
    
    document.querySelectorAll('#move-up, #move-down, #move-left, #move-right').forEach(btn => {
        if (btn) {
            btn.addEventListener('click', function() {
                if (!selectedBubble) return;
                
                const index = parseInt(selectedBubble.dataset.index);
                
                const currentX = parseInt(selectedBubble.style.left) || 0;
                const currentY = parseInt(selectedBubble.style.top) || 0;
                const currentWidth = parseInt(selectedBubble.style.width) || 100;
                const currentHeight = parseInt(selectedBubble.style.height) || 50;
                
                const zoomFactor = zoomMode === 'zoomed' ? (isVerticalImage ? 1.5 : 2.0) : 1.0;
                const moveStep = 5 * zoomFactor;
                
                const direction = this.id.replace('move-', '');
                let newX = currentX;
                let newY = currentY;
                
                switch (direction) {
                    case 'up': newY = currentY - moveStep; break;
                    case 'down': newY = currentY + moveStep; break;
                    case 'left': newX = currentX - moveStep; break;
                    case 'right': newX = currentX + moveStep; break;
                }
                
                selectedBubble.style.left = `${newX}px`;
                selectedBubble.style.top = `${newY}px`;
                
                const originalX = newX / (scaleRatio * zoomFactor);
                const originalY = newY / (scaleRatio * zoomFactor);
                const originalWidth = currentWidth / (scaleRatio * zoomFactor);
                const originalHeight = currentHeight / (scaleRatio * zoomFactor);
                
                translatedRegions[index].bbox_simple = [originalX, originalY, originalWidth, originalHeight];
            });
        }
    });
    
    const deleteBtn = document.getElementById('delete-bubble');
    if (deleteBtn) {
        deleteBtn.addEventListener('click', function() {
            if (!selectedBubble) return;
            
            if (!confirm('¿Estás seguro de que deseas eliminar esta burbuja?')) return;
            
            saveToHistory();
            
            const index = parseInt(selectedBubble.dataset.index);
            
            translatedRegions.splice(index, 1);
            
            const bubbles = document.querySelectorAll('.text-bubble');
            bubbles.forEach(bubble => {
                const bubbleIndex = parseInt(bubble.dataset.index);
                if (bubbleIndex > index) {
                    bubble.dataset.index = bubbleIndex - 1;
                }
            });
            
            selectedBubble.remove();
            selectedBubble = null;
            
            bubbleEditor.classList.add('d-none');
            noSelection.classList.remove('d-none');
            updateBubbleList();
            updateBubbleCount();
        });
    }
    
    const addBtn = document.getElementById('add-bubble');
    if (addBtn) {
        addBtn.addEventListener('click', function() {
            saveToHistory();
            
            let initialX, initialY;
            
            if (isVerticalImage && imageContainer && zoomMode === 'zoomed') {
                const scrollTop = imageContainer.scrollTop;
                const zoomFactor = isVerticalImage ? 1.5 : 2.0;
                
                initialX = originalImageWidth / 2;
                initialY = (scrollTop / (scaleRatio * zoomFactor)) + (imageContainer.clientHeight / (2 * scaleRatio * zoomFactor));
            } else {
                initialX = originalImageWidth / 2;
                initialY = originalImageHeight / 2;
            }
            
            const newRegion = {
                id: translatedRegions.length,
                text: '',
                translated_text: 'Nuevo texto',
                bbox_simple: [initialX, initialY, 150, 80],
                confidence: 100,
                language_detected: 'auto',
                font_family: 'Arial, sans-serif',
                text_align: 'center',
                font_size: 16
            };
            
            translatedRegions.push(newRegion);
            
            const bubble = document.createElement('div');
            bubble.className = 'text-bubble';
            bubble.dataset.index = translatedRegions.length - 1;
            
            const zoomFactor = zoomMode === 'zoomed' ? (isVerticalImage ? 1.5 : 2.0) : 1.0;
            const scaledX = initialX * scaleRatio * zoomFactor;
            const scaledY = initialY * scaleRatio * zoomFactor;
            const scaledWidth = 150 * scaleRatio * zoomFactor;
            const scaledHeight = 80 * scaleRatio * zoomFactor;
            
            bubble.style.left = `${scaledX}px`;
            bubble.style.top = `${scaledY}px`;
            bubble.style.width = `${scaledWidth}px`;
            bubble.style.height = `${scaledHeight}px`;
            bubble.style.fontFamily = newRegion.font_family;
            bubble.style.textAlign = newRegion.text_align;
            
            const scaledFontSize = newRegion.font_size * scaleRatio * zoomFactor;
            bubble.style.fontSize = `${scaledFontSize}px`;
            
            const textElement = document.createElement('p');
            textElement.textContent = newRegion.translated_text;
            bubble.appendChild(textElement);
            
            const resizeHandle = document.createElement('div');
            resizeHandle.className = 'resize-handle';
            bubble.appendChild(resizeHandle);
            
            bubble.addEventListener('mousedown', onBubbleMouseDown);
            bubble.addEventListener('click', onBubbleClick);
            resizeHandle.addEventListener('mousedown', onResizeHandleMouseDown);
            
            bubbleContainer.appendChild(bubble);
            
            selectBubble(bubble);
            
            updateBubbleList();
            updateBubbleCount();
        });
    }
    
    const translateBtn = document.getElementById('translate-to-spanish');
    if (translateBtn) {
        translateBtn.addEventListener('click', function() {
            if (!selectedBubble) return;
            
            const index = parseInt(selectedBubble.dataset.index);
            const region = translatedRegions[index];
            
            if (!region.text || region.text.trim() === '') {
                showToast('No hay texto original para traducir', 'warning');
                return;
            }
            
            const originalContent = this.innerHTML;
            this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Traduciendo...';
            this.disabled = true;
            
            fetch('/api/translate_text/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    text: region.text,
                    source_language: region.language_detected || 'auto',
                    target_language: 'es'
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.translated_text) {
                    translatedText.value = data.translated_text;
                    translatedText.dispatchEvent(new Event('input'));
                    showToast('Traducción completada', 'success');
                } else {
                    showToast('Error al traducir: ' + (data.error || 'Error desconocido'), 'error');
                }
            })
            .catch(error => {
                showToast('Error al comunicarse con el servidor de traducción', 'error');
            })
            .finally(() => {
                this.disabled = false;
                this.innerHTML = originalContent;
            });
        });
    }
    
    const saveBtn = document.getElementById('save-changes');
    if (saveBtn) {
        saveBtn.addEventListener('click', function() {
            showLoading(true);
            
            const originalContent = this.innerHTML;
            this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Guardando...';
            this.disabled = true;
            
            fetch(`/api/translations/${translationId}/update_regions/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    regions: translatedRegions
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showToast('Cambios guardados correctamente', 'success');
                    originalRegions = JSON.parse(JSON.stringify(translatedRegions));
                } else {
                    showToast('Error al guardar: ' + (data.error || 'Error desconocido'), 'error');
                }
            })
            .catch(error => {
                showToast('Error al comunicarse con el servidor', 'error');
            })
            .finally(() => {
                this.disabled = false;
                this.innerHTML = originalContent;
                showLoading(false);
            });
        });
    }
    
    const resetBtn = document.getElementById('reset-changes');
    if (resetBtn) {
        resetBtn.addEventListener('click', function() {
            if (!confirm('¿Estás seguro de que deseas deshacer todos los cambios?')) return;
            
            translatedRegions = JSON.parse(JSON.stringify(originalRegions));
            createBubbles();
            updateBubbleList();
            updateBubbleCount();
            
            if (selectedBubble) {
                selectedBubble = null;
                bubbleEditor.classList.add('d-none');
                noSelection.classList.remove('d-none');
            }
            
            historyStack.length = 0;
            saveToHistory();
            
            showToast('Cambios descartados', 'info');
        });
    }
    
    const regenerateBtn = document.getElementById('regenerate-image');
    if (regenerateBtn) {
        regenerateBtn.addEventListener('click', function() {
            if (!confirm('¿Estás seguro de que deseas regenerar la imagen? Esto procesará la imagen con el texto traducido.')) return;
            
            showLoading(true);
            
            const originalContent = this.innerHTML;
            this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Regenerando...';
            this.disabled = true;
            
            fetch(`/api/translations/${translationId}/regenerate/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    regions: translatedRegions
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showToast('Imagen regenerada correctamente', 'success');
                    
                    const timestamp = new Date().getTime();
                    editorImage.src = `${editorImage.src.split('?')[0]}?t=${timestamp}`;
                    
                    editorImage.onload = function() {
                        workingContext.clearRect(0, 0, workingCanvas.width, workingCanvas.height);
                        workingContext.drawImage(editorImage, 0, 0, originalImageWidth, originalImageHeight);
                        showToast('Imagen actualizada', 'info');
                    };
                } else {
                    showToast('Error al regenerar la imagen: ' + (data.error || 'Error desconocido'), 'error');
                }
            })
            .catch(error => {
                showToast('Error al comunicarse con el servidor', 'error');
            })
            .finally(() => {
                this.disabled = false;
                this.innerHTML = originalContent;
                showLoading(false);
            });
        });
    }
    
    function setupDownloadHandlers() {
        const exportBtn = document.getElementById('export-image');
        if (exportBtn) {
            exportBtn.addEventListener('click', downloadProcessedImage);
        }
        
        const downloadBtn = document.getElementById('download-image');
        if (downloadBtn) {
            downloadBtn.addEventListener('click', downloadProcessedImage);
        }
    }
    
    function downloadProcessedImage() {
        showLoading(true);
        
        try {
            hiddenContext.clearRect(0, 0, hiddenCanvas.width, hiddenCanvas.height);
            hiddenContext.drawImage(editorImage, 0, 0, originalImageWidth, originalImageHeight);
            
            translatedRegions.forEach(region => {
                if (!region.bbox_simple || !region.translated_text) return;
                
                const [x, y, width, height] = region.bbox_simple;
                
                hiddenContext.save();
                
                hiddenContext.font = `${region.font_size || 16}px ${region.font_family || 'Arial, sans-serif'}`;
                hiddenContext.fillStyle = '#000000';
                hiddenContext.textAlign = region.text_align || 'center';
                hiddenContext.textBaseline = 'middle';
                
                const textX = x + (width / 2);
                const textY = y + (height / 2);
                
                const lines = region.translated_text.split('\n');
                const lineHeight = (region.font_size || 16) * 1.2;
                
                lines.forEach((line, i) => {
                    hiddenContext.fillText(
                        line,
                        textX,
                        textY - ((lines.length - 1) * lineHeight / 2) + (i * lineHeight)
                    );
                });
                
                hiddenContext.restore();
            });
            
            const dataUrl = hiddenCanvas.toDataURL('image/png');
            
            const link = document.createElement('a');
            link.href = dataUrl;
            link.download = `torii_translated_${translationId}.png`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            showToast('Imagen descargada correctamente', 'success');
        } catch (error) {
            showToast('Error al descargar la imagen', 'error');
        } finally {
            showLoading(false);
        }
    }
    
    function showToast(message, type = 'info') {
        let toastContainer = document.querySelector('.toast-container');
        
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            document.body.appendChild(toastContainer);
        }
        
        const toastId = 'toast-' + Date.now();
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.id = toastId;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        
        toastContainer.appendChild(toast);
        
        const bsToast = new bootstrap.Toast(toast, {
            autohide: true,
            delay: 3000
        });
        bsToast.show();
        
        toast.addEventListener('hidden.bs.toast', function() {
            toast.remove();
        });
    }
    
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    const historyStack = [];
    const maxHistorySize = 10;
    let currentHistoryIndex = -1;
    
    function saveToHistory() {
        const currentState = JSON.parse(JSON.stringify(translatedRegions));
        
        if (currentHistoryIndex >= 0 && currentHistoryIndex < historyStack.length - 1) {
            historyStack.splice(currentHistoryIndex + 1);
        }
        
        historyStack.push(currentState);
        
        if (historyStack.length > maxHistorySize) {
            historyStack.shift();
        }
        
        currentHistoryIndex = historyStack.length - 1;
        
        updateUndoRedoButtons();
    }
    
    function updateUndoRedoButtons() {
        const undoBtn = document.getElementById('undo-button');
        const redoBtn = document.getElementById('redo-button');
        
        if (undoBtn) {
            undoBtn.disabled = currentHistoryIndex <= 0;
        }
        
        if (redoBtn) {
            redoBtn.disabled = currentHistoryIndex >= historyStack.length - 1;
        }
    }
    
    document.addEventListener('keydown', function(e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
            e.preventDefault();
            undoAction();
        }
        
        if ((e.ctrlKey || e.metaKey) && ((e.key === 'z' && e.shiftKey) || e.key === 'y')) {
            e.preventDefault();
            redoAction();
        }
        
        if (e.key === 'Escape' && selectedBubble) {
            selectedBubble.classList.remove('selected');
            selectedBubble = null;
            bubbleEditor.classList.add('d-none');
            noSelection.classList.remove('d-none');
        }
    });
    
    function undoAction() {
        if (currentHistoryIndex > 0) {
            currentHistoryIndex--;
            translatedRegions = JSON.parse(JSON.stringify(historyStack[currentHistoryIndex]));
            createBubbles();
            updateBubbleList();
            updateUndoRedoButtons();
            
            if (selectedBubble) {
                selectedBubble = null;
                bubbleEditor.classList.add('d-none');
                noSelection.classList.remove('d-none');
            }
        }
    }
    
    function redoAction() {
        if (currentHistoryIndex < historyStack.length - 1) {
            currentHistoryIndex++;
            translatedRegions = JSON.parse(JSON.stringify(historyStack[currentHistoryIndex]));
            createBubbles();
            updateBubbleList();
            updateUndoRedoButtons();
            
            if (selectedBubble) {
                selectedBubble = null;
                bubbleEditor.classList.add('d-none');
                noSelection.classList.remove('d-none');
            }
        }
    }
    
    const undoBtn = document.getElementById('undo-button');
    if (undoBtn) {
        undoBtn.addEventListener('click', undoAction);
    }
    
    const redoBtn = document.getElementById('redo-button');
    if (redoBtn) {
        redoBtn.addEventListener('click', redoAction);
    }
    
    let autoSaveTimer = null;
    const autoSaveInterval = 60000; 
    
    function setupAutoSave() {
        if (autoSaveTimer) {
            clearInterval(autoSaveTimer);
        }
        
        autoSaveTimer = setInterval(() => {
            if (JSON.stringify(translatedRegions) !== JSON.stringify(originalRegions)) {
                fetch(`/api/translations/${translationId}/update_regions/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify({
                        regions: translatedRegions,
                        auto_save: true
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        originalRegions = JSON.parse(JSON.stringify(translatedRegions));
                        
                        const autoSaveIndicator = document.getElementById('auto-save-indicator');
                        if (autoSaveIndicator) {
                            autoSaveIndicator.classList.add('flash');
                            setTimeout(() => {
                                autoSaveIndicator.classList.remove('flash');
                            }, 1000);
                        }
                    }
                })
                .catch(error => {});
            }
        }, autoSaveInterval);
    }
    
    setupAutoSave();
    
    document.addEventListener('visibilitychange', function() {
        if (document.visibilityState === 'hidden') {
            if (JSON.stringify(translatedRegions) !== JSON.stringify(originalRegions)) {
                fetch(`/api/translations/${translationId}/update_regions/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify({
                        regions: translatedRegions,
                        auto_save: true
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        originalRegions = JSON.parse(JSON.stringify(translatedRegions));
                    }
                })
                .catch(error => {});
            }
            
            if (autoSaveTimer) {
                clearInterval(autoSaveTimer);
                autoSaveTimer = null;
            }
        } else {
            setupAutoSave();
        }
    });
    
    function initializeExtraTools() {
        const autoAdjustBtn = document.createElement('button');
        autoAdjustBtn.className = 'btn btn-sm btn-info ml-2';
        autoAdjustBtn.innerHTML = '<i class="fas fa-magic"></i> Auto-ajustar';
        autoAdjustBtn.title = 'Ajustar tamaño de todas las burbujas automáticamente';
        
        autoAdjustBtn.addEventListener('click', function() {
            if (!confirm('¿Ajustar automáticamente el tamaño de todas las burbujas según su contenido?')) return;
            
            saveToHistory();
            
            let adjustedCount = 0;
            translatedRegions.forEach((region, index) => {
                if (!region.translated_text) return;
                
                const tempElement = document.createElement('div');
                tempElement.style.position = 'absolute';
                tempElement.style.visibility = 'hidden';
                tempElement.style.fontFamily = region.font_family || 'Arial, sans-serif';
                tempElement.style.fontSize = `${region.font_size || 16}px`;
                tempElement.style.whiteSpace = 'pre-wrap';
                tempElement.style.width = 'auto';
                tempElement.style.maxWidth = '500px';
                tempElement.textContent = region.translated_text;
                
                document.body.appendChild(tempElement);
                
                const textWidth = tempElement.clientWidth + 20; 
                const textHeight = tempElement.clientHeight + 20;
                
                document.body.removeChild(tempElement);
                
                if (region.bbox_simple) {
                    const [x, y, width, height] = region.bbox_simple;
                    
                    if (textWidth > width || textHeight > height) {
                        region.bbox_simple = [x, y, Math.max(width, textWidth), Math.max(height, textHeight)];
                        adjustedCount++;
                    }
                }
            });
            
            createBubbles();
            updateBubbleList();
            
            showToast(`Se han ajustado ${adjustedCount} burbujas`, 'success');
        });
        
        const toolsContainer = document.querySelector('.editor-tools');
        if (toolsContainer) {
            toolsContainer.appendChild(autoAdjustBtn);
        }
    }
    
    initializeExtraTools();
    setupDownloadHandlers();
    
    function applyFixStyles() {
        const style = document.createElement('style');
        style.textContent = `
            /* Mejoras para visualización de imagen */
            .image-container {
                overflow-y: auto;
                overflow-x: hidden;
            }
            
            #image-wrapper {
                min-height: 100px;
            }
            
            /* Prevenir interacciones no deseadas durante arrastre */
            .dragging {
                cursor: grabbing !important;
                pointer-events: none;
            }
            
            /* Clase global para cuando se está arrastrando */
            body.dragging-active {
                cursor: grabbing;
                user-select: none;
            }
            
            /* Mejorar burbujas de texto */
            .text-bubble {
                transition: none;
                user-select: none;
            }
            
            .vertical-image #image-wrapper {
                min-height: 300px;
                width: 100%;
            }
        `;
        document.head.appendChild(style);
    }
    
    applyFixStyles();
});