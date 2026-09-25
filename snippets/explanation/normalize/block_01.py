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
