# Electronic States: Migration and Technical Notes

This page is developer-focused and complements the user-facing
`Electronic States` explanation page.

## Migration from Earlier Schema Versions

Earlier versions of the schema allowed direct assignment of
`SphericalSymmetryState` lists to a field called `orbitals_state` on
`AtomsState`. This pattern is deprecated. The modern approach requires
wrapping those states in an `ElectronicState` container and assigning to
the `electronic_state` field instead. Parsers and analysis code using the
old pattern must update to the new hierarchy.

The symbol-to-number conversion also requires attention during migration.
Code that previously set `l_quantum_symbol='p'` must change to
`l_quantum_number=1`. The symbol properties now serve only as read-only
accessors for display and verification purposes. Any logic depending on
symbols should be revised to work with quantum numbers directly.

Array-based quantum number access also breaks with recent changes. Code
indexing into `j_quantum_number[0]` fails because the field is now scalar.
Simply remove the indexing operation to access the value directly.
Similarly, `mj_quantum_number` changed from variable-length array to
scalar, eliminating the need to iterate over multiple `mj` values for a
single state.

## Technical Considerations

The quantization axis for `ml` symbols currently assumes a default
Cartesian coordinate frame. The symbols `x`, `y`, `z` for p-orbitals or
`xy`, `xz` for d-orbitals imply specific alignments with coordinate axes.
In magnetic field or crystal field contexts, this axis should align with
the field direction or principal crystal symmetry axes. Future development
will add an explicit `quantization_axis` quantity similar to the `axis`
field in `NonCollinearSpinState`, along with documentation clarifying that
`ml=0` corresponds to the z-direction while `ml=±1` span the xy-plane.

The coupling scheme methods like `_russell_saunders_j_values()` and
`_jj_coupling()` exist in the codebase but are not invoked during
normalization. These helper functions support future search and matching
operations where users might want to find all states compatible with
specific coupling schemes. Calling them requires explicit invocation in
analysis scripts rather than relying on automatic execution during data
ingestion.

Projection quantum numbers cannot exist independently of their parent
quantum numbers. While `j`, `l`, and `s` can be set independently when the
others are unknown or not applicable, `ml` requires `l` to be defined,
`mj` requires `j`, and `ms` requires `s`. This reflects the physical
reality that projections are meaningless without the corresponding total
angular momentum being specified first. Attempting to set only `ml`
without `l` will pass validation at construction but fail during
normalization with appropriate error messages.

## Further Information

The complete implementation resides in `atoms_state.py` within the
`nomad_simulations.schema_packages` module. Test cases in
`test_atoms_state.py` demonstrate construction patterns and validation
behavior.

Integration with the tight-binding model method appears in
`model_method.py`, where the `TB.resolve_orbital_references()` method
shows how to extract orbital information from model systems.

Property calculations reference electronic states through entity/orbital
reference fields (like `entity_ref` or `orbitals_state_ref`) that point to
`ElectronicState` instances. To access the parent `AtomsState`, use the
`get_parent_entity()` helper method. This Pattern A architecture eliminates
circular references while maintaining clean navigation through the
hierarchy.

Users encountering issues or seeking clarification should consult the
NOMAD forum at matsci.org, open issues on the GitHub repository, or refer
to the main NOMAD documentation for broader context on schema design
principles and the normalization system.
