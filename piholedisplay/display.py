from PIL import Image


class EpaperDisplay:
    def __init__(self):
        from .lib import epd2in13b

        self.epd = epd2in13b.EPD()
        self.awake = False

    def show(self, canvas, inverted):
        if not self.awake:
            self.epd.init()
            self.awake = True
        rotation = Image.ROTATE_270 if inverted else Image.ROTATE_90
        self.epd.display_frame(
            self.epd.get_frame_buffer(canvas.black.transpose(rotation)),
            self.epd.get_frame_buffer(canvas.red.transpose(rotation)),
        )
        self.epd.sleep()
        self.awake = False


class PngDisplay:
    def __init__(self, path, scale=4):
        self.path = path
        self.scale = scale

    def show(self, canvas, inverted):
        canvas.to_rgb(self.scale).save(self.path)
