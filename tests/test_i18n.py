from __future__ import annotations

from pomodoro_app.i18n import Translator, _


class TestTranslator:
    """Tests for Translator singleton and switch_language()."""

    def setup_method(self) -> None:
        # Reset singleton before each test
        Translator._inst = None

    def test_setup_and_translate(self) -> None:
        Translator.setup("zh")
        assert _("集中精力") == "集中精力"
        assert _("nonexistent_key") == "nonexistent_key"

    def test_switch_to_english(self) -> None:
        Translator.setup("zh")
        assert _("集中精力") == "集中精力"

        Translator.switch_language("en")
        assert _("集中精力") == "Focus"

    def test_switch_to_japanese(self) -> None:
        Translator.setup("zh")
        Translator.switch_language("ja")
        assert _("集中精力") == "集中"
        assert _("终止时钟") == "停止"

    def test_switch_to_russian(self) -> None:
        Translator.setup("zh")
        Translator.switch_language("ru")
        assert _("集中精力") == "Фокус"

    def test_switch_to_french(self) -> None:
        Translator.setup("zh")
        Translator.switch_language("fr")
        assert _("集中精力") == "Concentration"

    def test_switch_to_german(self) -> None:
        Translator.setup("zh")
        Translator.switch_language("de")
        assert _("集中精力") == "Fokus"

    def test_switch_back_to_chinese(self) -> None:
        Translator.setup("en")
        assert _("集中精力") == "Focus"
        Translator.switch_language("zh")
        assert _("集中精力") == "集中精力"

    def test_switch_nonexistent_language_falls_back_to_key(self) -> None:
        Translator.setup("zh")
        Translator.switch_language("xx")
        assert _("集中精力") == "集中精力"  # key returned when no translation file

    def test_switch_language_property_updates(self) -> None:
        Translator.setup("zh")
        assert Translator.instance().language == "zh"
        Translator.switch_language("en")
        assert Translator.instance().language == "en"

    def test_switch_when_not_setup_yet(self) -> None:
        Translator._inst = None
        Translator.switch_language("en")
        assert Translator.instance().language == "en"
        assert _("集中精力") == "Focus"

    def test_translate_all_common_keys(self) -> None:
        """Verify common keys exist in both zh and en."""
        Translator.setup("en")
        en_strings = {k: v for k, v in _load_all("en")}
        Translator.setup("zh")
        zh_strings = {k: v for k, v in _load_all("zh")}

        common_keys = set(en_strings) & set(zh_strings)
        assert len(common_keys) > 60, "Most keys should be shared between zh and en"


def _load_all(lang: str) -> list[tuple[str, str]]:
    import json
    from pathlib import Path

    path = Path(__file__).parent.parent / "pomodoro_app" / "i18n" / f"{lang}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data.items())
