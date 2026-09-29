import sys

dur = float(sys.argv[1])
out = sys.argv[2]

# (leaf_input, size, blur, xbase, amp, freq, phase, speed, yoff, rot, rph)
leaves = [
    # background - small, slow, slightly blurred
    (1, 55, 0.8,  80, 25, 0.7, 0.0,  70,    0,  0.30, 0.3),
    (2, 60, 0.8, 380, 20, 0.9, 1.0,  80,  600, -0.35, 1.1),
    (3, 50, 0.8, 600, 25, 0.8, 2.0,  65, 1000,  0.40, 2.2),
    (1, 65, 0.8, 240, 30, 0.6, 3.0,  90,  300, -0.30, 3.1),
    # midground - sharp
    (2, 100, 0,  40, 45, 1.0, 0.5, 130,  200,  0.50, 0.7),
    (3,  90, 0, 520, 40, 1.2, 1.5, 150,  800, -0.60, 1.9),
    (1, 110, 0, 300, 50, 0.8, 2.5, 120, 1200,  0.45, 2.8),
    (2,  95, 0, 640, 35, 1.4, 3.5, 160,  500, -0.50, 4.0),
    (3, 105, 0, 160, 55, 0.9, 4.5, 140,  900,  0.55, 5.1),
    (1,  85, 0, 450, 40, 1.1, 5.5, 170,  100, -0.40, 0.2),
    # foreground - big, blurred, fast (depth of field)
    (2, 230, 4, -40, 60, 0.6, 0.8, 260,  400,  0.35, 1.4),
    (1, 260, 5, 560, 70, 0.5, 2.2, 300, 1100, -0.30, 3.6),
]

counts = {1: 0, 2: 0, 3: 0}
for l in leaves:
    counts[l[0]] += 1

parts = []
# base grade + slow push-in + bloom
parts.append(
    "[0:v]colortemperature=temperature=5100:mix=0.85,"
    "eq=contrast=1.09:saturation=1.25:brightness=0.02:gamma=1.03,"
    "colorbalance=rs=0.03:bs=-0.04:rm=0.05:bm=-0.05:rh=0.02:bh=-0.03,"
    "unsharp=5:5:0.6:5:5:0.0,"
    "scale=1080:1920,"
    f"zoompan=z='1+0.10*in/{int(dur*30)}':d=1:x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':s=720x1280:fps=30,"
    "format=gbrp,split=2[bl0][bl1];"
    "[bl1]gblur=sigma=18[blur];"
    "[bl0][blur]blend=all_mode=screen:all_opacity=0.12[graded];"
)
# light leak drifting (subtle, corners only)
parts.append(
    "[5:v]format=gbrp[leak];"
    "[leak]crop=720:1280:x='140+120*sin(t*0.13)':y='210+90*sin(t*0.09)'[lk];"
    "[graded][lk]blend=all_mode=screen:all_opacity=0.10,"
    "eq=contrast=1.04:saturation=1.05,format=yuv420p[litbase];"
)
# split leaf sources
for k, c in counts.items():
    labels = "".join(f"[L{k}_{j}]" for j in range(c))
    parts.append(f"[{k}:v]format=rgba,split={c}{labels};")

# build leaf chains
used = {1: 0, 2: 0, 3: 0}
prev = "litbase"
for i, (src, size, blur, xb, amp, fr, ph, sp, yo, rot, rph) in enumerate(leaves):
    j = used[src]; used[src] += 1
    lbl = f"lf{i}"
    chain = f"[L{src}_{j}]scale={size}:-1,rotate='t*{rot}+0.5*sin(t*1.1+{rph})':c=none:ow=hypot(iw\\,ih):oh=ow"
    if blur:
        chain += f",gblur=sigma={blur}"
    chain += f"[{lbl}];"
    parts.append(chain)
    nxt = f"v{i}"
    parts.append(
        f"[{prev}][{lbl}]overlay=x='{xb}+{amp}*sin(t*{fr}+{ph})':"
        f"y='mod(t*{sp}+{yo}\\,1880)-300'[{nxt}];"
    )
    prev = nxt

# grain, vignette, fades
parts.append(
    f"[{prev}]noise=alls=6:allf=t+u,"
    "vignette=PI/5.5,"
    f"fade=t=in:st=0:d=0.5,fade=t=out:st={dur-0.8:.2f}:d=0.8[vout];"
)
# audio
parts.append("[0:a]volume=0.35,highpass=f=90[a0];")
parts.append("[4:a]volume=0.95,afade=t=in:st=0:d=0.6[a1];")
parts.append(
    f"[a0][a1]amix=inputs=2:duration=first:normalize=0,"
    f"afade=t=out:st={dur-1.4:.2f}:d=1.4[aout]"
)

with open(out, "w") as f:
    f.write("\n".join(parts))
print("filtergraph written:", out)
