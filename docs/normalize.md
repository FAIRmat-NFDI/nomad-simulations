# Normalization

## The `normalize()` function

Each base section defined using the NOMAD schema has a set of public functions which can be used at any moment when reading and parsing files in NOMAD. The `normalize(archive, logger)` function is a special case of such functions, which warrants an in-depth description.

This function is run within the NOMAD infrastructure by the [`MetainfoNormalizer`](https://github.com/nomad-coe/nomad/blob/develop/nomad/normalizing/metainfo.py) in the following order:

1. A child section's `normalize()` function is run before their/its parents' `normalize()` function.
2. For sibling sections, the `normalize()` function is executed from the smaller to the larger `normalizer_level` attribute. If `normalizer_level` is not set or if they are the same for two different sections, the order is established by the attributes definition order in the parent section.
3. Using `super().normalize(archive, logger)` runs the inherited section normalize function.

Let's see some examples. Imagine having the following `Section` and `SubSection` structure:

```python
from nomad.datamodel.data import ArchiveSection


class Section1(ArchiveSection):
    normalizer_level = 1

    def normalize(self, achive, logger):
        # some operations here
        pass


class Section2(ArchiveSection):
    normalizer_level = 0

    def normalize(self, archive, logger):
        super().normalize(archive, logger)
        # Some operations here or before `super().normalize(archive, logger)`


class ParentSection(ArchiveSection):

    sub_section_1 = SubSection(Section1.m_def, repeats=False)

    sub_section_2 = SubSection(Section2.m_def, repeats=True)

    def normalize(self, archive, logger):
        super().normalize(archive, logger)
        # Some operations here or before `super().normalize(archive, logger)`
```

Now, `MetainfoNormalizer` will be run on the `ParentSection`. Applying **rule 1**, the `normalize()` functions of the `ParentSection`'s childs are executed first. The order of these functions is established by **rule 2** with the `normalizer_level` atrribute, i.e., all the `Section2` (note that `sub_section_2` is a list of sections) `normalize()` functions are run first, then `Section1.normalize()`. Then, the order of execution will be:

1. `Section2.normalize()`
2. `Section1.normalize()`
3. `ParentSection.normalize()`

In case we do not assign a value to `Section1.normalizer_level` and `Section2.normalizer_level`, `Section1.normalize()` will run first before `Section2.normalize()`, due to the order of `SubSection` attributes in `ParentSection`. Thus the order will be in this case:

1. `Section1.normalize()`
2. `Section2.normalize()`
3. `ParentSection.normalize()`

By checking on the `normalize()` functions and **rule 3**, we can establish whether `ArchiveSection.normalize()` will be run or not. In `Section1.normalize()`, it will not, while in the other sections, `Section2` and `ParentSection`, it will.

### Logging Messages

The `normalize` interface accepts an optional `logger` variable, via which it can store _info_, _warning_, or _error_ messages. <!-- add link to other docs -->
When `logger` is left `None`, NOMAD will provide its own logger.
The advantage of providing your own `logger` comes from customization and labelling of code portions.

## Cross-referencing between Sections

Sections like `model_system` tend to follow a similar structure as `outputs`.
Our schema highlights this structure by providing references in each section to its counterpart.
These sections cannot be directly populated by the `MappingAnnotation` parsing technique, but should connected afterwards at the parsing or normalization level.

If the schema allows for a reference, NOMAD will perform the conversion to and from its underlying section automatically.

### How To

- **between sections at the same level:** use `self.m_parent` to go one node up in the schema hierarchy. Then climb the schema ladder from any of the connecting sections using up till the first common node.
- **between repeating sections:** obtain any subsection's index via `self.m_parent_index`. If they are not `repeating`, the index defaults to `-1`.
