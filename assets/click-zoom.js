/**
 * Click-to-zoom functionality for diagram images
 */
document.addEventListener('DOMContentLoaded', function() {
    // Function to add click handlers to diagram images
    function setupClickZoom() {
        const images = document.querySelectorAll('.click-zoom-img');
        
        images.forEach(function(img) {
            // Remove any existing click handler
            img.removeEventListener('click', toggleZoom);
            // Add click handler
            img.addEventListener('click', toggleZoom);
        });
    }
    
    function toggleZoom(event) {
        event.preventDefault();
        this.classList.toggle('zoomed');
    }
    
    // Initial setup
    setupClickZoom();
    
    // Re-setup when navigation occurs (for Material's instant navigation)
    document.addEventListener('DOMContentLoaded', setupClickZoom);
    
    // Also handle Material for MkDocs instant navigation
    if (typeof document$ !== 'undefined') {
        document$.subscribe(setupClickZoom);
    }
});
