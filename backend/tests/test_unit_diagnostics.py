from backend.app.services import portal
from datetime import date


def test_unknown_unit_details_are_available_without_raw_record():
    row = {"se_cd": "02", "ctgry_cd": "200", "item_cd": "211", "vrty_cd": "03",
           "grd_cd": "04", "sgg_cd": "1101", "item_nm": "배추", "vrty_nm": "가을",
           "sgg_nm": "서울", "exmn_ymd": "20261027", "exmn_dd_avg_prc": "1234",
           "unit": "포기", "unit_sz": "1", "private_unrelated_field": "TEST_ONLY_PRIVATE"}
    series, quality = portal.normalize([row], date(2026, 10, 1), date(2026, 10, 27), "1101", "03", "04")
    assert series == []
    assert quality["unit_samples"] == [{"unit": "포기", "unit_size": "1"}]
    message = portal.empty_message(quality)
    assert "단위=포기 / 단위크기=1" in message
    assert "1234" not in message and "PRIVATE" not in message


def test_unusual_or_long_unit_values_are_not_echoed():
    assert portal.unit_label("TEST_ONLY_SENTINEL_" * 8) == "(단위 표기 확인 필요)"
    assert portal.unit_label("https://example.invalid/?secret=TEST_ONLY") == "(단위 표기 확인 필요)"
    assert portal.unit_label(None) == "(없음)"
    assert portal.unit_label("10kg(그물망)") == "10kg(그물망)"
