import re

_BACKUP_ID_PATTERN = re.compile(r"dashboard-\d{8}T\d{6}Z-[0-9a-f]{8}\.sqlite3\.gz\Z")


def is_generated_backup_id(value: str) -> bool:
    return _BACKUP_ID_PATTERN.fullmatch(value) is not None
