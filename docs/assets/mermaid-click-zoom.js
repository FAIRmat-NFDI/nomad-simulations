// Simple click-to-zoom for Mermaid diagrams
// Based on the approach from fairmat-tutorial-14-computational-plugins

document.addEventListener('DOMContentLoaded', function() {
    // Wait for Mermaid to render, then wrap diagrams
    setTimeout(function() {
        wrapMermaidDiagrams();
    }, 500);
    
    // Re-initialize on navigation (Material for MkDocs instant loading)
    if (typeof document$ !== 'undefined') {
        document$.subscribe(function() {
            setTimeout(wrapMermaidDiagrams, 500);
        });
    }
});

function wrapMermaidDiagrams() {
    // Find all pre.mermaid elements
    const mermaidBlocks = document.querySelectorAll('pre.mermaid');
    
    mermaidBlocks.forEach(function(pre) {
        // Skip if already wrapped
        if (pre.closest('.click-zoom')) {
            return;
        }
        
        // Check if it has SVG (Mermaid has rendered)
        const svg = pre.querySelector('svg');
        if (!svg) {
            return;
        }
        
        // Create the click-zoom wrapper structure
        const wrapper = document.createElement('div');
        wrapper.className = 'click-zoom';
        
        const label = document.createElement('label');
        
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        
        // Extract and clone the SVG
        const svgClone = svg.cloneNode(true);
        
        // Build structure: wrapper > label > (checkbox + svg)
        label.appendChild(checkbox);
        label.appendChild(svgClone);
        wrapper.appendChild(label);
        
        // Replace the pre element with our wrapper
        pre.parentNode.replaceChild(wrapper, pre);
    });
}

