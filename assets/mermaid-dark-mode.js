/**
 * Configure Mermaid to use the appropriate theme based on Material for MkDocs color scheme.
 * Detects dark mode and applies corresponding Mermaid theme dynamically.
 */

(function() {
    'use strict';

    /**
     * Get the current color scheme from Material for MkDocs
     * @returns {string} 'slate' for dark mode, 'default' for light mode
     */
    function getCurrentScheme() {
        return document.querySelector('[data-md-color-scheme]')?.getAttribute('data-md-color-scheme') || 'default';
    }

    /**
     * Map Material theme to Mermaid theme
     * @param {string} scheme - Material color scheme ('default' or 'slate')
     * @returns {string} Mermaid theme name
     */
    function getMermaidTheme(scheme) {
        return scheme === 'slate' ? 'dark' : 'default';
    }

    /**
     * Watch for theme changes and update mermaid configuration
     */
    function watchThemeChanges() {
        const observer = new MutationObserver(() => {
            const scheme = getCurrentScheme();
            const theme = getMermaidTheme(scheme);

            // Update mermaid configuration if available
            if (window.mermaid && window.mermaid.initialize) {
                window.mermaid.initialize({
                    theme: theme,
                    startOnLoad: false
                });
            }
        });

        // Watch for changes to the html element's data-md-color-scheme attribute
        const target = document.documentElement;
        if (target) {
            observer.observe(target, {
                attributes: true,
                attributeFilter: ['data-md-color-scheme']
            });
        }
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', watchThemeChanges);
    } else {
        watchThemeChanges();
    }
})();
