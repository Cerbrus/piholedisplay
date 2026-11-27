from pathlib import Path

from PIL import Image

from piholedisplay.canvas import HEIGHT, WIDTH
from piholedisplay.demo import SCREEN_SCALE, demo_frames, icons_markdown, write_demo
from piholedisplay.icons import ICONS

ROOT = Path(__file__).parent.parent


def test_icon_documentation_is_up_to_date():
    assert (ROOT / 'docs' / 'icons.md').read_text(encoding='utf-8') == icons_markdown()


def test_every_icon_has_a_committed_picture():
    assert {path.stem for path in (ROOT / 'docs' / 'icons').glob('*.png')} == set(ICONS)


def test_write_demo_creates_screens_icons_and_the_legend(tmp_path):
    write_demo(tmp_path)

    assert {path.stem for path in (tmp_path / 'screens').glob('*.png')} == set(demo_frames())
    assert {path.stem for path in (tmp_path / 'icons').glob('*.png')} == set(ICONS)
    assert (tmp_path / 'icons.md').read_text(encoding='utf-8') == icons_markdown()
    with Image.open(tmp_path / 'screens' / 'normal-1.png') as image:
        assert image.size == (WIDTH * SCREEN_SCALE, HEIGHT * SCREEN_SCALE)
