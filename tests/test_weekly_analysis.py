from ai_portfolio_watchtower.weekly_analysis import format_weekly_brief


def test_format_weekly_brief_converts_sections_to_bullets() -> None:
    raw = """
    Executive readout: No fresh buy signals appeared this week.

    Fresh portfolio decisions this period:
    None.

    Watchlist candidates, not buy recommendations:
    - AVGO appeared in multiple portfolio updates.
    MU was mentioned as a performance contributor.
    """

    formatted = format_weekly_brief(raw)

    assert "*Executive readout*" in formatted
    assert "- No fresh buy signals appeared this week." in formatted
    assert "*Fresh portfolio decisions this period*" in formatted
    assert "- None." in formatted
    assert "- AVGO appeared in multiple portfolio updates." in formatted
    assert "- MU was mentioned as a performance contributor." in formatted


def test_format_weekly_brief_removes_duplicate_bullet_symbols() -> None:
    formatted = format_weekly_brief(
        """
        *Executive readout*
        • AVGO appeared in multiple portfolio updates.
        """
    )

    assert "- AVGO appeared in multiple portfolio updates." in formatted
    assert "- •" not in formatted
