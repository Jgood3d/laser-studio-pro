"""Générateur de tracés vectoriels (police 5x7) pour étiquettes texte G-Code, sans dépendance externe."""


class VectorFont:
    """Générateur de tracés vectoriels (5x7) pour étiquettes texte G-Code sans dépendance externe"""
    FONT_5X7 = {
        '0': [(0,0,5,0), (5,0,5,7), (5,7,0,7), (0,7,0,0), (0,0,5,7)],
        '1': [(2,0,2,7), (1,5,2,7)],
        '2': [(0,7,5,7), (5,7,5,4), (5,4,0,3), (0,3,0,0), (0,0,5,0)],
        '3': [(0,7,5,7), (5,7,5,0), (5,0,0,0), (1,3.5,5,3.5)],
        '4': [(0,7,0,3.5), (0,3.5,5,3.5), (4,7,4,0)],
        '5': [(5,7,0,7), (0,7,0,4), (0,4,5,3.5), (5,3.5,5,0), (5,0,0,0)],
        '6': [(5,7,0,7), (0,7,0,0), (0,0,5,0), (5,0,5,3.5), (5,3.5,0,3.5)],
        '7': [(0,7,5,7), (5,7,2,0)],
        '8': [(0,0,5,0), (5,0,5,7), (5,7,0,7), (0,7,0,0), (0,3.5,5,3.5)],
        '9': [(5,3.5,0,3.5), (0,3.5,0,7), (0,7,5,7), (5,7,5,0), (5,0,0,0)],
        '%': [(0,7,1,7), (1,7,1,6), (1,6,0,6), (0,6,0,7), (0,0,5,7), (4,1,5,1), (5,1,5,0), (5,0,4,0), (4,0,4,1)],
        '(': [(3,0,1,2), (1,2,1,5), (1,5,3,7)],
        ')': [(1,0,3,2), (3,2,3,5), (3,5,1,7)],
        '.': [(2,0,3,0), (3,0,3,1), (3,1,2,1), (2,1,2,0)],
        'P': [(0,0,0,7), (0,7,5,7), (5,7,5,3.5), (5,3.5,0,3.5)],
        'U': [(0,7,0,1), (0,1,1,0), (1,0,4,0), (4,0,5,1), (5,1,5,7)],
        'I': [(1,0,4,0), (2.5,0,2.5,7), (1,7,4,7)],
        'S': [(5,7,0,7), (0,7,0,4), (0,4,5,3), (5,3,5,0), (5,0,0,0)],
        'A': [(0,0,2.5,7), (2.5,7,5,0), (1,2.5,4,2.5)],
        'N': [(0,0,0,7), (0,7,5,0), (5,0,5,7)],
        'C': [(5,7,0,7), (0,7,0,0), (0,0,5,0)],
        'E': [(5,7,0,7), (0,7,0,0), (0,0,5,0), (0,3.5,3.5,3.5)],
        'V': [(0,7,2.5,0), (2.5,0,5,7)],
        'T': [(0,7,5,7), (2.5,7,2.5,0)],
        'O': [(0,0,5,0), (5,0,5,7), (5,7,0,7), (0,7,0,0)],
        'M': [(0,0,0,7), (0,7,2.5,3.5), (2.5,3.5,5,7), (5,7,5,0)],
        'B': [(0,0,0,7), (0,7,4,7), (4,7,4,3.5), (0,3.5,4,3.5), (4,3.5,4,0), (0,0,4,0)],
        'R': [(0,0,0,7), (0,7,4,7), (4,7,4,3.5), (0,3.5,4,3.5), (1.5,3.5,5,0)],
        'D': [(0,0,0,7), (0,7,3,7), (3,7,4,6), (4,6,4,1), (4,1,3,0), (3,0,0,0)],
        ' ': []
    }

    @staticmethod
    def generate_text_gcode(text, start_x, start_y, char_height=3.0, feed_rate=1500, power_val=500, laser_cmd="M3", vertical=False):
        gcode = [f"; --- Étiquette Texte: '{text}' ---"]
        scale = char_height / 7.0
        char_width = 5 * scale
        char_spacing = 2 * scale

        curr_x = start_x
        curr_y = start_y
        for char in str(text).upper():
            if char in VectorFont.FONT_5X7:
                segments = VectorFont.FONT_5X7[char]
                for x1, y1, x2, y2 in segments:
                    # Le glyphe garde toujours la même orientation, qu'il
                    # soit empilé horizontalement ou verticalement — seul le
                    # point d'ancrage (curr_x/curr_y) avance différemment
                    # entre les caractères (voir plus bas). Une inversion du
                    # signe ici retournerait chaque caractère à l'envers.
                    px1 = curr_x + (x1 * scale)
                    py1 = curr_y + (y1 * scale)
                    px2 = curr_x + (x2 * scale)
                    py2 = curr_y + (y2 * scale)

                    gcode.append(f"G0 X{px1:.3f} Y{py1:.3f}")
                    gcode.append(f"{laser_cmd} S{power_val}")
                    gcode.append(f"G1 X{px2:.3f} Y{py2:.3f} F{feed_rate}")
                    gcode.append("M5")
            if vertical:
                curr_y -= (7 * scale) + char_spacing
            else:
                curr_x += char_width + char_spacing
        return gcode
