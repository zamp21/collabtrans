import types

from collabtrans.translator.ai_translator.docx_translator import extract_run_format, RunFormatInfo


class _DummyFont:
    """Dummy font object to simulate python-docx font with problematic highlight_color."""

    def __init__(self, raise_on_highlight: bool = False):
        self.name = None
        self.size = None
        self.bold = None
        self.italic = None
        self.underline = None
        self.color = None
        self.strike = None
        self._raise_on_highlight = raise_on_highlight

    @property
    def highlight_color(self):
        if self._raise_on_highlight:
            # Simulate python-docx ValueError for unsupported highlight value 'none'
            raise ValueError("WD_COLOR_INDEX has no XML mapping for 'none'")
        return None


class _DummyRun:
    """Dummy run object with a .font attribute."""

    def __init__(self, font):
        self.font = font
        self.text = "dummy"


def test_extract_run_format_ignores_unsupported_highlight_none():
    """
    When the underlying font.highlight_color access raises
    'WD_COLOR_INDEX has no XML mapping for 'none'',
    extract_run_format should swallow this error and set highlight_color to None.
    """
    dummy_font = _DummyFont(raise_on_highlight=True)
    dummy_run = _DummyRun(dummy_font)

    info: RunFormatInfo = extract_run_format(dummy_run)

    assert isinstance(info, RunFormatInfo)
    # The key behavior: we should not crash, and highlight_color should be None
    assert info.highlight_color is None

