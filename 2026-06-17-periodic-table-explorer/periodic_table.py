#!/usr/bin/env python3
"""
Interactive Terminal Periodic Table Explorer
Browse all 118 elements with a curses TUI. Navigate with arrow keys,
search by name/symbol, filter by category, and view detailed element info.
"""

import curses
import sys

# ── Element data ──────────────────────────────────────────────────────────
# Each element: (number, symbol, name, atomic_mass, category, phase, year_discovered)
# Categories: alkali-metal, alkaline-earth, transition-metal, post-transition,
#             metalloid, nonmetal, halogen, noble-gas, lanthanide, actinide
# Phase: solid, liquid, gas, unknown (at STP)

ELEMENTS = [
    (1, "H", "Hydrogen", 1.008, "nonmetal", "gas", 1766),
    (2, "He", "Helium", 4.003, "noble-gas", "gas", 1868),
    (3, "Li", "Lithium", 6.941, "alkali-metal", "solid", 1817),
    (4, "Be", "Beryllium", 9.012, "alkaline-earth", "solid", 1798),
    (5, "B", "Boron", 10.81, "metalloid", "solid", 1808),
    (6, "C", "Carbon", 12.011, "nonmetal", "solid", -3750),
    (7, "N", "Nitrogen", 14.007, "nonmetal", "gas", 1772),
    (8, "O", "Oxygen", 15.999, "nonmetal", "gas", 1774),
    (9, "F", "Fluorine", 18.998, "halogen", "gas", 1810),
    (10, "Ne", "Neon", 20.180, "noble-gas", "gas", 1898),
    (11, "Na", "Sodium", 22.990, "alkali-metal", "solid", 1807),
    (12, "Mg", "Magnesium", 24.305, "alkaline-earth", "solid", 1755),
    (13, "Al", "Aluminum", 26.982, "post-transition", "solid", 1825),
    (14, "Si", "Silicon", 28.086, "metalloid", "solid", 1824),
    (15, "P", "Phosphorus", 30.974, "nonmetal", "solid", 1669),
    (16, "S", "Sulfur", 32.065, "nonmetal", "solid", -500),
    (17, "Cl", "Chlorine", 35.453, "halogen", "gas", 1774),
    (18, "Ar", "Argon", 39.948, "noble-gas", "gas", 1894),
    (19, "K", "Potassium", 39.098, "alkali-metal", "solid", 1807),
    (20, "Ca", "Calcium", 40.078, "alkaline-earth", "solid", 1808),
    (21, "Sc", "Scandium", 44.956, "transition-metal", "solid", 1879),
    (22, "Ti", "Titanium", 47.867, "transition-metal", "solid", 1791),
    (23, "V", "Vanadium", 50.942, "transition-metal", "solid", 1801),
    (24, "Cr", "Chromium", 51.996, "transition-metal", "solid", 1797),
    (25, "Mn", "Manganese", 54.938, "transition-metal", "solid", 1774),
    (26, "Fe", "Iron", 55.845, "transition-metal", "solid", -5000),
    (27, "Co", "Cobalt", 58.933, "transition-metal", "solid", 1735),
    (28, "Ni", "Nickel", 58.693, "transition-metal", "solid", 1751),
    (29, "Cu", "Copper", 63.546, "transition-metal", "solid", -9000),
    (30, "Zn", "Zinc", 65.380, "transition-metal", "solid", 1746),
    (31, "Ga", "Gallium", 69.723, "post-transition", "solid", 1875),
    (32, "Ge", "Germanium", 72.630, "metalloid", "solid", 1886),
    (33, "As", "Arsenic", 74.922, "metalloid", "solid", 1250),
    (34, "Se", "Selenium", 78.971, "nonmetal", "solid", 1817),
    (35, "Br", "Bromine", 79.904, "halogen", "liquid", 1826),
    (36, "Kr", "Krypton", 83.798, "noble-gas", "gas", 1898),
    (37, "Rb", "Rubidium", 85.468, "alkali-metal", "solid", 1861),
    (38, "Sr", "Strontium", 87.620, "alkaline-earth", "solid", 1790),
    (39, "Y", "Yttrium", 88.906, "transition-metal", "solid", 1794),
    (40, "Zr", "Zirconium", 91.224, "transition-metal", "solid", 1789),
    (41, "Nb", "Niobium", 92.906, "transition-metal", "solid", 1801),
    (42, "Mo", "Molybdenum", 95.950, "transition-metal", "solid", 1781),
    (43, "Tc", "Technetium", 98.000, "transition-metal", "solid", 1937),
    (44, "Ru", "Ruthenium", 101.070, "transition-metal", "solid", 1844),
    (45, "Rh", "Rhodium", 102.906, "transition-metal", "solid", 1803),
    (46, "Pd", "Palladium", 106.420, "transition-metal", "solid", 1803),
    (47, "Ag", "Silver", 107.868, "transition-metal", "solid", -5000),
    (48, "Cd", "Cadmium", 112.414, "transition-metal", "solid", 1817),
    (49, "In", "Indium", 114.818, "post-transition", "solid", 1863),
    (50, "Sn", "Tin", 118.710, "post-transition", "solid", -3500),
    (51, "Sb", "Antimony", 121.760, "metalloid", "solid", -3000),
    (52, "Te", "Tellurium", 127.600, "metalloid", "solid", 1783),
    (53, "I", "Iodine", 126.904, "halogen", "solid", 1811),
    (54, "Xe", "Xenon", 131.293, "noble-gas", "gas", 1898),
    (55, "Cs", "Cesium", 132.905, "alkali-metal", "solid", 1860),
    (56, "Ba", "Barium", 137.327, "alkaline-earth", "solid", 1808),
    (57, "La", "Lanthanum", 138.905, "lanthanide", "solid", 1839),
    (58, "Ce", "Cerium", 140.116, "lanthanide", "solid", 1803),
    (59, "Pr", "Praseodymium", 140.908, "lanthanide", "solid", 1885),
    (60, "Nd", "Neodymium", 144.242, "lanthanide", "solid", 1885),
    (61, "Pm", "Promethium", 145.000, "lanthanide", "solid", 1945),
    (62, "Sm", "Samarium", 150.360, "lanthanide", "solid", 1879),
    (63, "Eu", "Europium", 151.964, "lanthanide", "solid", 1901),
    (64, "Gd", "Gadolinium", 157.250, "lanthanide", "solid", 1880),
    (65, "Tb", "Terbium", 158.925, "lanthanide", "solid", 1843),
    (66, "Dy", "Dysprosium", 162.500, "lanthanide", "solid", 1886),
    (67, "Ho", "Holmium", 164.930, "lanthanide", "solid", 1878),
    (68, "Er", "Erbium", 167.259, "lanthanide", "solid", 1842),
    (69, "Tm", "Thulium", 168.934, "lanthanide", "solid", 1879),
    (70, "Yb", "Ytterbium", 173.045, "lanthanide", "solid", 1878),
    (71, "Lu", "Lutetium", 174.967, "lanthanide", "solid", 1907),
    (72, "Hf", "Hafnium", 178.490, "transition-metal", "solid", 1923),
    (73, "Ta", "Tantalum", 180.948, "transition-metal", "solid", 1802),
    (74, "W", "Tungsten", 183.840, "transition-metal", "solid", 1783),
    (75, "Re", "Rhenium", 186.207, "transition-metal", "solid", 1925),
    (76, "Os", "Osmium", 190.230, "transition-metal", "solid", 1803),
    (77, "Ir", "Iridium", 192.217, "transition-metal", "solid", 1803),
    (78, "Pt", "Platinum", 195.084, "transition-metal", "solid", 1735),
    (79, "Au", "Gold", 196.967, "transition-metal", "solid", -6000),
    (80, "Hg", "Mercury", 200.592, "transition-metal", "liquid", -1500),
    (81, "Tl", "Thallium", 204.380, "post-transition", "solid", 1861),
    (82, "Pb", "Lead", 207.200, "post-transition", "solid", -7000),
    (83, "Bi", "Bismuth", 208.980, "post-transition", "solid", 1753),
    (84, "Po", "Polonium", 209.000, "post-transition", "solid", 1898),
    (85, "At", "Astatine", 210.000, "halogen", "solid", 1940),
    (86, "Rn", "Radon", 222.000, "noble-gas", "gas", 1900),
    (87, "Fr", "Francium", 223.000, "alkali-metal", "solid", 1939),
    (88, "Ra", "Radium", 226.000, "alkaline-earth", "solid", 1898),
    (89, "Ac", "Actinium", 227.000, "actinide", "solid", 1899),
    (90, "Th", "Thorium", 232.038, "actinide", "solid", 1829),
    (91, "Pa", "Protactinium", 231.036, "actinide", "solid", 1913),
    (92, "U", "Uranium", 238.029, "actinide", "solid", 1789),
    (93, "Np", "Neptunium", 237.000, "actinide", "solid", 1940),
    (94, "Pu", "Plutonium", 244.000, "actinide", "solid", 1940),
    (95, "Am", "Americium", 243.000, "actinide", "solid", 1944),
    (96, "Cm", "Curium", 247.000, "actinide", "solid", 1944),
    (97, "Bk", "Berkelium", 247.000, "actinide", "solid", 1949),
    (98, "Cf", "Californium", 251.000, "actinide", "solid", 1950),
    (99, "Es", "Einsteinium", 252.000, "actinide", "solid", 1952),
    (100, "Fm", "Fermium", 257.000, "actinide", "solid", 1952),
    (101, "Md", "Mendelevium", 258.000, "actinide", "solid", 1955),
    (102, "No", "Nobelium", 259.000, "actinide", "solid", 1966),
    (103, "Lr", "Lawrencium", 266.000, "actinide", "solid", 1961),
    (104, "Rf", "Rutherfordium", 267.000, "transition-metal", "unknown", 1964),
    (105, "Db", "Dubnium", 268.000, "transition-metal", "unknown", 1967),
    (106, "Sg", "Seaborgium", 269.000, "transition-metal", "unknown", 1974),
    (107, "Bh", "Bohrium", 270.000, "transition-metal", "unknown", 1981),
    (108, "Hs", "Hassium", 269.000, "transition-metal", "unknown", 1984),
    (109, "Mt", "Meitnerium", 278.000, "unknown", "unknown", 1982),
    (110, "Ds", "Darmstadtium", 281.000, "unknown", "unknown", 1994),
    (111, "Rg", "Roentgenium", 282.000, "unknown", "unknown", 1994),
    (112, "Cn", "Copernicium", 285.000, "transition-metal", "unknown", 1996),
    (113, "Nh", "Nihonium", 286.000, "unknown", "unknown", 2003),
    (114, "Fl", "Flerovium", 289.000, "post-transition", "unknown", 1998),
    (115, "Mc", "Moscovium", 290.000, "unknown", "unknown", 2003),
    (116, "Lv", "Livermorium", 293.000, "unknown", "unknown", 2000),
    (117, "Ts", "Tennessine", 294.000, "unknown", "unknown", 2010),
    (118, "Og", "Oganesson", 294.000, "unknown", "unknown", 2002),
]

# Element positions on the periodic table (group, period)
# Main table
TABLE_POS = {
    1: (1, 1), 2: (18, 1),
    3: (1, 2), 4: (2, 2), 5: (13, 2), 6: (14, 2), 7: (15, 2),
    8: (16, 2), 9: (17, 2), 10: (18, 2),
    11: (1, 3), 12: (2, 3), 13: (13, 3), 14: (14, 3), 15: (15, 3),
    16: (16, 3), 17: (17, 3), 18: (18, 3),
    19: (1, 4), 20: (2, 4), 21: (3, 4), 22: (4, 4), 23: (5, 4),
    24: (6, 4), 25: (7, 4), 26: (8, 4), 27: (9, 4), 28: (10, 4),
    29: (11, 4), 30: (12, 4), 31: (13, 4), 32: (14, 4), 33: (15, 4),
    34: (16, 4), 35: (17, 4), 36: (18, 4),
    37: (1, 5), 38: (2, 5), 39: (3, 5), 40: (4, 5), 41: (5, 5),
    42: (6, 5), 43: (7, 5), 44: (8, 5), 45: (9, 5), 46: (10, 5),
    47: (11, 5), 48: (12, 5), 49: (13, 5), 50: (14, 5), 51: (15, 5),
    52: (16, 5), 53: (17, 5), 54: (18, 5),
    55: (1, 6), 56: (2, 6),
    72: (3, 6), 73: (4, 6), 74: (5, 6), 75: (6, 6), 76: (7, 6),
    77: (8, 6), 78: (9, 6), 79: (10, 6), 80: (11, 6), 81: (12, 6),
    82: (13, 6), 83: (14, 6), 84: (15, 6), 85: (16, 6), 86: (17, 6),
    87: (1, 7), 88: (2, 7),
    104: (3, 7), 105: (4, 7), 106: (5, 7), 107: (6, 7), 108: (7, 7),
    109: (8, 7), 110: (9, 7), 111: (10, 7), 112: (11, 7), 113: (12, 7),
    114: (13, 7), 115: (14, 7), 116: (15, 7), 117: (16, 7), 118: (18, 7),
}

# Lanthanide row positions (displayed below the main table)
LANTHANIDE_POS = {}
for _i, _z in enumerate(range(57, 72)):
    LANTHANIDE_POS[_z] = (4 + _i, 9)

# Actinide row positions (displayed below lanthanides)
ACTINIDE_POS = {}
for _i, _z in enumerate(range(89, 104)):
    ACTINIDE_POS[_z] = (4 + _i, 10)

# Category display names and colors
CATEGORY_DISPLAY = {
    "alkali-metal": "Alkali Metal",
    "alkaline-earth": "Alkaline Earth",
    "transition-metal": "Transition Metal",
    "post-transition": "Post-Transition",
    "metalloid": "Metalloid",
    "nonmetal": "Nonmetal",
    "halogen": "Halogen",
    "noble-gas": "Noble Gas",
    "lanthanide": "Lanthanide",
    "actinide": "Actinide",
    "unknown": "Unknown",
}

PHASE_DISPLAY = {
    "solid": "Solid",
    "liquid": "Liquid",
    "gas": "Gas",
    "unknown": "Unknown",
}

# Curses color pairs assigned to categories (will be set up in _init_colors)
CATEGORY_COLOR_IDS = {
    "alkali-metal": 1,
    "alkaline-earth": 2,
    "transition-metal": 3,
    "post-transition": 4,
    "metalloid": 5,
    "nonmetal": 6,
    "halogen": 7,
    "noble-gas": 8,
    "lanthanide": 9,
    "actinide": 10,
    "unknown": 11,
}

# RGB values for each category (for custom color support)
CATEGORY_RGB = {
    "alkali-metal": (230, 70, 70),
    "alkaline-earth": (255, 165, 0),
    "transition-metal": (255, 215, 0),
    "post-transition": (100, 200, 100),
    "metalloid": (0, 200, 200),
    "nonmetal": (100, 149, 237),
    "halogen": (180, 100, 220),
    "noble-gas": (255, 105, 180),
    "lanthanide": (210, 180, 140),
    "actinide": (188, 143, 143),
    "unknown": (150, 150, 150),
}


def format_year(year):
    if year < 0:
        return f"{abs(year)} BCE"
    return str(year)


class PeriodicTableApp:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.selected = 1
        self.mode = "table"  # table, search, filter, detail
        self.search_query = ""
        self.filter_category = None
        self.search_results = list(ELEMENTS)
        self.search_cursor = 0
        self.filter_categories = [
            "alkali-metal", "alkaline-earth", "transition-metal",
            "post-transition", "metalloid", "nonmetal", "halogen",
            "noble-gas", "lanthanide", "actinide", "unknown",
        ]
        self.filter_cursor = 0
        self.detail_element = None
        self.element_by_num = {e[0]: e for e in ELEMENTS}
        self.use_color = False
        self._init_colors()

    def _init_colors(self):
        self.use_color = curses.has_colors()
        if not self.use_color:
            return
        curses.start_color()
        curses.use_default_colors()

        # Try to use custom colors, fall back to basic if not supported
        can_custom = curses.can_change_color()

        for cat, color_id in CATEGORY_COLOR_IDS.items():
            r, g, b = CATEGORY_RGB[cat]
            if can_custom:
                try:
                    curses.init_color(color_id + 20,
                                      int(r * 1000 / 255),
                                      int(g * 1000 / 255),
                                      int(b * 1000 / 255))
                    curses.init_pair(color_id, color_id + 20, -1)
                except curses.error:
                    # Fall back to basic colors
                    basic_map = {
                        "alkali-metal": 1,      # red
                        "alkaline-earth": 3,    # yellow
                        "transition-metal": 3,  # yellow
                        "post-transition": 2,   # green
                        "metalloid": 6,         # cyan
                        "nonmetal": 4,          # blue
                        "halogen": 5,           # magenta
                        "noble-gas": 5,         # magenta
                        "lanthanide": 3,        # yellow
                        "actinide": 3,          # yellow
                        "unknown": 7,           # white
                    }
                    curses.init_pair(color_id, basic_map.get(cat, 7), -1)
            else:
                basic_map = {
                    "alkali-metal": 1,
                    "alkaline-earth": 3,
                    "transition-metal": 3,
                    "post-transition": 2,
                    "metalloid": 6,
                    "nonmetal": 4,
                    "halogen": 5,
                    "noble-gas": 5,
                    "lanthanide": 3,
                    "actinide": 3,
                    "unknown": 7,
                }
                curses.init_pair(color_id, basic_map.get(cat, 7), -1)

        # Highlight pair (black on white)
        curses.init_pair(50, 0, 7)
        self.highlight_pair = 50

        # Title color
        curses.init_pair(51, 11, -1)  # Yellow on default
        self.title_pair = 51

        # Dim color
        curses.init_pair(52, 8, -1)
        self.dim_pair = 52

        # Inverse pair
        curses.init_pair(53, 0, 15)
        self.inverse_pair = 53

    def _get_cat_color(self, cat):
        if not self.use_color:
            return 0
        return curses.color_pair(CATEGORY_COLOR_IDS.get(cat, 7))

    def run(self):
        curses.curs_set(0)
        self.stdscr.nodelay(False)
        self.stdscr.keypad(True)

        while True:
            self.stdscr.clear()
            h, w = self.stdscr.getmaxyx()

            if self.mode == "table":
                self._draw_table(h, w)
            elif self.mode == "search":
                self._draw_search(h, w)
            elif self.mode == "filter":
                self._draw_filter(h, w)
            elif self.mode == "detail":
                self._draw_detail(h, w)

            self.stdscr.refresh()
            key = self.stdscr.getch()
            if not self._handle_input(key):
                break

    # ── Draw methods ──────────────────────────────────────────────────

    def _draw_table(self, h, w):
        cell_w = 5
        cell_h = 3
        table_start_y = 2
        table_start_x = 1

        # Title
        title = "PERIODIC TABLE EXPLORER"
        self.stdscr.addstr(0, max(0, (w - len(title)) // 2), title,
                          curses.color_pair(self.title_pair) | curses.A_BOLD)

        # Draw main table cells
        for elem in ELEMENTS:
            z = elem[0]
            if z in LANTHANIDE_POS:
                col, row = LANTHANIDE_POS[z]
            elif z in ACTINIDE_POS:
                col, row = ACTINIDE_POS[z]
            else:
                col, row = TABLE_POS[z]

            x = table_start_x + (col - 1) * (cell_w + 1)
            y = table_start_y + (row - 1) * (cell_h + 1)

            if x + cell_w > w or y + cell_h > h:
                continue

            # Determine if filtered out
            dimmed = self.filter_category is not None and elem[4] != self.filter_category

            is_selected = (z == self.selected)
            cat_color = self._get_cat_color(elem[4])

            if is_selected:
                # Highlighted cell
                for dy in range(cell_h):
                    self.stdscr.addstr(y + dy, x, ' ' * cell_w,
                                      curses.color_pair(self.highlight_pair) | curses.A_BOLD)
                self.stdscr.addstr(y, x + 1, f"{z:3d}"[:cell_w - 1],
                                  curses.color_pair(self.highlight_pair) | curses.A_BOLD)
                self.stdscr.addstr(y + 1, x + (cell_w - 1) // 2, elem[1][:cell_w - 2],
                                  curses.color_pair(self.highlight_pair) | curses.A_BOLD)
            else:
                # Normal cell with border
                attr = cat_color | curses.A_BOLD if not dimmed else curses.color_pair(self.dim_pair)

                # Top border
                self.stdscr.addstr(y, x, "+" + "-" * (cell_w - 2) + "+")
                # Middle lines
                self.stdscr.addstr(y + 1, x, "|")
                self.stdscr.addstr(y + 1, x + 1, elem[1].center(cell_w - 2)[:cell_w - 2], attr)
                self.stdscr.addstr(y + 1, x + cell_w - 1, "|")
                # Bottom border
                self.stdscr.addstr(y + 2, x, "+" + "-" * (cell_w - 2) + "+")

                # Atomic number (tiny, in corner)
                num_str = f"{z:2d}"[:cell_w - 2]
                num_attr = curses.color_pair(self.dim_pair) if dimmed else cat_color
                try:
                    self.stdscr.addstr(y, x + 1, num_str, num_attr)
                except curses.error:
                    pass

        # Draw lanthanide/actinide labels
        label_y_base = table_start_y + 6 * (cell_h + 1)
        if label_y_base + 4 * (cell_h + 1) < h:
            self.stdscr.addstr(label_y_base, table_start_x,
                              "La-Lu", curses.color_pair(self.dim_pair))
            self.stdscr.addstr(label_y_base + 1 * (cell_h + 1), table_start_x,
                              "Ac-Lr", curses.color_pair(self.dim_pair))

        # Draw info panel for selected element (right side)
        elem = self.element_by_num.get(self.selected)
        if elem:
            panel_x = max(0, w - 38)
            panel_y = 2
            panel_w = 36
            panel_h = 14
            if panel_x > 75:
                self._draw_info_panel(elem, panel_x, panel_y, panel_w, panel_h)

        # Legend at bottom
        legend_y = h - 3
        if legend_y > 0:
            self.stdscr.addstr(legend_y, 2,
                              "Arrows: Navigate | Enter: Detail | /: Search | F: Filter | q: Quit",
                              curses.color_pair(self.dim_pair))

        # Mini category legend
        leg_y = h - 2
        if leg_y > 0:
            x_pos = 2
            for cat in ["alkali-metal", "alkaline-earth", "transition-metal",
                        "nonmetal", "halogen", "noble-gas", "lanthanide", "actinide"]:
                short = CATEGORY_DISPLAY[cat].split()[0][:3]
                attr = self._get_cat_color(cat) | curses.A_BOLD
                text = f"{short}"
                if x_pos + len(text) + 1 < w:
                    self.stdscr.addstr(leg_y, x_pos, text, attr)
                    x_pos += len(text) + 2

    def _draw_info_panel(self, elem, x, y, pw, ph):
        z, sym, name, mass, cat, phase, year = elem
        cat_color = self._get_cat_color(cat)

        # Draw panel
        self.stdscr.addstr(y, x, "+" + "=" * (pw - 2) + "+")
        for i in range(1, ph - 1):
            self.stdscr.addstr(y + i, x, "|")
            self.stdscr.addstr(y + i, x + pw - 1, "|")
        self.stdscr.addstr(y + ph - 1, x, "+" + "=" * (pw - 2) + "+")

        # Clear inside
        for i in range(1, ph - 1):
            self.stdscr.addstr(y + i, x + 1, " " * (pw - 2))

        # Content
        self.stdscr.addstr(y + 1, x + 2, f"#{z} {name}",
                          cat_color | curses.A_BOLD)
        self.stdscr.addstr(y + 2, x + 2, f"Symbol: {sym}",
                          cat_color | curses.A_BOLD)
        self.stdscr.addstr(y + 4, x + 2, f"Atomic Mass: {mass:.3f} u")
        self.stdscr.addstr(y + 5, x + 2, f"Category:    {CATEGORY_DISPLAY.get(cat, cat)}")
        self.stdscr.addstr(y + 6, x + 2, f"Phase (STP): {PHASE_DISPLAY.get(phase, phase)}")
        self.stdscr.addstr(y + 7, x + 2, f"Discovered:  {format_year(year)}")

        # Position info
        if z in TABLE_POS:
            group, period = TABLE_POS[z]
            self.stdscr.addstr(y + 9, x + 2, f"Period: {period}  Group: {group}")
        elif z in LANTHANIDE_POS:
            self.stdscr.addstr(y + 9, x + 2, f"Period: 6  (Lanthanide)")
        elif z in ACTINIDE_POS:
            self.stdscr.addstr(y + 9, x + 2, f"Period: 7  (Actinide)")

        # Mass rank
        sorted_mass = sorted(ELEMENTS, key=lambda e: e[3])
        rank = next(i for i, e in enumerate(sorted_mass) if e[0] == z) + 1
        self.stdscr.addstr(y + 10, x + 2, f"Mass Rank:   #{rank}/118")

    def _draw_search(self, h, w):
        self.stdscr.addstr(0, 2, "Search Elements (ESC: cancel, Enter: select, Up/Down: scroll):",
                          curses.color_pair(self.title_pair) | curses.A_BOLD)
        self.stdscr.addstr(2, 2, f"> {self.search_query}_")

        if self.search_query:
            q = self.search_query.lower()
            self.search_results = [
                e for e in ELEMENTS
                if q in e[2].lower()
                or q == e[1].lower()
                or (q.isdigit() and int(q) == e[0])
            ]
        else:
            self.search_results = list(ELEMENTS)

        # Clamp cursor
        if self.search_cursor >= len(self.search_results):
            self.search_cursor = max(0, len(self.search_results) - 1)

        max_rows = min(h - 4, len(self.search_results))
        scroll_offset = max(0, self.search_cursor - max_rows + 5)

        for i in range(max_rows):
            idx = i + scroll_offset
            if idx >= len(self.search_results):
                break
            elem = self.search_results[idx]
            z, sym, name, mass, cat, phase, year = elem
            cat_color = self._get_cat_color(cat)

            if idx == self.search_cursor:
                attr = curses.color_pair(self.highlight_pair) | curses.A_BOLD
            else:
                attr = cat_color

            line = f" {z:3d} {sym:2s} {name:20s} {mass:10.3f} {CATEGORY_DISPLAY.get(cat, cat):16s} "
            self.stdscr.addstr(4 + i, 2, line, attr)

        # Show count
        self.stdscr.addstr(h - 1, 2,
                          f"Showing {max_rows} of {len(self.search_results)} results",
                          curses.color_pair(self.dim_pair))

    def _draw_filter(self, h, w):
        self.stdscr.addstr(0, 2, "Filter by Category (Enter: toggle, ESC: close, C: clear):",
                          curses.color_pair(self.title_pair) | curses.A_BOLD)

        for i, cat in enumerate(self.filter_categories):
            cat_color = self._get_cat_color(cat)
            is_active = (self.filter_category == cat)
            is_cursor = (i == self.filter_cursor)

            display_name = CATEGORY_DISPLAY.get(cat, cat)
            marker = "[x]" if is_active else "[ ]"

            if is_cursor:
                attr = curses.color_pair(self.highlight_pair) | curses.A_BOLD
            else:
                attr = cat_color

            self.stdscr.addstr(2 + i, 2, f" {marker} {display_name}", attr)

        if self.filter_category:
            self.stdscr.addstr(2 + len(self.filter_categories) + 1, 2,
                              f"Active: {CATEGORY_DISPLAY.get(self.filter_category, self.filter_category)}",
                              curses.color_pair(self.title_pair))
            self.stdscr.addstr(2 + len(self.filter_categories) + 2, 2,
                              "Press Enter on active filter to clear it",
                              curses.color_pair(self.dim_pair))

    def _draw_detail(self, h, w):
        if not self.detail_element:
            self.mode = "table"
            return

        z, sym, name, mass, cat, phase, year = self.detail_element
        cat_color = self._get_cat_color(cat)

        # Title bar
        title = f"  {sym} - {name} (#{z})  "
        self.stdscr.addstr(0, max(0, (w - len(title)) // 2), title,
                          cat_color | curses.A_BOLD)

        # Big symbol in ASCII art
        big_sym = self._make_big_symbol(sym)
        sym_start_y = 3
        sym_start_x = max(0, (w // 3) - 10)

        for i, line in enumerate(big_sym):
            if sym_start_y + i < h:
                self.stdscr.addstr(sym_start_y + i, sym_start_x, line,
                                  cat_color | curses.A_BOLD)

        # Details on the right side
        detail_x = min(w - 38, (w // 2) + 5)
        detail_y = 3

        details = [
            ("Atomic Number", str(z)),
            ("Symbol", sym),
            ("Name", name),
            ("Atomic Mass", f"{mass:.3f} u"),
            ("Category", CATEGORY_DISPLAY.get(cat, cat)),
            ("Phase (STP)", PHASE_DISPLAY.get(phase, phase)),
            ("Discovered", format_year(year)),
        ]

        if z in TABLE_POS:
            group, period = TABLE_POS[z]
            details.append(("Period", str(period)))
            details.append(("Group", str(group)))
        elif z in LANTHANIDE_POS:
            details.append(("Period", "6"))
            details.append(("Row", "Lanthanide"))
        elif z in ACTINIDE_POS:
            details.append(("Period", "7"))
            details.append(("Row", "Actinide"))

        sorted_mass = sorted(ELEMENTS, key=lambda e: e[3])
        mass_rank = next(i for i, e in enumerate(sorted_mass) if e[0] == z) + 1
        details.append(("Mass Rank", f"#{mass_rank} of 118"))

        # Neighbors
        neighbors = []
        if z > 1:
            neighbors.append(self.element_by_num[z - 1])
        if z < 118:
            neighbors.append(self.element_by_num[z + 1])
        neighbor_str = "  ".join(f"{n[1]}({n[0]})" for n in neighbors)
        details.append(("Neighbors", neighbor_str))

        for i, (label, value) in enumerate(details):
            if detail_y + i < h - 3:
                self.stdscr.addstr(detail_y + i, detail_x, f"{label}:",
                                  curses.A_BOLD)
                self.stdscr.addstr(detail_y + i, detail_x + 18, value)

        # Separator line
        sep_y = h - 4
        if sep_y > detail_y + len(details):
            self.stdscr.addstr(sep_y, 2, "-" * (w - 4))

        # Category bar
        bar_y = h - 3
        if bar_y > 0:
            self.stdscr.addstr(bar_y, 2, "Category: ", curses.A_BOLD)
            self.stdscr.addstr(bar_y, 12,
                              f" {CATEGORY_DISPLAY.get(cat, cat)} ",
                              cat_color | curses.A_BOLD)

            phase_icons = {"solid": "[=]", "liquid": "[~]", "gas": "[o]", "unknown": "[?]"}
            self.stdscr.addstr(bar_y, 35,
                              f"Phase: {phase_icons.get(phase, '[?]')} {PHASE_DISPLAY.get(phase, phase)}")

        # Navigation help
        self.stdscr.addstr(h - 1, 2,
                          "Left/Right: Prev/Next element | ESC/Enter: Back to table",
                          curses.color_pair(self.dim_pair))

    def _make_big_symbol(self, sym):
        """Create a large ASCII art representation of element symbol."""
        glyphs = {
            'A': ["  #  ", "#   #", "#####", "#   #", "#   #"],
            'B': ["#### ", "#   #", "#### ", "#   #", "#### "],
            'C': [" ####", "#    ", "#    ", "#    ", " ####"],
            'D': ["#### ", "#   #", "#   #", "#   #", "#### "],
            'E': ["#####", "#    ", "###  ", "#    ", "#####"],
            'F': ["#####", "#    ", "###  ", "#    ", "#    "],
            'G': [" ####", "#    ", "#  ##", "#   #", " ####"],
            'H': ["#   #", "#   #", "#####", "#   #", "#   #"],
            'I': ["#####", "  #  ", "  #  ", "  #  ", "#####"],
            'J': ["  ###", "    #", "    #", "#   #", " ### "],
            'K': ["#   #", "#  # ", "###  ", "#  # ", "#   #"],
            'L': ["#    ", "#    ", "#    ", "#    ", "#####"],
            'M': ["#   #", "## ##", "# # #", "#   #", "#   #"],
            'N': ["#   #", "##  #", "# # #", "#  ##", "#   #"],
            'O': [" ### ", "#   #", "#   #", "#   #", " ### "],
            'P': ["#### ", "#   #", "#### ", "#    ", "#    "],
            'Q': [" ### ", "#   #", "# # #", "#  ##", " ####"],
            'R': ["#### ", "#   #", "#### ", "#  # ", "#   #"],
            'S': [" ####", "#    ", " ### ", "    #", "#### "],
            'T': ["#####", "  #  ", "  #  ", "  #  ", "  #  "],
            'U': ["#   #", "#   #", "#   #", "#   #", " ### "],
            'V': ["#   #", "#   #", "#   #", " # # ", "  #  "],
            'W': ["#   #", "#   #", "# # #", "## ##", "#   #"],
            'X': ["#   #", " # # ", "  #  ", " # # ", "#   #"],
            'Y': ["#   #", " # # ", "  #  ", "  #  ", "  #  "],
            'Z': ["#####", "   # ", "  #  ", " #   ", "#####"],
        }

        result = []
        for row in range(5):
            line = ""
            for ch in sym:
                if ch.upper() in glyphs:
                    line += glyphs[ch.upper()][row] + " "
                else:
                    line += "      "
            result.append(line)
        return result

    # ── Input handling ────────────────────────────────────────────────

    def _handle_input(self, key):
        if self.mode == "table":
            return self._handle_table_input(key)
        elif self.mode == "search":
            return self._handle_search_input(key)
        elif self.mode == "filter":
            return self._handle_filter_input(key)
        elif self.mode == "detail":
            return self._handle_detail_input(key)
        return True

    def _handle_table_input(self, key):
        if key == ord('q'):
            return False
        elif key == 27:  # ESC
            return False
        elif key == curses.KEY_UP:
            self._move_selected(0, -1)
        elif key == curses.KEY_DOWN:
            self._move_selected(0, 1)
        elif key == curses.KEY_LEFT:
            self._move_selected(-1, 0)
        elif key == curses.KEY_RIGHT:
            self._move_selected(1, 0)
        elif key == ord('\n') or key == curses.KEY_ENTER:
            self.detail_element = self.element_by_num.get(self.selected)
            if self.detail_element:
                self.mode = "detail"
        elif key == ord('/'):
            self.search_query = ""
            self.search_cursor = 0
            self.mode = "search"
        elif key == ord('f') or key == ord('F'):
            self.filter_cursor = 0
            self.mode = "filter"
        return True

    def _move_selected(self, dx, dy):
        """Move selection in the periodic table grid."""
        # Check if we're in lanthanides
        if self.selected in LANTHANIDE_POS:
            keys = sorted(LANTHANIDE_POS.keys())
            idx = keys.index(self.selected)
            if dx > 0 and idx < len(keys) - 1:
                self.selected = keys[idx + 1]
            elif dx < 0 and idx > 0:
                self.selected = keys[idx - 1]
            elif dy < 0:
                # Go up to main table
                self.selected = 56  # Ba
            return

        # Check if we're in actinides
        if self.selected in ACTINIDE_POS:
            keys = sorted(ACTINIDE_POS.keys())
            idx = keys.index(self.selected)
            if dx > 0 and idx < len(keys) - 1:
                self.selected = keys[idx + 1]
            elif dx < 0 and idx > 0:
                self.selected = keys[idx - 1]
            elif dy < 0:
                self.selected = 88  # Ra
            return

        current_pos = TABLE_POS.get(self.selected)
        if not current_pos:
            self.selected = 1
            return

        cur_group, cur_period = current_pos

        # Find nearest element in direction
        candidates = []
        if dx != 0:
            for z, (g, p) in TABLE_POS.items():
                if p == cur_period and (dx > 0 and g > cur_group or dx < 0 and g < cur_group):
                    candidates.append((abs(g - cur_group), z))
        if dy != 0:
            for z, (g, p) in TABLE_POS.items():
                if g == cur_group and (dy > 0 and p > cur_period or dy < 0 and p < cur_period):
                    candidates.append((abs(p - cur_period), z))

        if candidates:
            candidates.sort()
            self.selected = candidates[0][1]
            return

        # Transition to/from lanthanides/actinides
        if dy > 0 and cur_group == 3 and cur_period == 6 and self.selected == 72:
            self.selected = 57
            return
        if dy > 0 and cur_group == 3 and cur_period == 7 and self.selected == 104:
            self.selected = 89
            return

        # Simple fallback: increment/decrement
        if dy > 0 or dx > 0:
            self.selected = min(118, self.selected + 1)
        elif dy < 0 or dx < 0:
            self.selected = max(1, self.selected - 1)

    def _handle_search_input(self, key):
        if key == 27:  # ESC
            self.mode = "table"
            return True
        elif key == curses.KEY_UP:
            self.search_cursor = max(0, self.search_cursor - 1)
        elif key == curses.KEY_DOWN:
            if self.search_results:
                self.search_cursor = min(len(self.search_results) - 1, self.search_cursor + 1)
        elif key == ord('\n') or key == curses.KEY_ENTER:
            if self.search_results and 0 <= self.search_cursor < len(self.search_results):
                self.selected = self.search_results[self.search_cursor][0]
                self.detail_element = self.element_by_num.get(self.selected)
                if self.detail_element:
                    self.mode = "detail"
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            self.search_query = self.search_query[:-1]
        elif 32 <= key <= 126:
            self.search_query += chr(key)
        return True

    def _handle_filter_input(self, key):
        if key == 27:  # ESC
            self.mode = "table"
            return True
        elif key == curses.KEY_UP:
            self.filter_cursor = max(0, self.filter_cursor - 1)
        elif key == curses.KEY_DOWN:
            self.filter_cursor = min(len(self.filter_categories) - 1, self.filter_cursor + 1)
        elif key == ord('\n') or key == curses.KEY_ENTER:
            cat = self.filter_categories[self.filter_cursor]
            if self.filter_category == cat:
                self.filter_category = None
            else:
                self.filter_category = cat
            self.mode = "table"
        elif key == ord('c') or key == ord('C'):
            self.filter_category = None
            self.mode = "table"
        return True

    def _handle_detail_input(self, key):
        if key == 27 or key == ord('\n') or key == curses.KEY_ENTER:
            self.mode = "table"
        elif key == curses.KEY_LEFT:
            if self.detail_element and self.detail_element[0] > 1:
                self.detail_element = self.element_by_num[self.detail_element[0] - 1]
                self.selected = self.detail_element[0]
        elif key == curses.KEY_RIGHT:
            if self.detail_element and self.detail_element[0] < 118:
                self.detail_element = self.element_by_num[self.detail_element[0] + 1]
                self.selected = self.detail_element[0]
        return True


def main(stdscr):
    app = PeriodicTableApp(stdscr)
    app.run()


if __name__ == "__main__":
    curses.wrapper(main)