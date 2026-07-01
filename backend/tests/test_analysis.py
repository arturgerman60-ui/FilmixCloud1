from app.analysis import analyze_report
from app.schemas import Direction, ThreatType


def test_analyze_report_extracts_threat_location_and_direction() -> None:
    result = analyze_report("Шахед через Миколаївщину курсом на північний захід")

    assert result.threat_type == ThreatType.SHAHED
    assert result.primary_location == "миколаївщина"
    assert result.coordinate is not None
    assert result.direction == Direction.NORTHWEST
    assert result.confidence >= 0.7


def test_analyze_report_keeps_unknown_low_confidence() -> None:
    result = analyze_report("Незрозуміле повідомлення без деталей")

    assert result.threat_type == ThreatType.UNKNOWN
    assert result.primary_location is None
    assert result.direction == Direction.UNKNOWN
    assert result.confidence < 0.4
    assert result.direction_uncertainty_deg == 180


def test_analyze_report_detects_recon_drone() -> None:
    result = analyze_report("Розвіддрон у Харкові, курс на південь")

    assert result.threat_type == ThreatType.RECON_DRONE
    assert result.primary_location in {"харків", "харьков"}
    assert result.direction == Direction.SOUTH
    assert 20 <= result.direction_uncertainty_deg <= 90
