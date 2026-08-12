"""Focused regression tests for BITTU's natural-language-first command palette."""
from __future__ import annotations

import asyncio
import shutil
import tempfile


def run_checks() -> int:
    from zedpy import commands as cmds

    palette_names = {command.name for command in cmds.PALETTE_COMMANDS}
    assert "/web" not in palette_names
    assert "/fetch" not in palette_names
    assert "/cost" not in palette_names
    assert "/model" in palette_names
    assert "/effort" in palette_names
    assert "/sessions" in palette_names
    assert "/checkpoint" in palette_names
    assert "/help" in palette_names

    assert [c.name for c in cmds.match("/mo", palette=True)] == ["/model", "/mode"]
    assert cmds.match("/web", palette=True) == []
    assert cmds.REGISTRY["/web"].handler is not None
    assert cmds.REGISTRY["/fetch"].handler is not None
    assert cmds.REGISTRY["/cost"].handler is not None

    async def tui_checks() -> None:
        from zedpy.config import Config
        from zedpy.tui.app import BittuApp

        workdir = tempfile.mkdtemp(prefix="bittu_palette_")
        cfg = Config.load()
        cfg.workdir = workdir
        app = BittuApp(cfg)
        try:
            async with app.run_test(size=(110, 40)) as pilot:
                await pilot.press("/")
                await pilot.pause()
                assert app._palette_matches
                palette_text = str(app.query_one("#palette").render())
                assert "WORKSPACE" in palette_text
                assert "EXECUTION" in palette_text
                assert "HISTORY" in palette_text
                assert "SETTINGS" in palette_text
                assert "/web" not in palette_text
                assert "/cost" not in palette_text

                await pilot.press("m", "o")
                await pilot.pause()
                assert [c.name for c in app._palette_matches] == ["/model", "/mode"]
                assert app._palette_query == "/mo"

                await pilot.press("tab")
                await pilot.pause()
                assert app.query_one("#prompt").value == "/model "
                assert not app._palette_matches

                app.query_one("#prompt").value = "/"
                await pilot.pause()
                await pilot.press("escape")
                await pilot.pause()
                assert not app._palette_matches
                assert app.query_one("#palette").styles.display == "none"
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    asyncio.run(tui_checks())
    print("palette regression checks: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_checks())
