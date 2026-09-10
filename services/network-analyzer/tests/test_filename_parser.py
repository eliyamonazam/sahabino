import pytest
from analyzer.filename_parser import InvalidFilenameError, parse_filename


@pytest.mark.parametrize(
    "filename,expected_app_name,expected_scenario,expected_sequence",
    [
        ("baham_send_01.pcap", "baham", "send", "01"),
        ("pinno_receive_02.pcap", "pinno", "receive", "02"),
        ("baham_receive_01.pcap", "baham", "receive", "01"),
        # scenario matching is case-insensitive and normalized to lowercase
        ("baham_SEND_01.pcap", "baham", "send", "01"),
        # app names with underscores resolve from the right
        ("my_app_name_send_10.pcap", "my_app_name", "send", "10"),
    ],
)
def test_parse_filename_valid(filename, expected_app_name, expected_scenario, expected_sequence):
    parsed = parse_filename(filename)

    assert parsed.app_name == expected_app_name
    assert parsed.scenario == expected_scenario
    assert parsed.sequence == expected_sequence


@pytest.mark.parametrize(
    "filename",
    [
        "baham_send.pcap",  # missing sequence number
        "baham_download_01.pcap",  # invalid scenario
        "baham_send_01.pcapng",  # wrong extension
        "baham_send_01",  # no extension
        "send_01.pcap",  # missing app name
        "baham_send_aa.pcap",  # non-numeric sequence
    ],
)
def test_parse_filename_invalid_raises(filename):
    with pytest.raises(InvalidFilenameError):
        parse_filename(filename)
