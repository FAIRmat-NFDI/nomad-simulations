function fixMermaidInheritanceMarkers(root = document) {
    const docStyle = getComputedStyle(document.documentElement);
    const edge =
        docStyle.getPropertyValue('--md-mermaid-edge-color').trim()
        || docStyle.getPropertyValue('--md-default-fg-color').trim()
        || '#000000';

    root.querySelectorAll('svg defs marker.marker.extension.class path').forEach((path) => {
        path.style.setProperty('fill', '#ffffff', 'important');
        path.style.setProperty('stroke', edge, 'important');
        path.style.setProperty('stroke-width', '1.8px', 'important');
    });
}

function watchMermaidInheritanceMarkers() {
    fixMermaidInheritanceMarkers();

    const observer = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
            for (const node of mutation.addedNodes) {
                if (!(node instanceof Element)) {
                    continue;
                }
                if (node.matches('svg, .mermaid, .panzoom-box')) {
                    fixMermaidInheritanceMarkers(node);
                } else if (node.querySelector('svg defs marker.marker.extension.class path')) {
                    fixMermaidInheritanceMarkers(node);
                }
            }
        }
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true,
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', watchMermaidInheritanceMarkers, {
        once: true,
    });
} else {
    watchMermaidInheritanceMarkers();
}
