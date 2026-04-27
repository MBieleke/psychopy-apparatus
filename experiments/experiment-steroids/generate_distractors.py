import random
import math

def rgb_to_lab(rgb):
    """
    Convert color from RGB to CIELAB space. 

    Parameters
    ----------
    c: tuple
        A tuple of three floats representing the RGB color (each in range 0-1).
    """
    def pivot_rgb(c):
        return ((c + 0.055)/1.055)**2.4 if c > 0.04045 else c/12.92

    R, G, B = [pivot_rgb(v) for v in rgb]

    X = 0.4124564*R + 0.3575761*G + 0.1804375*B
    Y = 0.2126729*R + 0.7151522*G + 0.0721750*B
    Z = 0.0193339*R + 0.1191920*G + 0.9503041*B

    X /= 0.95047
    Z /= 1.08883

    def f(t):
        return t**(1/3) if t > 0.008856 else (7.787*t + 16/116)

    L = 116 * f(Y) - 16
    a = 500 * (f(X) - f(Y))
    b = 200 * (f(Y) - f(Z))

    return (L, a, b)

def delta_e2000(lab1, lab2):
    """
    Calculate the Delta E 2000 color difference between two CIELAB colors.

    Parameters
    ----------
    lab1 : tuple
        A tuple of three floats representing the first CIELAB color (L, a, b).
    lab2 : tuple
        A tuple of three floats representing the second CIELAB color (L, a, b).
    """
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2

    avg_L = (L1 + L2) / 2
    C1 = math.sqrt(a1*a1 + b1*b1)
    C2 = math.sqrt(a2*a2 + b2*b2)
    avg_C = (C1 + C2) / 2

    G = 0.5 * (1 - math.sqrt((avg_C**7)/((avg_C**7) + (25**7))))
    a1p = a1 * (1 + G)
    a2p = a2 * (1 + G)

    C1p = math.sqrt(a1p*a1p + b1*b1)
    C2p = math.sqrt(a2p*a2p + b2*b2)
    avg_Cp = (C1p + C2p) / 2

    h1p = (math.degrees(math.atan2(b1, a1p)) + 360) % 360
    h2p = (math.degrees(math.atan2(b2, a2p)) + 360) % 360

    dhp = h2p - h1p
    if abs(dhp) > 180:
        dhp -= 360 * math.copysign(1, dhp)
    dHp = 2 * math.sqrt(C1p*C2p) * math.sin(math.radians(dhp/2))

    avg_hp = (h1p + dhp/2) % 360

    T = 1 - 0.17*math.cos(math.radians(avg_hp - 30)) \
          + 0.24*math.cos(math.radians(2*avg_hp)) \
          + 0.32*math.cos(math.radians(3*avg_hp + 6)) \
          - 0.20*math.cos(math.radians(4*avg_hp - 63))

    Sl = 1 + (0.015*((avg_L - 50)**2)) / math.sqrt(20 + (avg_L - 50)**2)
    Sc = 1 + 0.045 * avg_Cp
    Sh = 1 + 0.015 * avg_Cp * T

    Rt = -2 * math.sqrt((avg_Cp**7)/((avg_Cp**7)+(25**7))) * \
         math.sin(math.radians(60 * math.exp(-(((avg_hp - 275)/25)**2))))

    dE = math.sqrt(
        (L2-L1)**2 / (Sl**2) +
        (C2p-C1p)**2 / (Sc**2) +
        (dHp)**2 / (Sh**2) +
        Rt * (C2p-C1p)/Sc * dHp/Sh
    )
    return dE

def generate_distractors(target_rgb, deltaE_mid, n):
    """
    Generate n distractor colors in RGB space that are approximately deltaE_mid away from the target_rgb color.
    
    Parameters
    ----------
    target_rgb : tuple
        A tuple of three floats representing the target RGB color (each in range 0-1).
    deltaE_mid : float
        The target Delta E 2000 distance from the target color.
    n : int
        The number of distractor colors to generate.
    """
    target_lab = rgb_to_lab(target_rgb)

    distractors = []
    attempts = 0

    while len(distractors) < n and attempts < 50000:
        attempts += 1

        # random RGB candidate
        rgb = (random.random(), random.random(), random.random())
        lab = rgb_to_lab(rgb)
        dE = delta_e2000(target_lab, lab)

        if abs(dE - deltaE_mid) <= 1.5:  # Bandbreite 3
            distractors.append(rgb)

    if len(distractors) < n:
        print("WARNUNG: nicht genug Farben im DeltaE-Band gefunden.")
        # auffüllen mit Zufallsfarben
        while len(distractors) < n:
            distractors.append((random.random(),random.random(),random.random()))

    return distractors




import time

start = time.time()
result = generate_distractors([150/255, 150/255, 125/255], 30, 7)
end = time.time()

for i, color in enumerate(result):
    print(f"Color {i+1}: R={color[0]:.3f}, G={color[1]:.3f}, B={color[2]:.3f}")

print(f"\nDauer: {end - start:.3f} Sekunden")