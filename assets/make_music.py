import numpy as np, wave, struct

SR = 44100

def note_freq(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)

def piano_tone(freq, dur, vel=0.5, sr=SR):
    t = np.arange(int(dur * sr)) / sr
    # soft felt-piano-ish: fundamental + harmonics with decay
    env = np.exp(-t * 2.2) * (1 - np.exp(-t * 400))
    s = (np.sin(2*np.pi*freq*t) * 1.0
         + np.sin(2*np.pi*freq*2*t) * 0.35 * np.exp(-t*4)
         + np.sin(2*np.pi*freq*3*t) * 0.12 * np.exp(-t*6)
         + np.sin(2*np.pi*freq*1.003*t) * 0.4)  # gentle detune warmth
    return s * env * vel

def add(buf, start, sig):
    i = int(start * SR)
    j = min(len(buf), i + len(sig))
    if j > i:
        buf[i:j] += sig[:j-i]

# Autumn Leaves progression in Em: Am7 D7 Gmaj7 Cmaj7 F#m7b5 B7 Em9 Em9
chords = [
    [57, 60, 64, 67],   # Am7
    [50, 54, 57, 60],   # D7
    [55, 59, 62, 66],   # Gmaj7
    [48, 52, 55, 59],   # Cmaj7
    [54, 57, 60, 64],   # F#m7b5
    [47, 51, 54, 57],   # B7
    [52, 55, 59, 62],   # Em7
    [52, 55, 59, 64],   # Em9
]
bass = [45, 38, 43, 36, 42, 35, 40, 40]
melody = [76, 74, 71, 72, 69, 66, 67, 71]  # gentle top line

beat = 60 / 76          # 76 BPM
bar = beat * 2          # 2 beats per chord
total = bar * len(chords) + 3
buf = np.zeros(int(total * SR))

rng = np.random.default_rng(7)
for k, ch in enumerate(chords):
    t0 = k * bar
    # bass
    add(buf, t0, piano_tone(note_freq(bass[k]), bar*1.6, 0.40))
    # soft arpeggio
    for n, m in enumerate(ch):
        add(buf, t0 + n * beat * 0.24 + rng.uniform(0, 0.02),
            piano_tone(note_freq(m), bar*1.5, 0.30 - n*0.03))
    # melody note, slightly late, airy
    add(buf, t0 + beat * 0.55, piano_tone(note_freq(melody[k]), bar*1.4, 0.20))

# vinyl crackle: sparse pops + soft hiss
hiss = rng.normal(0, 1, len(buf))
# lowpass hiss crudely
h = np.convolve(hiss, np.ones(24)/24, mode='same') * 0.006
pops = np.zeros(len(buf))
idx = rng.choice(len(buf)-100, size=int(total*9), replace=False)
for i in idx:
    l = rng.integers(15, 60)
    pops[i:i+l] += rng.normal(0, 0.05) * np.exp(-np.arange(l)/8)
buf = buf + h + pops

# gentle lowpass for warmth (moving average x2)
buf = np.convolve(buf, np.ones(6)/6, mode='same')
buf = np.convolve(buf, np.ones(4)/4, mode='same')

# normalize, fade in/out
buf = buf / np.max(np.abs(buf)) * 0.82
fi = int(0.8*SR); fo = int(2.0*SR)
buf[:fi] *= np.linspace(0, 1, fi)
buf[-fo:] *= np.linspace(1, 0, fo)

# light stereo: delay right channel a touch
right = np.roll(buf, int(0.012*SR)); right[:int(0.012*SR)] = 0
stereo = np.stack([buf, 0.92*right + 0.08*buf], axis=1)
pcm = (np.clip(stereo, -1, 1) * 32767).astype('<i2')

with wave.open('/home/user/pgotofood/assets/autumn_theme.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print('done', total, 'sec')
