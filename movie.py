import moviepy.editor as mpe
import numpy as np

def stutter(tempo):
    return lambda t: int(tempo*t)/tempo

def luma(image):
    return np.apply_along_axis(
        lambda rgb: [0.2126*rgb[0] + 0.7152*rgb[1] + 0.0722*rgb[2]]*3,
        -1, image,
    )

tempo = 134/60 *3
def stutter_noise(gf, t):
    tt = int(tempo*t)/tempo
    s = int(tempo*t) % 3
    rng = np.random.default_rng(int(tt * 1000))
    f = gf(tt)
    return f * rng.random((*f.shape[:2], 1)) * s

v = mpe.VideoFileClip("/home/tom/Videos/sources/singing.mp4")
v=v.subclip(0,1.5)
v=v.fx(mpe.vfx.resize, height=100)
v=v.fl_image(luma)

v=v.fl(stutter_noise, keep_duration=True)
v.write_videofile("preview.mp4")
