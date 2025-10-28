import os
import shutil

from nomad import datamodel, utils
from nomad.files import StagingUploadFiles, UploadFiles


# TODO remove this only a temporary fix: function not included in package
def create_test_upload_files(
    upload_id: str | None,
    archives: list[datamodel.EntryArchive] | None = None,
    published: bool = True,
    embargo_length: int = 0,
    raw_files: str = None,
    template_files: str = '',
    template_mainfile: str = '',
    additional_files_path: str = None,
) -> UploadFiles:
    """
    Creates an upload_files object and the underlying files for test/mock purposes.

    Arguments:
        upload_id: The upload id for the upload. Will generate a random UUID if None.
        archives: A list of class:`datamodel.EntryArchive` metainfo objects. This will
            be used to determine the mainfiles. Will create respective directories and
            copy the template entry to create raw files for each archive.
            Will also be used to fill the archives in the create upload.
        published: Creates a :class:`PublicUploadFiles` object with published files
            instead of a :class:`StagingUploadFiles` object with staging files. Default
            is published.
        embargo_length: The embargo length
        raw_files: A directory path. All files here will be copied into the raw files
            dir of the created upload files.
        template_files: A zip file with example files in it. One directory will be used
            as a template. It will be copied for each given archive.
        template_mainfile: Path of the template mainfile within the given template_files.
        additional_files_path: Path to additional files to add.
    """
    if upload_id is None:
        upload_id = utils.create_uuid()
    if archives is None:
        archives = []

    upload_files = StagingUploadFiles(upload_id, create=True)
    if raw_files:
        shutil.rmtree(upload_files._raw_dir.os_path)
        shutil.copytree(raw_files, upload_files._raw_dir.os_path)
    if template_files:
        upload_files.add_rawfiles(template_files)
    if additional_files_path:
        upload_files.add_rawfiles(additional_files_path)

    for archive in archives:
        mainfile = archive.metadata.mainfile
        assert mainfile is not None, (
            'Archives to create test upload must have a mainfile'
        )
        # create an archive "file" for each archive
        entry_id = archive.metadata.entry_id
        assert entry_id is not None, (
            'Archives to create test upload must have an entry_id'
        )
        upload_files.write_archive(entry_id, archive.m_to_dict())

    if published:
        upload_files.pack(
            [archive.metadata for archive in archives], with_embargo=embargo_length > 0
        )
        upload_files.delete()
        return UploadFiles.get(upload_id)

    return upload_files
