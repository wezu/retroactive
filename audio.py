from panda3d.core import *
from direct.interval.MetaInterval import Sequence
from direct.interval.FunctionInterval import Func, Wait
from direct.interval.LerpInterval import LerpFunc

__all__ = ['Audio']

class Audio(object):
    def __init__(self, drop_off_factor=0.0, distance_factor=0.3):
        """This module handles music and sound playback."""
        self.music_manager=base.musicManager
        self.sound_manager=base.sfxManagerList[0]

        self.sound_manager.audio3dSetDropOffFactor(drop_off_factor)
        self.sound_manager.audio3dSetDistanceFactor(distance_factor)

        self.sfx=[]
        self.sounds={}
        self.current_music=None
        self.playlist=[]
        self.current_track= None

        #set volume
        self.set_music_volume(Config.getfloat('audio','music-volume'))
        self.set_sound_volume(Config.getfloat('audio','sound-volume'))

        taskMgr.add(self.update, 'audio_update_tsk')

    def load_sounds(self, sound_dict, positional=True):
        """Preload sounds for later playback"""
        for name, filename in sound_dict.items():
            self.sounds[name]=loader.load_sound(self.sound_manager, filename, positional)

    def set_music_volume(self, value):
        """Sets the music volume in 0.0-1.0 range"""
        self.music_manager.set_volume(value)
        Config.set('audio','music-volume', str(value))

    def set_sound_volume(self, value):
        """Sets the sound volume in 0.0-1.0 range"""
        self.sound_manager.set_volume(value)
        Config.set('audio','sound-volume', str(value))

    def next_track(self):
        """Jumps to the next music track(or the first if there is no next track)"""
        if self.current_track is None:
            return
        self.current_track+=1
        if self.current_track >= len(self.playlist):
            self.current_track=0
        self.current_music=self.playlist[self.current_track]
        self.track_seq=Sequence(Wait(self.current_music.length()), Func(self.next_track))
        self.track_seq.start()
        self.current_music.play()

    def load_music(self, track_names):
        """
        Loads music tracks from the track_names list
        """
        self.playlist=[]
        for track_name in track_names:
            self.playlist.append(loader.load_music(track_name))

        self.current_music=self.playlist[0]
        self.current_track=0

    def fade_out_music(self, duration=5.0):
        old_music_volume=self.music_manager.get_volume()
        Sequence(LerpFunc(self.music_manager.set_volume,
                         fromData=old_music_volume,
                         toData=0,
                         duration=duration),
                Func(self.stop_music),
                Func(self.music_manager.set_volume, old_music_volume)
                ).start()

    def play_music(self):
        """
        Starts playing music
        """
        self.track_seq=Sequence(Wait(self.current_music.length()), Func(self.next_track))
        self.track_seq.start()
        self.current_music.play()

    def stop_music(self):
        """Stops the music"""
        self.current_music.stop()
        self.current_track = None

    def stop_sound(self, sound):
        """Stops a sound"""
        sound.stop()

    def is_playing(self, sound):
        if sound is None:
            return False
        return sound.status() == sound.PLAYING

    def play_sound(self, sound, node=None, loop=False, pos=Vec3(0,0,0), vel=Vec3(0,0,0), rate=1.0):
        """
        Play a positional (3D) sound at node or pos location.
        If node is not None the sound will move with the node.
        """
        #print('playing ', sound, node)
        if sound in self.sounds:
            sfx=self.sounds[sound]
        else:
            sfx=loader.load_sound(self.sound_manager, sound, True)
        if node is not None:
            pos=node.get_pos(render)
        sfx.set3dAttributes(*pos, *vel)
        if loop:
            sfx.set_loop_count(0)
        sfx.set_play_rate(rate)
        sfx.play()
        self.sfx.append((sfx, node))
        return sfx

    def play_sound_2d(self, sound):
        """Plays the sound """
        if sound in self.sounds:
            sfx=self.sounds[sound]
        else:
            sfx=loader.load_sound(self.sound_manager, sound, False)
        sfx.play()
        self.sfx.append((sfx, None))
        return sfx

    def stop_all(self):
        """ Stops all currently playing sound effects (but not music!)"""
        for sfx, node in self.sfx:
            sfx.stop()

    def update(self, task):
        """Updates the position and velocity of currently playing sounds"""
        dt=globalClock.getDt()
        pos=base.camera.get_pos(render)
        forward=render.get_relative_vector(base.camera, Vec3.forward())
        up=render.get_relative_vector(base.camera, Vec3.up())
        vel=base.camera.get_pos_delta(render)/dt
        self.sound_manager.audio3dSetListenerAttributes(*pos, *vel, *forward, *up)

        for i, (sfx, node) in enumerate(self.sfx):
            if sfx.status()==sfx.PLAYING:
                if node is not None:
                    if node.is_empty():
                        sfx.stop()
                        #print('removing', self.sfx[i])
                        del self.sfx[i]
                    else:
                        pos=node.get_pos(render)
                        vel=node.get_pos_delta(render)/dt
                        sfx.set3dAttributes(*pos, *vel)
            else:
                #print('removing', self.sfx[i])
                del self.sfx[i]
        return task.cont
