from temporalio import activity

from nomad_simulations.actions.legacy_cleanup.models import CleanupSingleUploadInput

# Cap on the per-entry breakdown included in the result payload (the payload is
# persisted in the action record); aggregate stats always cover all entries.
MAX_REPORTED_ENTRIES = 200


@activity.defn
async def cleanup_upload(data: CleanupSingleUploadInput) -> dict:
    """
    Apply the legacy-`contributions` cleanup to every successful entry of one upload.

    Reads each entry archive, applies
    `nomad_simulations.schema_packages.utils.cleanup_archive`, and — unless
    `dry_run` — persists the changed archives and re-indexes the affected entries.
    Staging uploads are written directly; published uploads require
    `include_published` and are rewritten through the canonical staging round-trip
    (unpack, write, repack), the same mechanism NOMAD uses after reprocessing a
    published upload. The cleanup is idempotent, so activity retries after partial
    writes are safe.

    The activity guards per upload: the initiating user must be an admin or one of
    the upload's writers (the action-level ACL only controls who may start the
    action), and uploads with a running process are skipped. The guard is re-checked
    before writing, but the activity cannot take the processing lock, so a small
    race window with concurrently started processing remains.
    """
    from nomad import datamodel
    from nomad.archive import to_json
    from nomad.datamodel.datamodel import EntryArchive
    from nomad.files import StagingUploadFiles
    from nomad.processing.data import Upload
    from nomad.utils import get_logger

    from nomad_simulations.schema_packages.utils import (
        LegacyCleanupStats,
        cleanup_archive,
    )

    logger = get_logger(__name__, upload_id=data.upload_id)

    def result(status: str, **kwargs) -> dict:
        return {'upload_id': data.upload_id, 'status': status, **kwargs}

    upload = Upload.get(data.upload_id)

    user = datamodel.User.get(user_id=data.user_id)
    if not (user.is_admin or data.user_id in upload.writers):
        logger.warning('Cleanup requested by a user without write access; skipping.')
        return result('forbidden')

    if upload.process_running:
        return result('busy')

    published = bool(upload.published)
    write_allowed = not data.dry_run and (not published or data.include_published)

    totals = LegacyCleanupStats()
    changed_entries: list[dict] = []
    failures: list[dict] = []
    changed_archives: dict[str, dict] = {}
    n_scanned = 0
    n_changed = 0

    for entry in upload.successful_entries:
        n_scanned += 1
        try:
            with upload.upload_files.read_archive(entry.entry_id) as reader:
                archive_dict = to_json(reader[entry.entry_id])
            if 'data' not in archive_dict:
                continue
            entry_archive = EntryArchive.m_from_dict(
                archive_dict, m_context=upload.archive_context
            )
            stats = cleanup_archive(entry_archive, logger)
        except Exception as exc:
            failures.append({'entry_id': entry.entry_id, 'error': str(exc)})
            continue
        totals.merge(stats)
        if not stats.changed:
            continue
        n_changed += 1
        if len(changed_entries) < MAX_REPORTED_ENTRIES:
            changed_entries.append(
                {'entry_id': entry.entry_id, 'stats': stats.to_dict()}
            )
        if write_allowed:
            changed_archives[entry.entry_id] = entry_archive.m_to_dict(with_def_id=True)

    if data.dry_run:
        status = 'dry-run'
    elif published and not data.include_published:
        # changes were only reported; enable `include_published` to write them
        status = 'reported-only' if n_changed else 'clean'
    else:
        status = 'cleaned' if n_changed else 'clean'

    if changed_archives:
        # re-check right before writing (no processing lock available)
        upload = Upload.get(data.upload_id)
        if upload.process_running:
            return result('busy')

        if not published:
            for entry_id, archive_data in changed_archives.items():
                upload.upload_files.write_archive(entry_id, archive_data)
        else:
            # canonical published-upload rewrite: unpack to staging, write, repack
            # (mirrors the post-reprocess flow in nomad.processing.data)
            if StagingUploadFiles.exists_for(upload.upload_id):
                StagingUploadFiles(upload.upload_id).delete()
            staging = upload.upload_files.to_staging(create=True, include_archive=True)
            for entry_id, archive_data in changed_archives.items():
                staging.write_archive(entry_id, archive_data)
            staging.pack(
                upload.entries_mongo_metadata(),
                with_embargo=upload.with_embargo,
                create=False,
                include_raw=False,
            )
            staging.delete()
            # fresh handle: the cached upload_files predate the repack
            upload = Upload.get(data.upload_id)

        upload.cleanup_entries_batch(entry_ids=list(changed_archives), refresh=True)
        logger.info(
            'Rewrote and re-indexed entry archives after legacy cleanup.',
            n_entries=len(changed_archives),
        )

    return result(
        status,
        published=published,
        n_entries_scanned=n_scanned,
        n_entries_changed=n_changed,
        stats=totals.to_dict(),
        entries=changed_entries,
        failures=failures,
    )
