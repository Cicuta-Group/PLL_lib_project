import pyglet
import pyglet.gl as gl
import os
import numpy as np
import ctypes
from importlib.metadata import version
version = version('PLL_Lib')

border = 20

def probe_text(comp):
    return f'{comp}X probe compensation.'

no_probe_text = 'No probe compensation.'

ideal_grid = 80

grid_color = np.array([0.5, 0.5, 0.5])

label_exclusion_left = 90
label_exclusion_right = 40

chB_color = np.array([1, 0, 0])
chA_color = np.array([0, 0, 1])

trigger_size = 8

trigger_color = (236,240,5)

status_color = (236,240,5,255)

font_name = 'Ebrima'

captime_samples = 100


def get_spacing(min, max, screenspace, ideal):
    rnge = max - min
    base = 10 ** np.floor(np.log10(rnge))
    options = np.array([base / 4, base / 2, base, base * 2.5, base * 5])
    screenspaces = screenspace * options / rnge
    best_base = options[np.argmin(np.abs(screenspaces - ideal))]
    if min == 0:
        return np.arange(0, max * 1.0001, best_base)
    return np.concatenate([np.arange(0, min * 1.0001, -best_base)[:0:-1],np.arange(0, max * 1.0001, best_base)])


class ScopeDisplay:
    def __init__(self, min_v, max_v, min_t, max_t, time_per_sample_text, no_samples, probe_comp, trigger_voltage,
                 trigger_time, width=1000,
                 height=500):
        self._waiting_key = None
        self.max_v, self.min_v = max_v, min_v
        self.max_t, self.min_t = max_t, min_t
        self.draw_width = width - 2 * border
        self.draw_height = height - 2 * border
        window = pyglet.window.Window(width=width, height=height)
        self.window = window
        self.points_x = np.array([])
        self.points_y_a, self.points_y_b = np.array([]), np.array([])
        self.setup_grid()
        self.labels = pyglet.graphics.Batch()
        pyglet.text.Label(f'PLL_Lib PycoScope version {version}. Press q to quit.',
                          font_name=font_name,
                          font_size=11,
                          x=border, y=window.height,
                          anchor_x='left', anchor_y='top', batch=self.labels)

        self.status_label = pyglet.text.Label('Status: ',
                          font_name=font_name,
                          font_size=12,
                          x=border, y=0, color=status_color,
                          anchor_x='left', anchor_y='bottom', batch=self.labels)

        pyglet.text.Label(
            f'{no_samples} samples with {time_per_sample_text} per sample. '.replace('micro_', 'μ')
            + (probe_text(probe_comp) if probe_comp != 1 else no_probe_text),
            font_name=font_name,
            font_size=12,
            x=border + self.draw_width, y=window.height,
            anchor_x='right', anchor_y='top', batch=self.labels)

        self.rate_label = pyglet.text.Label(''
                          + probe_text(probe_comp) if probe_comp != 1 else no_probe_text,
                          font_name=font_name,
                          font_size=12,
                          x=border + self.draw_width, y=0,
                          anchor_x='right', anchor_y='bottom', batch=self.labels)

        self.overflow_label = pyglet.text.Label('Warning: Channel Overrange',
                          font_name=font_name,
                          font_size=14,
                          x=border+5, y=border + self.draw_height, color=status_color,
                          anchor_x='left', anchor_y='top')

        self.rectA = pyglet.shapes.Rectangle(1.5 * border, 2.5 * border, 10, 10, chA_color * 255, batch=self.labels)
        pyglet.text.Label('Channel A',
                          font_name=font_name,
                          font_size=8,
                          x=1.5 * border + 15, y=2.5 * border + 5,
                          color=(255 * chA_color[0], 255 * chA_color[1], 255 * chA_color[2], 255),
                          anchor_x='left', anchor_y='center', batch=self.labels)
        self.rectB = pyglet.shapes.Rectangle(1.5 * border, 1.5 * border, 10, 10, chB_color * 255)
        pyglet.text.Label('Channel B',
                          font_name=font_name,
                          font_size=8,
                          x=1.5 * border + 15, y=1.5 * border + 5,
                          color=(255 * chB_color[0], 255 * chB_color[1], 255 * chB_color[2], 255),
                          anchor_x='left', anchor_y='center', batch=self.labels)
        self.trigger = None
        if trigger_voltage is not None:
            self.trigger = pyglet.graphics.Batch()
            trigger_x = border + (trigger_time - self.min_t)*self.draw_width/(self.max_t - self.min_t)
            trigger_y = border + (trigger_voltage - self.min_v)*self.draw_height/(self.max_v - self.min_v)
            self.trigger_rect = pyglet.shapes.Rectangle(trigger_x, trigger_y, trigger_size, trigger_size, color=trigger_color, batch=self.labels)
            self.trigger_rect.anchor_position = trigger_size//2, trigger_size//2
            self.trigger_rect.rotation = 45
        self.overflow = False
        self.captimes = []

        @self.window.event
        def on_draw():
            self.window.clear()
            gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
            gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
            gl.glEnableClientState(gl.GL_COLOR_ARRAY)
            self.draw_grid()
            self.draw_line(self.points_x, self.points_y_a, chA_color)
            self.draw_line(self.points_x, self.points_y_b, chB_color)
            self.draw_border()
            self.labels.draw()
            if self.trigger is not None: self.trigger_rect.draw()
            self.rectA.draw(),self.rectB.draw()
            if self.overflow: self.overflow_label.draw()

        @self.window.event
        def on_key_press(symbol, modifiers):
            if symbol == 113:  # q key
                print('q key pressed. Stopping...')
                os._exit(1)
            if self._waiting_key is not None:
                if symbol == self._waiting_key:
                    self._waiting_key = None
        self.set_status('Waiting for first capture...')
        self.update(np.array([]), np.array([]), np.array([]), None, False)
        self.update(np.array([]), np.array([]), np.array([]), None, False) # Have to do this twice the first time. Don't know why...

    def av_captime(self, captime):
        if len(self.captimes) == captime_samples:
            self.captimes.pop()
        self.captimes.insert(0,captime)
        return np.mean(self.captimes)

    def update(self, times, voltages_a, voltages_b, captime, overflow):
        pyglet.clock.tick()
        self.overflow = overflow
        if captime is not None and captime > 0: self.rate_label.text = f'Approx {np.round(1 / self.av_captime(captime), 1)} captures per second.'
        self.points_x = (times - self.min_t) * self.draw_width / (self.max_t - self.min_t) + border
        self.points_y_a = (voltages_a - self.min_v) * self.draw_height / (self.max_v - self.min_v) + border
        self.points_y_b = (voltages_b - self.min_v) * self.draw_height / (self.max_v - self.min_v) + border
        self.window.switch_to()
        self.window.dispatch_events()
        self.window.dispatch_event('on_draw')
        self.window.flip()

    def draw_line(self, points_x, points_y, color):
        vertPoints = np.stack([points_x, points_y]).flatten(order="F").astype(ctypes.c_float)
        vertices_gl = vertPoints.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
        color_array = np.ones((len(points_x), 3)) * color
        vertColors = color_array.flatten().astype(ctypes.c_float)
        colors_gl = vertColors.ctypes.data_as(ctypes.POINTER(ctypes.c_float))

        gl.glVertexPointer(2, gl.GL_FLOAT, 0, vertices_gl)
        gl.glColorPointer(3, gl.GL_FLOAT, 0, colors_gl)
        gl.glDrawArrays(gl.GL_LINE_STRIP, 0, len(vertPoints) // 2)

    def draw_border(self):
        self.draw_line(np.array([border, border + self.draw_width, border + self.draw_width, border, border]),
                       np.array([border, border, border + self.draw_height, border + self.draw_height, border]),
                       np.array([1, 1, 1]))

    def setup_grid(self):
        self.x_grid_spacing = get_spacing(self.min_t, self.max_t, self.draw_width, ideal_grid)
        self.x_grid_screen = self.draw_width * (self.x_grid_spacing - self.min_t) / (self.max_t - self.min_t) + border
        self.y_grid_spacing = get_spacing(self.min_v, self.max_v, self.draw_height, ideal_grid)
        self.y_grid_screen = self.draw_height * (self.y_grid_spacing - self.min_v) / (self.max_v - self.min_v) + border
        self.grid_labels = pyglet.graphics.Batch()
        for x, x_screen in zip(self.x_grid_spacing, self.x_grid_screen):
            if x_screen < label_exclusion_left or self.draw_width - x_screen < label_exclusion_right: continue
            pyglet.text.Label(f'{x:.1e}s',
                              font_name=font_name,
                              font_size=9,
                              x=x_screen + 3, y=2 * border,
                              anchor_x='left', anchor_y='top', batch=self.grid_labels)
        for y, y_screen in zip(self.y_grid_spacing[1:-1], self.y_grid_screen[1:-1]):
            pyglet.text.Label(f'{y:.1e}v',
                              font_name=font_name,
                              font_size=9,
                              x=2 * border, y=y_screen,
                              anchor_x='left', anchor_y='bottom', batch=self.grid_labels)

    def draw_grid(self):
        self.grid_labels.draw()
        for x_screen in self.x_grid_screen:
            self.draw_line(np.array([x_screen, x_screen]), np.array([border, border + self.draw_height]), grid_color)
        for y_screen in self.y_grid_screen:
            self.draw_line(np.array([border, border + self.draw_width]), np.array([y_screen, y_screen]), grid_color)

    def set_status(self, status):
        self.status_label.text = f'Status: {status}'

    def wait_for_keycode(self, keycode):
        self._waiting_key = keycode

    @property
    def done_waiting(self):
        return self._waiting_key is None

    def close(self):
        self.window.close()