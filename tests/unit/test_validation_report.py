from cellforge.validation import ValidationReport


def test_report_distinguishes_warnings_from_errors() -> None:
    report = ValidationReport(dataset="fixture")
    report.add_warning("known_limitation", "A documented limitation")
    assert report.valid

    report.add_error("invalid_data", "An invalid field")
    assert not report.valid
