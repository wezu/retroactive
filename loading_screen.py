from contextlib import contextmanager
from panda3d.core import *
from direct.gui.OnscreenImage import OnscreenImage

@contextmanager
def loading(*args):
    '''A context manager that shows a loading screen'''
    x=base.win.get_x_size()//2
    y=base.win.get_y_size()//2
    if y<350:
        img=loader.load_texture('img/loading_512.png')
        scale=(256, 0, 256)#img size//2
    else:
        img=loader.load_texture('img/loading_1024.png')
        scale=(512, 0, 512)#img size//2
    load_screen = OnscreenImage(image = img, scale=scale, pos = (x, 0, -y), parent=pixel2d)
    load_screen.set_transparency(TransparencyAttrib.M_alpha)
    #render 3 frames because we may be in a threaded rendering pipeline
    #we render frames to make sure the load screen is shown
    base.graphicsEngine.renderFrame()
    base.graphicsEngine.renderFrame()
    base.graphicsEngine.renderFrame()
    try:
        yield
    finally:
        for i in range(8):
            base.graphicsEngine.renderFrame()
        load_screen.remove_node()
