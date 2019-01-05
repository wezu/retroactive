from collections import namedtuple
import builtins
import sys
import os
import random
from panda3d.core import *
from direct.gui.DirectGui import *
import configparser
Config = configparser.ConfigParser()
Config.read('config.ini')
builtins.Config = Config
#read all options as prc_file_data in case they have p3d meaning
for section in Config.sections():
    for option in Config.options(section):
        load_prc_file_data("", option +' '+Config.get(section, option))

from panda3d.bullet import *
from direct.showbase.DirectObject import DirectObject
load_prc_file_data('','textures-power-2 None')


from direct.showbase import ShowBase
from direct.filter.FilterManager import FilterManager

from direct.particles.Particles import Particles
from direct.particles.ParticleEffect import ParticleEffect
from direct.particles.ForceGroup import ForceGroup
from direct.gui.OnscreenImage import OnscreenImage
from direct.actor.Actor import Actor
from direct.interval.IntervalGlobal import *
import direct.particles.ParticleManagerGlobal

from vfx import Vfx
from audio import Audio
from projectile import Projectile
from loading_screen import loading

wp = WindowProperties.getDefault()
wp.set_title("Retro-Active by wezu")
wp.set_cursor_filename('img/cursor.cur')
wp.set_icon_filename('img/p3d.ico')
WindowProperties.setDefault(wp)

#this is used for ray tests return values
Hit = namedtuple('Hit', 'pos node')

class App(DirectObject):
    def __init__(self):
        builtins.game=self
        #basic setup
        base = ShowBase.ShowBase()
        base.enableParticles()
        base.accept('tab', base.bufferViewer.toggleEnable)
        lens=base.cam.node().get_lens()
        fov=lens.get_fov()
        lens.set_fov(fov*1.5)
        #print(lens.get_fov())
        lens.set_near_far(0.01, 500.0)
        base.set_background_color(0.0, 0.0, 0.0)
        base.disable_mouse()

        with loading():
            #GUI
            self.font = loader.loadFont('img/clock_font.ttf')
            self.font.setPixelsPerUnit(45)
            self.shield_parent=pixel2d.attach_new_node('shields')
            self.shields_frame = DirectFrame(frameSize=(-256, 0, 0, 256),
                                        frameColor=(1,1,1,1),
                                        frameTexture='img/ring.png',
                                        parent=self.shield_parent)
            self.shields_frame.set_pos(128,0,-128)
            self.shields_frame.flatten_light()
            self.shields_frame.set_transparency(TransparencyAttrib.M_alpha)

            self.shields_interval=LerpHprInterval(nodePath=self.shield_parent,
                                                  duration=10.0,
                                                  hpr=(0, 0, 360),
                                                  startHpr=(0,0,0))
            self.shields_interval.loop()
            self.shields_label=DirectLabel(text = '100%',
                                    frameColor=(0, 0, 0, 0),
                                    text_font=self.font,
                                    text_scale = 45,
                                    text_fg=(1,1,1,0.7),
                                    text_align=TextNode.ALeft,
                                    textMayChange=1,
                                    parent=pixel2d
                                    )
            self.shields_label.set_pos(0,0,-50)
            self.shield_parent.hide()
            self.shields_label.hide()

            #bullet setup
            self.world_np = render.attach_new_node('World')
            #the bullet world
            self.world = BulletWorld()
            self.world.set_gravity(Vec3(0, 0, -9.81))


            '''# debug
            self.debugNP = self.world_np.attachNewNode(BulletDebugNode('Debug'))
            self.debugNP.show()
            self.debugNP.node().showWireframe(True)
            self.debugNP.node().showConstraints(True)
            self.debugNP.node().showBoundingBoxes(False)
            self.debugNP.node().showNormals(True)

            self.world = BulletWorld()
            self.world.setGravity(Vec3(0, 0, -9.81))
            self.world.setDebugNode(self.debugNP.node())'''

            #fade to black card
            cm = CardMaker("black-quad")
            cm.set_frame((2, -2, 2, -2))
            self.fade_quad = NodePath(cm.generate())
            color=base.get_background_color()
            self.fade_quad.set_color(color[0],color[1],color[2],1)
            self.fade_quad.reparent_to(aspect2d)
            self.fade_quad.set_transparency(TransparencyAttrib.M_alpha)
            self.fade_quad.set_bin("fixed", 10)

            #collision masks
            wall =1
            monster=2
            player=3
            weapon=4

            #bit masks used for collisions
            #this grew over time, maybe it's no good?
            Masks = namedtuple('Masks', 'wall monster player weapon')
            self.bit_mask=Masks(*(BitMask32() for i in range(4)))
            self.bit_mask.wall.set_bit(wall)
            self.bit_mask.monster.set_bit(monster)
            self.bit_mask.player.set_bit(player)
            self.bit_mask.weapon.set_bit(weapon)

            #player collision sphere
            self.pc_collision = self.world_np.attach_new_node(BulletRigidBodyNode('player'))
            shape=BulletSphereShape(0.3)
            shape.set_margin(0.0)
            self.pc_collision.node().add_shape(shape)
            #self.pc_collision.node().set_kinematic(True)
            self.pc_collision.node().set_deactivation_enabled(False)
            self.pc_collision.node().set_deactivation_time(100000.0)
            self.pc_collision.set_collide_mask(self.bit_mask.player)
            self.world.attach_rigid_body(self.pc_collision.node())

            #load the map
            self.map_model=loader.load_model('models/map_fix1')
            self.map_model.reparent_to(render)
            self.map_model.set_shader(Shader.load(Shader.SLGLSL, 'shaders/line_v.glsl','shaders/line_f.glsl'),1)
            self.map_model.set_shader_input('color', Vec4(0.49, 0.83, 0.43, 1.0))
            #make collisions from the map model
            self.map_body = self.world_np.attach_new_node(BulletRigidBodyNode('map'))
            for body in BulletHelper.from_collision_solids(self.map_model, True):
                for shape in body.node().get_shapes():
                    shape.set_margin(0.0)
                    self.map_body.node().add_shape(shape)
            self.map_body.node().set_mass(0)
            self.map_body.set_collide_mask(self.bit_mask.wall)
            self.world.attach_rigid_body(self.map_body.node())


            self.text=loader.load_model('models/text')
            self.text.reparent_to(render)
            self.text.set_color(0.49, 0.83, 0.43, 1.0)
            self.text.hide()

            self.start_text=loader.load_model('models/start_text')
            self.start_text.reparent_to(render)
            self.start_text.set_color(0.49, 0.83, 0.43, 1.0)

            self.plane=loader.load_model('models/plane')
            self.plane.reparent_to(render)
            self.plane.set_color(0.49, 0.83, 0.43, 1.0)
            #self.plane.set_scale(5.0)
            self.plane.set_z(0.2)
            #self.plane.hide()

            #load enemies
            self.monster_dummys=Actor('models/monster_dummy',
                                      {'anim':'models/monster_anim'}  )
            self.monster_dummys.reparent_to(render)
            self.monster_dummys.set_blend(frameBlend = True)
            self.monster_dummys.set_play_rate(0.55, 'anim')
            self.monster_dummys.node().set_bounds(OmniBoundingVolume())
            self.monster_dummys.node().set_final(True)
            #print(self.monster_dummys.listJoints())
            self.monster_joints=[]
            self.monsters=[]
            for joint in self.monster_dummys.getJoints():
                name=joint.get_name()
                exposed_joint=self.monster_dummys.expose_joint(None, 'modelRoot', name)
                self.monster_joints.append(exposed_joint)

                collison = self.world_np.attach_new_node(BulletRigidBodyNode('monster'))
                shape=BulletSphereShape(0.3)
                shape.set_margin(0.0)
                collison.node().add_shape(shape)
                #collison.node().set_kinematic(True)
                collison.node().set_deactivation_enabled(False)
                collison.node().set_deactivation_time(100000.0)
                collison.set_pos(exposed_joint.get_pos(render))
                collison.set_collide_mask(self.bit_mask.monster)
                self.world.attach_rigid_body(collison.node())
                collison.set_python_tag('hp', 4)

                model=loader.load_model('models/shape'+random.choice(['1','2','3','4a','4']))
                model.set_h(180)
                model.flatten_strong()
                model.reparent_to(collison)
                model.set_scale(0.01)
                model.hide()
                collison.set_python_tag('model', model)
                self.monsters.append(collison)



            #setup post-processing
            manager = FilterManager(base.win, base.cam)
            #the textures need to be clamped
            base_tex = Texture()
            base_tex.set_wrap_u(SamplerState.WM_clamp)
            base_tex.set_wrap_v(SamplerState.WM_clamp)
            bloom_tex = Texture()
            bloom_tex.set_wrap_u(SamplerState.WM_clamp)
            bloom_tex.set_wrap_v(SamplerState.WM_clamp)
            chroma_tex= Texture()
            chroma_tex.set_wrap_u(SamplerState.WM_clamp)
            chroma_tex.set_wrap_v(SamplerState.WM_clamp)
            blur_x_tex = Texture()
            blur_x_tex.set_wrap_u(SamplerState.WM_clamp)
            blur_x_tex.set_wrap_v(SamplerState.WM_clamp)
            blur_tex = Texture()
            blur_tex.set_wrap_u(SamplerState.WM_clamp)
            blur_tex.set_wrap_v(SamplerState.WM_clamp)
            final_quad = manager.renderSceneInto(colortex=base_tex)

            # step #1a - bur base_tex->blur_x_tex
            blur_x_quad = manager.renderQuadInto(colortex=blur_x_tex, div=2 )
            blur_x_quad.set_shader(Shader.load(Shader.SLGLSL, 'shaders/blur13_v.glsl','shaders/blur13_f.glsl'))
            blur_x_quad.set_shader_input("input_tex", base_tex)
            blur_x_quad.set_shader_input("mode", Vec2(1.0, 0.0))
            blur_x_quad.set_shader_input("size", Vec2(1280//2,720//2))
            # 1b step - bur blur_x_tex->blur_tex
            blur_quad = manager.renderQuadInto(colortex=blur_tex, div=2)
            blur_quad.set_shader(Shader.load(Shader.SLGLSL, 'shaders/blur13_v.glsl','shaders/blur13_f.glsl'))
            blur_quad.set_shader_input("input_tex", blur_x_tex)
            blur_quad.set_shader_input("mode", Vec2(0.0, 1.0))
            blur_quad.set_shader_input("size", Vec2(1280//2,720//2))


            # step #2 bloom blur_tex->bloom_tex
            bloom_quad = manager.renderQuadInto(colortex=bloom_tex)
            bloom_quad.set_shader(Shader.load(Shader.SLGLSL, 'shaders/bloom_v.glsl','shaders/bloom_f.glsl'))
            bloom_quad.set_shader_input("blur_tex", blur_tex)
            bloom_quad.set_shader_input("base_tex", base_tex)

            #step #3 chromatic aberration and beat effect bloom_tex->chroma_tex
            chroma_quad = manager.renderQuadInto(colortex=chroma_tex)
            chroma_quad.set_shader(Shader.load(Shader.SLGLSL, 'shaders/chroma_v.glsl','shaders/chroma_f.glsl'))
            chroma_quad.set_shader_input("input_tex", bloom_tex)
            chroma_quad.set_shader_input('beat_tex', loader.load_texture('img/spectrogram_1x2048.png'))
            #we'll be updating this each frame,
            # so we need a pointer in order not to call
            #set_shader_input each frame
            self.beat_uv=Vec2F(0,0.5)
            self.pta_beat_uv=PTALVecBase2f()
            self.pta_beat_uv.push_back(self.beat_uv)
            chroma_quad.set_shader_input("beat_uv",self.pta_beat_uv)

            # Final -fxaa chroma_tex->screen
            final_quad.set_shader(Shader.load(Shader.SLGLSL, 'shaders/fxaa_v.glsl','shaders/fxaa_f.glsl'))
            final_quad.set_shader_input('pre_aa', chroma_tex)
            final_quad.set_shader_input('subpix_shift', 1.0/4.0)
            final_quad.set_shader_input('span_max', 8.0)
            final_quad.set_shader_input('reduce_mul', 1.0/8.0)
            final_quad.set_shader_input('reduce_min', 1.0/128.0)

            #the camera motion is an actor...
            self.pilot= Actor('models/pilot',
                           {'flyby':'models/fly_bank_2'})
            self.pilot.reparent_to(render)
            self.pilot.set_blend(frameBlend = True)
            self.pilot.set_play_rate(0.55, 'flyby')
            #self.pilot.loop('flyby')
            self.pilot.node().set_bounds(OmniBoundingVolume())
            self.pilot.node().set_final(True)
            self.pilot.hide()

            self.bone = self.pilot.expose_joint(None, 'modelRoot', 'Bone002')
            #base.camera.reparent_to(self.bone)
            #base.camera.set_h(-90)


            #self.particle_np  = render.attach_new_node("particleNode")
            #self.particle_np.setLightOff()
            self.air_dust = ParticleEffect()
            self.air_dust.loadConfig('vfx/dust.ptf')
            for geom in self.air_dust.findAllMatches('**/+GeomNode'):
                geom.set_light_off()
            #self.air_dust.start(parent=base.camera, renderParent = render)


            #preload textures
            t=loader.load_texture('vfx/plasm2.png')
            t2=loader.load_texture('vfx/spark_explode.png')
            t3=loader.load_texture('vfx/explode_red.png')
            t4=loader.load_texture('vfx/plasm.png')
            t5=loader.load_texture('vfx/red_spark_explode.png')

            #load sounds
            self.audio=Audio()
            sounds={}
            for filename in os.listdir('sfx'):
                sounds[filename[:-4]]='sfx/'+filename
            self.audio.load_sounds(sounds)

            #load music
            self.audio.load_music(('music/synthwave.ogg',))
            #self.audio.set_music_volume(0.5)



        self.splash=self.make_splash('img/warning.png')
        self.splash.set_transparency(TransparencyAttrib.M_alpha)
        base.buttonThrowers[0].node().setButtonDownEvent('buttonDown')
        self.accept('buttonDown', self.remove_splash)

        self.player_hp=100
        self.vis_tsk_timer=0
        self.screen_shake=0
        self.shake_tilt=0

        self.text_hide_seq=Sequence()
        self.game_over_seq=Sequence()
        self.is_game_over=False


    def game_over(self):
        if self.is_game_over:
            return
        self.shield_parent.hide()
        self.shields_label.hide()
        self.pilot.pose('flyby', 0)
        self.is_game_over=True
        self.game_over_seq.finish()
        #print('game over')
        pos=base.camera.get_pos(render)
        hpr=base.camera.get_hpr(render)
        base.camera.reparent_to(render)
        base.camera.set_pos(pos)
        base.camera.set_hpr(hpr)

        self.plane.set_z(-4.0)
        self.plane.show()
        Sequence(Wait(6.0), LerpPosInterval(self.plane,5.0,(0, 0, 0.2))).start()
        Sequence(Wait(8.0), Func(self.audio.fade_out_music)).start()
        for monster in self.monsters:
            monster.get_python_tag('model').hide()
        self.ignore('mouse1')
        s=Sequence(Wait(0.2),
                   LerpPosHprInterval(nodePath=base.camera,
                                   duration=2.0,
                                   pos=(pos.x, pos.y, 9.0),
                                   hpr=(90, -90, -180),
                                   startHpr=hpr),
                   LerpPosInterval(nodePath=base.camera,
                                   duration=6.0,
                                   pos=Point3(0, 0, 20.0)),
                   LerpPosInterval(nodePath=base.camera,
                                   duration=5.0,
                                   pos=Point3(-3.5, 1, 109.5)),
                   Func(self.show_start)
                   )
        s.start()

    def on_monster_hit(self, hit_node, hit_pos, projectile):
        hit_vfx=Vfx('vfx/red_spark_explode.png', False, 60, 256)
        hit_vfx.set_scale(1.5)
        hit_vfx.set_pos(hit_pos)
        #print('monster hit', hit_node)
        if hit_node.get_name()=='player':
            self.audio.play_sound('laser_hit3', node=None, pos=hit_pos)
            self.player_hp-=3.3
            self.shields_label['text']='{:03.0f}%'.format(self.player_hp)
            self.screen_shake+=10
            #print('player hp:', self.player_hp)
            if self.player_hp<0:
                self.game_over()
        #else:
        #    self.audio.play_sound('laser_hit4', node=None, pos=hit_pos)
        projectile.remove()

    def test_visibility(self, task):
        if self.is_game_over:
            return task.done
        if self.vis_tsk_timer<10.0:
            self.vis_tsk_timer+=task.delayTime
            return task.again
        from_point=base.camera.get_pos(render)
        for monster in self.monsters:
            to_point=monster.get_pos(render)
            hit=self.ray_test(from_point, to_point)
            if hit.node:
                if hit.node.get_name()=='monster':
                    hp=hit.node.get_python_tag('hp')
                    if hp >0:
                        vis=Vfx('vfx/plasm.png', loop=True, fps=60.0, frame_size=128)
                        vis.set_pos(monster.get_pos(render))
                        target=render.get_relative_point(base.camera, (0, 1.8, 0))
                        vis.look_at(target)
                        vis.set_scale(0.15)
                        Projectile(visual=vis,
                                   size=0.15,
                                   pos=vis.get_pos(render),
                                   hpr=vis.get_hpr(render),
                                   speed=15.0,
                                   mask=self.bit_mask.player|self.bit_mask.weapon|self.bit_mask.wall,
                                   on_hit_cmd=self.on_monster_hit)
        return task.again


    def fade_screen(self, time=1.5, color=(0,0,0)):
        '''Turns the screen to 'color' then fades the color away in 'time' seconds'''
        startColor=self.fade_quad.get_color()
        if startColor[3] == 0.0:
            Sequence(
            Func(self.fade_quad.show),
            LerpColorInterval(nodePath=self.fade_quad, duration=time, color=(color[0],color[1],color[2],1), startColor=startColor),
            ).start()
        else:
            Sequence(
            Func(self.fade_quad.show),
            Wait(time*0.1),
            LerpColorInterval(nodePath=self.fade_quad, duration=time*0.9, color=(color[0],color[1],color[2],0), startColor=startColor, blendType = 'easeIn'),
            Func(self.fade_quad.hide),
            ).start()


    def fire(self):
        hit=self.mouse_ray_test(self.bit_mask.weapon)
        self.audio.play_sound_2d('laser_shot')
        if hit:
            vis=Vfx('vfx/plasm2.png', loop=True, fps=60.0, frame_size=128)
            vis.set_pos(base.camera.get_pos(render))
            vis.look_at(hit.pos)
            vis.set_scale(0.15)
            Projectile(visual=vis,
                       size=0.1,
                       pos=vis.get_pos(render),
                       hpr=vis.get_hpr(render),
                       speed=25.0,
                       mask=self.bit_mask.weapon|self.bit_mask.monster|self.bit_mask.wall,
                       on_hit_cmd=self.on_hit)

        #else:
        #    print('zonk')

    def explode(self, pos):
        hit_vfx=Vfx('vfx/explode_red.png', False, 30, 256)
        hit_vfx.set_scale(2.0)
        hit_vfx.set_pos(pos)

    def on_hit(self, hit_node, hit_pos, projectile):
        if hit_node:
            hit_vfx=Vfx('vfx/spark_explode.png', False, 60, 256)
            hit_vfx.set_scale(1.5)
            #hit_vfx.set_pos(hit_pos)
            hit_vfx.set_pos(projectile.visual.get_pos(render))
            self.audio.play_sound('laser_hit2', node=None, pos=hit_pos)
            if hit_node.get_name()=='monster':
                hp=hit_node.get_python_tag('hp')-1
                hit_node.set_python_tag('hp', hp)
                if hp <0:
                    hit_node.get_python_tag('model').hide()
                    np=NodePath().any_path(hit_node)
                    np.set_collide_mask(BitMask32().all_off())
                    self.explode(np.get_pos(render))

        projectile.remove()

    def mouse_ray_test(self, mask=None):
        """Find the first object (and point) under the mouse cursor """
        if base.mouseWatcherNode.has_mouse():
            m_pos=base.mouseWatcherNode.getMouse()
            from_point = Point3()
            to_point = Point3()
            base.camLens.extrude(m_pos, from_point, to_point)
            # Transform to global coordinates
            from_point = render.get_relative_point(base.cam, from_point)
            to_point = render.get_relative_point(base.cam, to_point)
            return self.ray_test(from_point, to_point, mask)
        return None

    def ray_test(self, from_point, to_point, mask=None):
        """Find the first object (and point) on the from_point-to_point line """
        if mask is None:
            result= self.world.ray_test_closest(from_point, to_point)
        else:
            result= self.world.ray_test_closest(from_point, to_point, mask)
        if result.has_hit():
            return Hit(result.get_hit_pos(), result.get_node())
        else:
            return Hit(from_point, None)

    def show_start(self):
        self.air_dust.disable()
        self.text.hide()
        self.start_text.show()
        self.plane.show()
        base.camera.reparent_to(render)
        base.camera.set_pos(-3.5, 1, 109.5)
        base.camera.set_hpr(90, -90, -180)
        try:
            taskMgr.remove(self.sync_task)
        except:
            pass
        self.beat_uv.x=0
        self.pta_beat_uv[0]=self.beat_uv
        s=Sequence(Func(self.fade_screen, 0.5), Wait(0.55), Func(self.start_game))
        self.accept('mouse1', s.start)



    def start_game(self):
        self.fade_screen(0.5)
        self.player_hp=100
        self.shield_parent.show()
        self.shields_label.show()
        self.shields_label['text']='{:03.0f}%'.format(self.player_hp)
        self.is_game_over=False
        self.text_hide_seq.finish()
        self.text_hide_seq=Sequence(Wait(15.0), Func(self.text.hide))
        self.text_hide_seq.start()
        self.game_over_seq=Sequence(Wait(146.0), Func(self.game_over))
        self.game_over_seq.start()
        self.plane.hide()
        self.text.show()
        self.start_text.hide()
        for monster in self.monsters:
            monster.get_python_tag('model').show()
            monster.set_python_tag('hp', 4)
            monster.set_collide_mask(self.bit_mask.monster)


        #base.camera.set_pos(37.7574, -40.4733, 0 )
        base.camera.set_pos(0, 0, 0 )
        base.camera.reparent_to(self.bone)
        base.camera.set_hpr(-90, 0, 0)
        self.pilot.play('flyby')
        self.monster_dummys.play('anim')
        self.air_dust.start(parent=base.camera, renderParent = render)
        self.audio.play_music()
        self.sync_task=taskMgr.add(self.sync, 'sync')
        self.vis_tsk_timer=0
        taskMgr.doMethodLater(1.0, self.test_visibility, 'visibility_tsk')
        self.ignore('mouse1')
        self.accept('mouse1', self.fire)

    def make_splash(self, img_path):
        x=base.win.get_x_size()//2
        y=base.win.get_y_size()//2
        img=loader.load_texture(img_path)
        scale=(256, 0, 256)#img size//2
        return OnscreenImage(image = img, scale=scale, pos = (x, 0, -y), parent=pixel2d)

    def remove_splash(self, key_event=None):
        '''Removes the splash screen'''
        self.splash.hide()
        self.fade_screen(0.5, base.get_background_color())
        self.ignore('buttonDown')
        self.show_start()


    def sync(self, task):
        dt=globalClock.get_dt()
        self.world.do_physics(dt)

        self.pc_collision.set_pos(base.camera.get_pos(render))
        for joint, monster in zip(self.monster_joints,self.monsters):
            hp=monster.get_python_tag('hp')
            if hp>0:
                pos=joint.get_pos(render)
                hpr=joint.get_hpr(render)
                monster.set_pos_hpr(pos, hpr)

        if self.screen_shake>0:
            r=random.uniform(-1.0, 1.0)
            self.shake_tilt+=r
            base.cam.set_r(base.cam.get_r()+r)
            self.screen_shake-=1
        elif self.screen_shake == 0:
            self.screen_shake-=1
            base.cam.set_r(base.cam.get_r()-self.shake_tilt)
            self.shake_tilt=0

        self.beat_uv.x+=dt*1.0/173.95
        if self.beat_uv.x>1.0:
            self.beat_uv.x=0
            self.pta_beat_uv[0]=self.beat_uv
            return task.done
        self.pta_beat_uv[0]=self.beat_uv
        return task.again


#Run it
app=App()
base.run()

