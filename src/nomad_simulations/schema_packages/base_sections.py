from nomad.datamodel.data import ArchiveSection
from nomad.metainfo import Quantity, Reference


class ModelBaseSection(ArchiveSection):
    """
    Base class for the model sections.
    Toggles the display name and adds a definition status.
    """

    name = Quantity(
        type=str,
        description="""
        Display name of the model within the archive.
        """,
    )

    iri = Quantity(
        type=str,
        shape=['*'],
        description="""
        The International Resource Identifier (IRI) of the model.
        Can be used to link definitions from curated vocabularies or ontologies.
        Use `http` or `https` specifier for active hyperlinks.
        """,  # ? TODO: impose the format of the IRI
    )

    normalized_from = Quantity(
        type=Reference(ArchiveSection), # ? repeating possible
        description="""
        Denotes any section that was used to normalize this section.
        """,
    )

    def name_from_section(self) -> str:
        """Return the name of the section based on the class name."""
        return ''.join(['_' + c.lower() if c.isupper() else c for c in self.__class__.__name__]).lstrip('_')  # ! d_o_s
    

    @property
    def plotly_legend_group(self) -> str:
        """Return the legend group for the plotly figure."""
        pass
    

    def normalize(self, *args, **kwargs) -> None:
        super().normalize(*args, **kwargs)
        if not self.name:
            self.name = self.name_from_section()
