"""Parses the `{app_name}_{scenario}_{NN}.pcap` filename convention used for
manually captured pcap files (e.g. `baham_send_01.pcap`).
"""

import re
from dataclasses import dataclass

# app_name may itself contain underscores; scenario and the trailing sequence
# number are anchored from the right so that ambiguity resolves in its favor.
_FILENAME_RE = re.compile(
    r"^(?P<app_name>.+)_(?P<scenario>send|receive)_(?P<sequence>\d+)\.pcap$", re.IGNORECASE
)


class InvalidFilenameError(ValueError):
    """Raised when a filename doesn't match the {app_name}_{scenario}_{NN}.pcap convention."""


@dataclass(frozen=True)
class ParsedFilename:
    app_name: str
    scenario: str
    sequence: str


def parse_filename(filename: str) -> ParsedFilename:
    match = _FILENAME_RE.match(filename)
    if match is None:
        raise InvalidFilenameError(
            f"Filename {filename!r} doesn't match the '{{app_name}}_{{send|receive}}_{{NN}}.pcap' convention"
        )
    return ParsedFilename(
        app_name=match.group("app_name"),
        scenario=match.group("scenario").lower(),
        sequence=match.group("sequence"),
    )
