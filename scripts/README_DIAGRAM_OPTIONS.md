# Diagram Viewing Options for Complex Schemas

This document outlines different approaches for viewing complex Mermaid diagrams in the documentation, comparing their trade-offs.

## Current Implementation: PNG with Click-to-Zoom

**Files:**
- `scripts/mermaid_to_png.py` - Converts Mermaid to PNG
- `docs/assets/click-zoom.js` - Simple click toggle zoom
- `docs/stylesheets/mermaid-zoom.css` - Click zoom styles

**How it works:**
- Mermaid diagrams converted to high-res PNG (2000px width, 2x scale)
- Simple CSS transform on click (scale 2x)
- White background overlay when zoomed

**Pros:**
- ✅ Simple implementation (no external libraries)
- ✅ Works everywhere (PNG is universally supported)
- ✅ No JavaScript complexity
- ✅ Fast loading
- ✅ Works offline once built

**Cons:**
- ❌ Limited zoom (only 2x)
- ❌ No pan capability
- ❌ Pixelation on high zoom
- ❌ Fixed resolution

**Best for:** Simple to medium complexity diagrams (methods, basis, system)

---

## Alternative 1: Interactive SVG with svg-pan-zoom Library

**Files:**
- `scripts/mermaid_to_svg.py` - Converts Mermaid to SVG
- `docs/assets/svg-pan-zoom-diagram.js` - Pan/zoom controller
- `docs/stylesheets/svg-diagram.css` - SVG container styles

**How it works:**
- Mermaid diagrams converted to SVG (vector format)
- SVG embedded in `<object>` tag
- [svg-pan-zoom](https://github.com/bumbu/svg-pan-zoom) library provides pan/zoom controls
- Infinite zoom quality (vectors)

**Setup:**
1. Add svg-pan-zoom library to `mkdocs.yml`:
   ```yaml
   extra_javascript:
     - 'https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js'
     - assets/svg-pan-zoom-diagram.js
   extra_css:
     - stylesheets/svg-diagram.css
   ```

2. Run SVG conversion:
   ```bash
   python scripts/gen_docs.py
   python scripts/mermaid_to_svg.py
   ```

**Pros:**
- ✅ Infinite zoom without quality loss (vector graphics)
- ✅ Pan and zoom with mouse wheel
- ✅ Built-in zoom controls (+/- buttons)
- ✅ Double-click to zoom in
- ✅ Reset button to fit view
- ✅ Smooth animations
- ✅ Mature, well-tested library (>4k GitHub stars)

**Cons:**
- ❌ Requires external JavaScript library (~13KB)
- ❌ More complex setup
- ❌ Needs `<object>` tag (can have CORS issues in some setups)
- ❌ Slightly more complex initialization

**Best for:** Complex diagrams (results, workflows, system with many relationships)

---

## Alternative 2: Fullscreen Modal with Pan/Zoom

**Concept:**
- Keep PNG for initial display
- Click opens fullscreen modal with SVG + pan/zoom
- Best of both worlds

**Implementation sketch:**
```javascript
// Click handler that opens fullscreen modal
document.querySelectorAll('.diagram-zoom-button').forEach(btn => {
    btn.addEventListener('click', function() {
        const svgUrl = this.dataset.svgUrl;
        openFullscreenDiagram(svgUrl);
    });
});

function openFullscreenDiagram(svgUrl) {
    // Create modal overlay
    // Load SVG
    // Initialize svg-pan-zoom
    // Add close button
}
```

**Pros:**
- ✅ Fast initial page load (PNG)
- ✅ Full pan/zoom when needed
- ✅ Fullscreen real estate for complex diagrams
- ✅ Familiar UX pattern (lightbox-style)

**Cons:**
- ❌ Requires both PNG and SVG versions
- ❌ More code complexity
- ❌ Modal UX might be disruptive

---

## Alternative 3: Separate Full-Page Diagram Views

**Concept:**
- Keep simple view in main docs
- Link to dedicated full-page diagram view with pan/zoom

**Implementation:**
- Create `docs/schema/results.diagram.md` with full-page SVG viewer
- Link from main page: "View interactive diagram →"

**Pros:**
- ✅ Doesn't clutter main documentation
- ✅ Full browser width/height for diagram
- ✅ Can have different zoom levels per diagram
- ✅ Easy to maintain

**Cons:**
- ❌ Extra navigation step
- ❌ Leaves main page context

---

## Alternative 4: Native Browser Zoom (Simplest)

**Concept:**
- Export SVG directly in markdown
- Let browser's native zoom handle it (Ctrl/Cmd + scroll)

**Implementation:**
```markdown
![Diagram](diagram.svg)
```

**Pros:**
- ✅ Zero JavaScript
- ✅ Users already know how to use browser zoom
- ✅ SVG quality
- ✅ Simplest implementation

**Cons:**
- ❌ Zooms entire page, not just diagram
- ❌ No dedicated pan controls
- ❌ Can be awkward UX

---

## Recommendation

**For your use case (complex diagrams like Results & Provenance):**

I recommend **Option 1: SVG with svg-pan-zoom library** because:

1. **It's mature and reliable** - The library has been around since 2014, well-maintained
2. **Perfect for complex diagrams** - Your Results diagram (3968px wide) benefits from infinite zoom
3. **Good UX** - Mouse wheel zoom + drag to pan is intuitive
4. **Small overhead** - Only 13KB library, loaded once
5. **Non-breaking** - Can be added alongside current PNG implementation

### Migration Strategy (Non-Breaking)

You can have both implementations coexist:

1. **Keep PNG + click-zoom for simple diagrams** (methods, basis, etc.)
2. **Use SVG + pan-zoom only for complex diagrams** (results, system, spectroscopy)

Create a hybrid script that chooses based on diagram complexity:

```python
def should_use_svg(title: str, mermaid_code: str) -> bool:
    """Determine if diagram should use SVG viewer instead of PNG."""
    # Use SVG for specific complex diagrams
    complex_diagrams = ['results', 'system', 'spectroscopy']
    
    if any(title.startswith(name) for name in complex_diagrams):
        return True
    
    # Or base on node count
    node_count = len(re.findall(r'class \w+', mermaid_code))
    return node_count > 15  # Threshold for "complex"
```

Would you like me to create this hybrid implementation?
