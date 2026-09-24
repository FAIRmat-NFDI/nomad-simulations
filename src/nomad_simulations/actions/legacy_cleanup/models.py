from pydantic import BaseModel, Field, field_validator


def parse_upload_id_list(value: str | list[str]) -> list[str]:
    """Parse upload IDs from either a Python list or comma-separated string.

    Args:
        value: Either a list of upload IDs or a comma-separated string

    Returns:
        List of upload ID strings with whitespace trimmed and empty strings filtered
    """
    if isinstance(value, str):
        return [
            upload_id.strip() for upload_id in value.split(',') if upload_id.strip()
        ]

    result = []
    for item in value:
        if isinstance(item, str):
            if not item.strip():
                continue
            result.extend(
                [
                    upload_id.strip()
                    for upload_id in item.split(',')
                    if upload_id.strip()
                ]
            )
        else:
            result.append(item)

    return result


class LegacyCleanupWorkflowInput(BaseModel):
    """Input model for cleaning legacy `ModelMethod.contributions` content."""

    upload_id: str | None = Field(
        default=None,
        description=(
            'Optional context upload the run is associated with. The GUI auto-fills '
            'it from the project when the action is launched there, so the run '
            'appears under that upload in the action history. Not a cleanup target.'
        ),
    )
    user_id: str = Field(
        ..., description='Unique identifier for the user who initiated the workflow.'
    )
    target_upload_ids: list[str] = Field(
        ...,
        description=(
            'List of upload identifiers to clean one by one. Can be provided as a '
            'Python list or comma-separated string.'
        ),
    )
    dry_run: bool = Field(
        default=True,
        description=(
            'Report what would change without writing any archive. Disable only '
            'after reviewing a dry run.'
        ),
    )
    include_published: bool = Field(
        default=False,
        description=(
            'Also rewrite published uploads (staging round-trip and repack of the '
            'public archive files). Off by default; published uploads are only '
            'reported.'
        ),
    )

    @field_validator('target_upload_ids', mode='before')
    @classmethod
    def validate_target_upload_ids(cls, v):
        """Parse target_upload_ids from either list or comma-separated string."""
        return parse_upload_id_list(v)


class CleanupSingleUploadInput(BaseModel):
    """Input model for cleaning a single upload."""

    upload_id: str = Field(..., description='Unique identifier for the upload.')
    user_id: str = Field(
        ..., description='Unique identifier for the user who initiated the workflow.'
    )
    dry_run: bool = Field(
        default=True, description='Report without writing any archive.'
    )
    include_published: bool = Field(
        default=False, description='Also rewrite published uploads.'
    )
