from __future__ import annotations


def build_relation_legend(
    *, has_inherit: bool, has_contain: bool, has_refs: bool
) -> list[str]:
    """Return HTML legend items that visually track Mermaid relationship arrows."""
    items: list[str] = []

    if has_inherit:
        items.append(
            '<div class="uml-legend__item" role="listitem">'
            '<svg class="uml-legend__swatch" viewBox="0 0 64 16" aria-hidden="true">'
            '<line class="uml-legend__line" x1="50" y1="8" x2="22" y2="8"/>'
            '<path class="uml-legend__head uml-legend__head--filled" d="M22 8 L32 3 L32 13 Z"/>'
            '</svg>'
            '<span><code>Parent &lt;|-- Child</code> is-a relationship, Parent-Child inheritance</span>'
            '</div>'
        )

    if has_contain:
        items.append(
            '<div class="uml-legend__item" role="listitem">'
            '<svg class="uml-legend__swatch" viewBox="0 0 64 16" aria-hidden="true">'
            '<line class="uml-legend__line" x1="8" y1="8" x2="40" y2="8"/>'
            '<path class="uml-legend__head uml-legend__head--open" d="M40 8 L48 4 M40 8 L48 12"/>'
            '</svg>'
            '<span><code>Owner --&gt; SubSection</code> has-a relationship, Owner-SubSection composition</span>'
            '</div>'
        )

    if has_refs:
        items.append(
            '<div class="uml-legend__item" role="listitem">'
            '<svg class="uml-legend__swatch" viewBox="0 0 64 16" aria-hidden="true">'
            '<line class="uml-legend__line uml-legend__line--dashed" x1="8" y1="8" x2="40" y2="8"/>'
            '<path class="uml-legend__head uml-legend__head--open" d="M40 8 L48 4 M40 8 L48 12"/>'
            '</svg>'
            '<span><code>A ..&gt; B</code> references relationship, A depends on B</span>'
            '</div>'
        )

    return items


def wrap_diagram_card(
    diagram_lines: list[str], legend_items: list[str] | None = None
) -> list[str]:
    """Wrap Mermaid markdown and an optional HTML legend in one visual card."""
    lines = ['<div class="uml-diagram-card" markdown="1">', '']
    lines.extend(diagram_lines)

    if legend_items:
        lines.extend(
            [
                '',
                '<p class="uml-legend__title">Legend</p>',
                '<div class="uml-legend" role="list" aria-label="Diagram relationship legend">',
            ]
        )
        lines.extend(legend_items)
        lines.append('</div>')

    lines.extend(['', '</div>'])
    return lines
