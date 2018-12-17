from panda3d.core import *
import random

class Vfx:
    def __init__(self, texture, loop=False, fps=15.0, frame_size=128):
        tex=loader.load_texture(texture)
        tex.set_magfilter(SamplerState.FT_linear_mipmap_linear )
        tex.set_minfilter(SamplerState.FT_linear_mipmap_linear)
        num_frames= (tex.get_x_size()//frame_size)*(tex.get_y_size()//frame_size)

        self.node=self._make_point()
        shader=Shader.load(Shader.SLGLSL, 'shaders/vfx_v.glsl','shaders/vfx_f.glsl')
        shader_attrib = ShaderAttrib.make(shader)
        shader_attrib = shader_attrib.set_flag(ShaderAttrib.F_shader_point_size, True)
        self.node.set_attrib(shader_attrib)
        self.node.set_transparency(TransparencyAttrib.M_alpha, 1)
        self.node.set_depth_test(False)
        self.scale=PointerToArrayFloat()
        self.scale.push_back(1.0)
        self.node.set_shader_input('scale', self.scale)
        self.node.set_shader_input('tex', tex)
        self.node.set_shader_input('config', Vec3(frame_size, fps, globalClock.get_frame_time()))
        self.node.set_shader_input('screen_size', Vec2(*base.get_size()))

        self.cleanup=[]

        if not loop:
            taskMgr.doMethodLater(num_frames/fps, self.remove,'auto_destruct')

    def setScale(self, *args):
        self.set_scale(*args)

    def set_scale(self, scale):
        self.scale.set_element(0, scale)

    def get_scale(self):
        return self.scale.get_element(0)

    def __getattr__(self,attr):
        return self.node.__getattribute__(attr)

    def remove(self, task=None):
        self.remove_node(task)

    def remove_node(self, task=None):
        for cmd in self.cleanup:
            cmd()
        self.node.remove_node()
        self=None

    def _make_point(self, num_points=1):
        aformat = GeomVertexArrayFormat("vertex", 1, GeomEnums.NT_uint8, GeomEnums.C_other)
        format = GeomVertexFormat.register_format(GeomVertexFormat(aformat))
        vdata = GeomVertexData('abc', format, GeomEnums.UH_static)
        vdata.set_num_rows(num_points)
        geom = Geom(vdata)
        p = GeomPoints(Geom.UH_static)
        #p.add_vertex(0)
        p.addNextVertices(num_points)
        geom.add_primitive(p)
        geom.set_bounds(OmniBoundingVolume())
        geom_node = GeomNode('point')
        geom_node.add_geom(geom)
        return render.attach_new_node(geom_node)
