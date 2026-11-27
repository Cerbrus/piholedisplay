from dataclasses import replace

import pytest

from piholedisplay import screen
from piholedisplay.canvas import HEIGHT, WIDTH, text_width
from piholedisplay.demo import demo_frames, demo_pihole, demo_system
from piholedisplay.icons import ICONS, SIZE
from piholedisplay.model import Frame

FRAMES = demo_frames()


def ink(image, box):
    left, top, right, bottom = box
    pixels = image.load()
    return sum(1 for x in range(left, right) for y in range(top, bottom) if pixels[x, y] == 0)


@pytest.mark.parametrize('name', FRAMES)
def test_every_demo_frame_renders_at_display_size(name):
    canvas = screen.render(FRAMES[name])

    assert canvas.black.size == canvas.red.size == (WIDTH, HEIGHT)
    assert ink(canvas.black, (0, 0, WIDTH, HEIGHT))
    assert ink(canvas.red, (0, 0, WIDTH, HEIGHT))


def test_black_and_red_never_share_a_pixel():
    for frame in FRAMES.values():
        canvas = screen.render(frame)
        black, red = canvas.black.load(), canvas.red.load()

        assert not any(black[x, y] == 0 and red[x, y] == 0 for x in range(WIDTH) for y in range(HEIGHT))


def test_frame_without_pihole_data_still_renders():
    canvas = screen.render(Frame(system=demo_system(), refreshed=FRAMES['normal-1'].refreshed))

    assert ink(canvas.black, (0, 0, WIDTH, HEIGHT))


def test_overlay_covers_the_middle_of_the_chart():
    box = (60, screen.OVERLAY_TOP + 1, 150, screen.OVERLAY_BOTTOM)
    plain, stopped = screen.render(FRAMES['normal-1']), screen.render(FRAMES['stopped'])

    assert ink(stopped.red, box) > ink(plain.red, box)
    assert ink(stopped.black, box) == 0


def test_markers_are_red_and_sit_left_of_the_divider():
    box = (60, 39, screen.DIVIDER_X, 50)

    assert ink(screen.render(FRAMES['normal-1']).red, box) == 0
    assert ink(screen.render(FRAMES['markers']).red, box)


def test_lone_marker_sits_against_the_divider():
    slot = (screen.DIVIDER_X - 11, 39, screen.DIVIDER_X, 50)
    warning_only = replace(FRAMES['normal-1'], pihole=demo_pihole(messages=2))
    voltage_only = replace(FRAMES['normal-1'], system=demo_system(under_voltage=True))

    assert ink(screen.render(warning_only).red, slot)
    assert ink(screen.render(voltage_only).red, slot)


def test_alternate_frame_changes_only_the_lower_grid_rows():
    first, second = screen.render(FRAMES['normal-1']), screen.render(FRAMES['normal-2'])
    upper = (screen.GRID_LEFT, 0, WIDTH, 24)
    lower = (screen.GRID_LEFT, 25, WIDTH, 49)

    assert first.black.crop(upper).tobytes() == second.black.crop(upper).tobytes()
    assert first.black.crop(lower).tobytes() != second.black.crop(lower).tobytes()


def test_chart_columns_use_whole_buckets_from_the_end():
    history = tuple((index, 1) for index in range(145))

    columns, per_column = screen.chart_columns(history, 69)

    assert per_column == 2
    assert len(columns) == 69
    assert columns[-1] == (143 + 144, 2)
    assert columns[0] == (7 + 8, 2)


def test_chart_columns_with_short_or_empty_history():
    assert screen.chart_columns((), 69) == ([], 0)
    assert screen.chart_columns(((5, 1), (7, 2)), 69) == ([(5, 1), (7, 2)], 1)


def test_number_formats():
    assert screen.thousands(12431) == '12.431'
    assert screen.compact(1243118) == '1.24M'
    assert screen.compact(853210) == '853k'
    assert screen.compact(9500) == '9.500'
    assert screen.blocked_share(18.44) == '18.4%'
    assert screen.blocked_share(100.0) == '100%'
    assert screen.percent(None) == '-'


def test_durations():
    assert screen.duration(12 * 86400 + 4 * 3600 + 59) == '12d 4h'
    assert screen.duration(4 * 3600 + 12 * 60) == '4h 12m'
    assert screen.duration(125) == '2m'
    assert screen.duration(None) == '-'


def test_phrase_fit_depends_on_the_blocked_count():
    assert screen.phrase_fits(12431, 'Yeeted')
    assert not screen.phrase_fits(1234567, 'Banhammered')


@pytest.mark.parametrize(('size', 'bold', 'advance'), [(8, False, 5), (9, False, 5), (10, False, 6), (9, True, 5), (24, True, 14)])
def test_font_advances_are_whole_pixels_on_every_platform(size, bold, advance):
    assert text_width('0' * 10, size, bold) == advance * 10


def test_icons_are_square_bitmaps_with_a_meaning():
    for name, icon in ICONS.items():
        assert icon.meaning, name
        assert len(icon.rows) == SIZE, name
        assert all(len(row) == SIZE and set(row) <= {'#', '.'} for row in icon.rows), name
