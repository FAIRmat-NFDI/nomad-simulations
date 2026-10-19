/**
 * Interactive SVG Pan/Zoom for Diagrams
 * Uses svg-pan-zoom library for smooth pan and zoom interactions
 */

document.addEventListener('DOMContentLoaded', function() {
    // Function to initialize SVG pan/zoom on all diagram SVGs
    function initSvgPanZoom() {
        // Check if svg-pan-zoom library is loaded
        if (typeof svgPanZoom === 'undefined') {
            console.warn('svg-pan-zoom library not loaded');
            return;
        }
        
        const svgEmbeds = document.querySelectorAll('.interactive-svg');
        
        svgEmbeds.forEach(function(embedElement) {
            // Skip if already initialized
            if (embedElement.svgPanZoomInstance) return;
            
            // Wait for embed to load
            embedElement.addEventListener('load', function() {
                try {
                    // Get the SVG document from embed
                    const svgDoc = embedElement.getSVGDocument ? embedElement.getSVGDocument() : 
                                   embedElement.contentDocument;
                    
                    if (!svgDoc) {
                        console.warn('Could not access SVG document');
                        return;
                    }
                    
                    const svg = svgDoc.querySelector('svg') || svgDoc.documentElement;
                    if (!svg) {
                        console.warn('SVG element not found');
                        return;
                    }
                    
                    // Initialize svg-pan-zoom
                    const panZoomInstance = svgPanZoom(svg, {
                        zoomEnabled: true,
                        controlIconsEnabled: true,
                        fit: true,
                        center: true,
                        minZoom: 0.5,
                        maxZoom: 10,
                        zoomScaleSensitivity: 0.3,
                        dblClickZoomEnabled: true,
                        mouseWheelZoomEnabled: true,
                        preventMouseEventsDefault: true,
                    });
                    
                    // Store instance for potential later use
                    embedElement.svgPanZoomInstance = panZoomInstance;
                    
                    // Mark container as interacted on first pan/zoom
                    const container = embedElement.closest('.diagram-container');
                    if (container) {
                        svg.addEventListener('mousedown', function() {
                            container.classList.add('interacted');
                        }, { once: true });
                    }
                    
                    console.log('SVG pan/zoom initialized for:', container ? container.dataset.diagram : 'diagram');
                    
                } catch (e) {
                    console.error('Error initializing SVG pan/zoom:', e);
                }
            });
            
            // Trigger load if already loaded
            if (embedElement.getSVGDocument || embedElement.contentDocument) {
                embedElement.dispatchEvent(new Event('load'));
            }
        });
    }
    
    // Initial setup
    setTimeout(initSvgPanZoom, 100);
    
    // Re-initialize on Material for MkDocs instant navigation
    if (typeof document$ !== 'undefined') {
        document$.subscribe(function() {
            setTimeout(initSvgPanZoom, 200);
        });
    }
});
