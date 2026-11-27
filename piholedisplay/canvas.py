from functools import cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .icons import ICONS

WIDTH = 212
HEIGHT = 104
FONTS = Path(__file__).parent / 'fonts'
RED = (200, 20, 20)
INK = 0
PAPER = 255


@cache
def font(size, bold=False):
    name = 'DejaVuSansMono-Bold.ttf' if bold else 'DejaVuSansMono.ttf'
    return ImageFont.truetype(str(FONTS / name), size, layout_engine=ImageFont.Layout.BASIC)


def text_width(message, size=10, bold=False):
    return font(size, bold).getlength(message)


class Canvas:
    def __init__(self, width=WIDTH, height=HEIGHT):
        self.width = width
        self.height = height
        self.black = Image.new('1', (width, height), PAPER)
        self.red = Image.new('1', (width, height), PAPER)
        self.draw = {'black': ImageDraw.Draw(self.black), 'red': ImageDraw.Draw(self.red)}

    def text(self, x, y, message, color='black', size=10, bold=False, align='left', fill=INK):
        if align == 'right':
            x -= text_width(message, size, bold)
        self.draw[color].text((x, y), message, font=font(size, bold), fill=fill)

    def icon(self, x, y, name, color='black', fill=INK):
        for row, line in enumerate(ICONS[name].rows):
            for column, pixel in enumerate(line):
                if pixel == '#':
                    self.draw[color].point((x + column, y + row), fill=fill)

    def line(self, start, end, color='black'):
        self.draw[color].line((*start, *end), fill=INK)

    def box(self, box, color='black', fill=INK):
        self.draw[color].rectangle(box, fill=fill)

    def clear(self, box):
        for draw in self.draw.values():
            draw.rectangle(box, fill=PAPER)

    def to_rgb(self, scale=1):
        image = Image.new('RGB', (self.width, self.height), (255, 255, 255))
        image.paste((0, 0, 0), mask=self.black.point(lambda value: 255 - value))
        image.paste(RED, mask=self.red.point(lambda value: 255 - value))
        return image.resize((self.width * scale, self.height * scale), Image.NEAREST)
