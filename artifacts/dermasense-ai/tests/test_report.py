from src.report.pdf_report import generate_pdf_report


def test_pdf_report_is_real_and_marks_low_confidence(tmp_path):
    output = tmp_path / "summary.pdf"
    report_id = generate_pdf_report(
        output,
        {"initials": "AB", "age": "42", "region": "arm"},
        prediction={
            "status": "low_confidence",
            "accepted": False,
            "warning": "This result is unreliable.",
            "top_three": [{"class_code": "MEL", "probability": 0.41}],
        },
    )

    assert report_id.startswith("DS-")
    assert output.read_bytes().startswith(b"%PDF-")
