import numpy as np; import ctypes
import pyglet; import pyglet.gl as gl

def drawArray(someArray):

    vertPoints = someArray[:,:2].flatten().astype(ctypes.c_float)
    print(someArray[:,:2].T.flatten(order = 'F'))
    print(someArray[:,:2].T)
    vertices_gl = vertPoints.ctypes.data_as(ctypes.POINTER(ctypes.c_float))

    color_array = np.ones((5,3))*np.array([1,0,1])
    vertColors = color_array.astype(ctypes.c_float)
    colors_gl = vertColors.ctypes.data_as(ctypes.POINTER(ctypes.c_float))

    gl.glVertexPointer(2, gl.GL_FLOAT, 0, vertices_gl)
    gl.glColorPointer(3,  gl.GL_FLOAT, 0, colors_gl)
    gl.glDrawArrays(gl.GL_LINE_STRIP, 0, len(vertPoints) // 2)

config = pyglet.gl.Config(sample_buffers=1, samples=4)
window = pyglet.window.Window(400,400, config = config)

@window.event
def on_draw():
    window.clear()
    gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
    gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
    gl.glEnableClientState(gl.GL_COLOR_ARRAY)

    points = np.random.random((5,5))*np.array([400,400,1,1,1])

    drawArray(points)

pyglet.app.run()