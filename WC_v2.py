"""
FIFA World Cup 2026 — 80-Variable Monte Carlo Simulator v4
===========================================================
11 variable categories, 50 000 simulations, stage W/L/D tracking,
72 game-wise group predictions, 4 matplotlib PNG charts.

Usage:
    python WC_v2.py                          # full run, 50 000 sims
    python WC_v2.py --sims 10000
    python WC_v2.py --match "France" "Spain"
    python WC_v2.py --team "England"
    python WC_v2.py --games                  # group-match predictions
    python WC_v2.py --stages                 # W/L/D by stage table
    python WC_v2.py --charts                 # generate 4 PNG files
    python WC_v2.py --json
"""
import argparse, bisect, json, math, os, random, sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from itertools import combinations

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import numpy as np
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — CORE RATINGS
# ═══════════════════════════════════════════════════════════════════════════════
ELO = {
    "Spain":2157,"Argentina":2115,"France":2063,"England":2024,
    "Brazil":1991,"Portugal":2028,"Colombia":1982,"Netherlands":1960,
    "Norway":1930,"Germany":1925,"Uruguay":1920,"Morocco":1905,
    "Belgium":1895,"Japan":1885,"Switzerland":1875,"USA":1865,
    "Turkey":1855,"Croatia":1848,"Senegal":1840,"South Korea":1835,
    "Mexico":1832,"Austria":1828,"Ecuador":1820,"Ivory Coast":1810,
    "Sweden":1805,"Algeria":1790,"Canada":1785,"Scotland":1780,
    "Iran":1765,"Australia":1755,"Egypt":1748,"Ghana":1735,
    "Tunisia":1720,"Paraguay":1715,"Saudi Arabia":1705,"Czechia":1700,
    "Bosnia":1690,"Congo DR":1665,"South Africa":1658,"New Zealand":1620,
    "Panama":1615,"Uzbekistan":1608,"Cabo Verde":1600,"Jordan":1580,
    "Iraq":1570,"Qatar":1555,"Curacao":1510,"Haiti":1495,
}

FIFA_PTS = {
    "Argentina":1868,"France":1843,"Spain":1833,"England":1793,
    "Brazil":1778,"Belgium":1773,"Portugal":1795,"Netherlands":1748,
    "Germany":1743,"Croatia":1739,"Colombia":1718,"Uruguay":1710,
    "Morocco":1706,"Senegal":1700,"USA":1688,"Japan":1681,
    "Switzerland":1673,"Mexico":1668,"South Korea":1652,"Norway":1645,
    "Austria":1641,"Turkey":1628,"Ecuador":1620,"Algeria":1605,
    "Canada":1598,"Ghana":1590,"Ivory Coast":1585,"Australia":1578,
    "Sweden":1570,"Iran":1563,"Scotland":1558,"Egypt":1550,
    "Tunisia":1542,"Paraguay":1530,"Saudi Arabia":1522,"Czechia":1518,
    "Bosnia":1510,"South Africa":1498,"Uzbekistan":1483,"Congo DR":1478,
    "Cabo Verde":1465,"Panama":1458,"New Zealand":1445,"Jordan":1438,
    "Iraq":1430,"Qatar":1418,"Curacao":1395,"Haiti":1378,
}

FLAGS = {
    "France":"🇫🇷","Spain":"🇪🇸","Argentina":"🇦🇷","England":"ENG",
    "Brazil":"🇧🇷","Portugal":"🇵🇹","Germany":"🇩🇪","Netherlands":"🇳🇱",
    "Morocco":"🇲🇦","USA":"🇺🇸","Colombia":"🇨🇴","Belgium":"🇧🇪",
    "Uruguay":"🇺🇾","Japan":"🇯🇵","Mexico":"🇲🇽","Senegal":"🇸🇳",
    "Croatia":"🇭🇷","Switzerland":"🇨🇭","South Korea":"🇰🇷","Ecuador":"🇪🇨",
    "Austria":"🇦🇹","Canada":"🇨🇦","Norway":"🇳🇴","Sweden":"🇸🇪",
    "Turkey":"🇹🇷","Australia":"🇦🇺","Ghana":"🇬🇭","Iran":"🇮🇷",
    "Egypt":"🇪🇬","Algeria":"🇩🇿","Ivory Coast":"🇨🇮","Scotland":"SCO",
    "Paraguay":"🇵🇾","Tunisia":"🇹🇳","Saudi Arabia":"🇸🇦","South Africa":"🇿🇦",
    "Czechia":"🇨🇿","Bosnia":"🇧🇦","Qatar":"🇶🇦","Haiti":"🇭🇹",
    "Jordan":"🇯🇴","Iraq":"🇮🇶","New Zealand":"🇳🇿","Cabo Verde":"🇨🇻",
    "Curacao":"🇨🇼","Panama":"🇵🇦","Congo DR":"🇨🇩","Uzbekistan":"🇺🇿",
}

GROUPS = {
    "A":["Mexico","South Korea","South Africa","Czechia"],
    "B":["Canada","Switzerland","Bosnia","Qatar"],
    "C":["Brazil","Morocco","Scotland","Haiti"],
    "D":["USA","Turkey","Australia","Paraguay"],
    "E":["Germany","Ivory Coast","Ecuador","Curacao"],
    "F":["Netherlands","Japan","Sweden","Tunisia"],
    "G":["Belgium","Egypt","Iran","New Zealand"],
    "H":["Spain","Uruguay","Saudi Arabia","Cabo Verde"],
    "I":["France","Senegal","Norway","Iraq"],
    "J":["Argentina","Austria","Algeria","Jordan"],
    "K":["Portugal","Colombia","Congo DR","Uzbekistan"],
    "L":["England","Croatia","Ghana","Panama"],
}

HOSTS = {"USA","Canada","Mexico"}

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — FORM (last 5 + last 10)
# ═══════════════════════════════════════════════════════════════════════════════
FORM_RESULTS = {
    "Spain":       ["W","W","W","W","D"],"Argentina":   ["W","W","D","W","L"],
    "France":      ["W","W","D","W","W"],"England":     ["W","W","W","W","W"],
    "Brazil":      ["L","W","W","D","L"],"Portugal":    ["W","W","W","W","D"],
    "Colombia":    ["W","W","W","D","W"],"Netherlands": ["W","W","D","W","W"],
    "Norway":      ["W","D","W","W","W"],"Germany":     ["W","W","W","D","W"],
    "Uruguay":     ["W","W","D","W","W"],"Morocco":     ["W","W","W","D","W"],
    "Belgium":     ["W","D","W","W","L"],"Japan":       ["W","W","D","W","W"],
    "Switzerland": ["W","W","D","W","D"],"USA":         ["W","W","W","D","W"],
    "Turkey":      ["W","W","D","W","D"],"Croatia":     ["W","D","W","L","W"],
    "Senegal":     ["W","W","D","W","D"],"South Korea": ["D","W","W","D","L"],
    "Mexico":      ["W","W","W","D","W"],"Austria":     ["W","W","W","D","W"],
    "Ecuador":     ["W","D","W","W","D"],"Ivory Coast": ["W","W","D","W","W"],
    "Sweden":      ["W","W","D","W","D"],"Algeria":     ["W","D","W","D","L"],
    "Canada":      ["W","W","D","W","W"],"Scotland":    ["W","D","W","W","D"],
    "Iran":        ["W","D","W","D","W"],"Australia":   ["D","W","D","W","L"],
    "Egypt":       ["W","D","W","D","W"],"Ghana":       ["D","W","D","W","L"],
    "Tunisia":     ["W","D","D","W","L"],"Paraguay":    ["D","L","W","D","W"],
    "Saudi Arabia":["W","D","W","L","D"],"Czechia":     ["W","D","W","D","D"],
    "Bosnia":      ["W","D","D","W","L"],"Congo DR":    ["W","D","W","D","L"],
    "South Africa":["W","L","D","L","L"],"New Zealand": ["D","W","L","D","W"],
    "Panama":      ["W","D","L","W","D"],"Uzbekistan":  ["W","W","D","D","L"],
    "Cabo Verde":  ["W","D","W","L","D"],"Jordan":      ["D","L","W","D","D"],
    "Iraq":        ["W","D","D","L","L"],"Qatar":       ["L","D","W","L","D"],
    "Curacao":     ["D","L","L","W","D"],"Haiti":       ["L","D","L","W","L"],
}

# (W, D, L) in last 10 official matches
FORM_10 = {
    "Spain":(8,1,1),"France":(7,2,1),"Argentina":(7,1,2),"England":(9,1,0),
    "Brazil":(5,2,3),"Portugal":(8,1,1),"Colombia":(7,2,1),"Netherlands":(7,2,1),
    "Norway":(7,2,1),"Germany":(7,2,1),"Uruguay":(7,2,1),"Morocco":(8,1,1),
    "Belgium":(6,2,2),"Japan":(7,2,1),"Switzerland":(7,2,1),"USA":(7,2,1),
    "Turkey":(7,1,2),"Croatia":(5,3,2),"Senegal":(7,2,1),"South Korea":(5,3,2),
    "Mexico":(7,2,1),"Austria":(8,1,1),"Ecuador":(6,3,1),"Ivory Coast":(7,2,1),
    "Sweden":(7,1,2),"Algeria":(5,3,2),"Canada":(7,2,1),"Scotland":(6,2,2),
    "Iran":(6,2,2),"Australia":(5,3,2),"Egypt":(6,2,2),"Ghana":(5,2,3),
    "Tunisia":(5,2,3),"Paraguay":(4,3,3),"Saudi Arabia":(5,2,3),"Czechia":(5,3,2),
    "Bosnia":(5,2,3),"Congo DR":(5,2,3),"South Africa":(3,2,5),"New Zealand":(4,3,3),
    "Panama":(4,3,3),"Uzbekistan":(5,2,3),"Cabo Verde":(5,2,3),"Jordan":(3,3,4),
    "Iraq":(4,2,4),"Qatar":(3,2,5),"Curacao":(3,2,5),"Haiti":(2,2,6),
}

def form_score(team):
    w = [0.30,0.25,0.20,0.15,0.10]
    r = FORM_RESULTS.get(team,["D","D","D","D","D"])
    v = {"W":1.0,"D":0.5,"L":0.0}
    return sum(w[i]*v.get(r[i],0.5) for i in range(5))

def form10_score(team):
    W,D,L = FORM_10.get(team,(5,3,2))
    return (W + 0.5*D) / 10.0

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — ATTACK STATS  (xG, gpg, shots/90, SOT/90, big_chances, sp_xg)
# ═══════════════════════════════════════════════════════════════════════════════
ATTACK_STATS = {
    "France":      (2.10,2.40,15.5,5.5,3.5,0.28),"Spain":       (2.05,2.20,16.0,5.8,3.8,0.25),
    "England":     (1.95,2.10,14.0,5.2,3.2,0.30),"Germany":     (2.00,2.15,15.0,5.5,3.5,0.22),
    "Norway":      (2.20,2.30,14.5,5.8,3.8,0.20),"Brazil":      (1.85,1.90,14.0,5.0,3.0,0.18),
    "Portugal":    (1.98,2.12,15.0,5.5,3.5,0.24),"Argentina":   (1.80,1.95,13.5,4.8,3.0,0.20),
    "Netherlands": (1.85,2.00,14.0,5.0,3.0,0.22),"Belgium":     (1.75,1.95,13.0,4.5,2.8,0.20),
    "Colombia":    (1.70,1.80,13.0,4.5,2.5,0.18),"Morocco":     (1.55,1.65,12.0,4.0,2.2,0.22),
    "Uruguay":     (1.60,1.70,12.5,4.2,2.5,0.20),"Japan":       (1.65,1.75,13.0,4.5,2.5,0.18),
    "Switzerland": (1.65,1.75,12.5,4.2,2.5,0.20),"USA":         (1.60,1.70,12.5,4.2,2.5,0.22),
    "Austria":     (1.70,1.85,13.0,4.5,2.8,0.20),"Mexico":      (1.55,1.65,12.0,4.0,2.2,0.18),
    "Ivory Coast": (1.50,1.65,12.0,4.0,2.0,0.15),"Ecuador":     (1.45,1.55,11.5,3.8,2.0,0.18),
    "Turkey":      (1.55,1.70,12.0,4.0,2.2,0.18),"Senegal":     (1.50,1.60,12.0,4.0,2.0,0.15),
    "Croatia":     (1.45,1.55,11.5,3.8,2.0,0.20),"South Korea": (1.40,1.50,11.5,3.8,2.0,0.15),
    "Canada":      (1.50,1.65,12.0,4.0,2.2,0.18),"Scotland":    (1.35,1.45,11.0,3.5,1.8,0.22),
    "Sweden":      (1.75,1.85,13.5,4.8,2.8,0.18),"Algeria":     (1.40,1.50,11.0,3.5,1.8,0.18),
    "Iran":        (1.30,1.40,10.5,3.2,1.5,0.15),"Australia":   (1.30,1.40,10.5,3.2,1.5,0.18),
    "Egypt":       (1.35,1.45,11.0,3.5,1.8,0.15),"Ghana":       (1.30,1.45,10.5,3.2,1.8,0.15),
    "Tunisia":     (1.25,1.35,10.0,3.0,1.5,0.18),"Paraguay":    (1.20,1.30,10.0,3.0,1.5,0.15),
    "Saudi Arabia":(1.20,1.30,10.0,3.0,1.5,0.15),"Czechia":     (1.35,1.45,11.0,3.5,1.8,0.20),
    "Bosnia":      (1.25,1.40,10.5,3.2,1.5,0.18),"Congo DR":    (1.20,1.30,10.0,3.0,1.5,0.15),
    "South Africa":(1.15,1.25, 9.5,2.8,1.2,0.12),"New Zealand": (1.10,1.20, 9.0,2.5,1.0,0.12),
    "Panama":      (1.10,1.20, 9.0,2.5,1.0,0.12),"Uzbekistan":  (1.15,1.25, 9.5,2.8,1.2,0.12),
    "Cabo Verde":  (1.10,1.20, 9.0,2.5,1.0,0.12),"Jordan":      (1.00,1.10, 8.5,2.2,0.8,0.10),
    "Iraq":        (1.00,1.10, 8.5,2.2,0.8,0.10),"Qatar":       (0.95,1.05, 8.0,2.0,0.7,0.10),
    "Curacao":     (0.90,1.00, 7.5,1.8,0.6,0.08),"Haiti":       (0.85,0.95, 7.0,1.5,0.5,0.08),
}

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — DEFENSE STATS  (xGA, gcpg, big_chances_all, cs_rate, aerial_win, def_errors)
# ═══════════════════════════════════════════════════════════════════════════════
DEFENSE_STATS = {
    "France":      (0.75,0.70,1.8,0.45,0.55,0.15),"England":     (0.55,0.45,1.2,0.55,0.60,0.10),
    "Spain":       (0.70,0.65,1.5,0.48,0.52,0.12),"Germany":     (0.85,0.90,2.0,0.38,0.58,0.18),
    "Brazil":      (0.90,0.95,2.0,0.40,0.50,0.20),"Portugal":    (0.65,0.70,1.5,0.48,0.54,0.11),
    "Argentina":   (0.80,0.85,1.8,0.42,0.52,0.15),"Netherlands": (0.85,0.90,2.0,0.38,0.55,0.18),
    "Norway":      (0.90,1.00,2.2,0.35,0.62,0.20),"Belgium":     (0.85,0.95,2.0,0.38,0.55,0.18),
    "Morocco":     (0.65,0.60,1.4,0.55,0.58,0.10),"Uruguay":     (0.75,0.70,1.6,0.48,0.58,0.15),
    "Colombia":    (0.90,0.95,2.0,0.35,0.50,0.20),"Japan":       (0.75,0.80,1.8,0.40,0.48,0.15),
    "Switzerland": (0.80,0.85,1.8,0.40,0.55,0.15),"USA":         (0.85,0.90,2.0,0.38,0.52,0.18),
    "Austria":     (0.80,0.85,1.8,0.40,0.55,0.15),"Mexico":      (0.90,0.95,2.0,0.38,0.50,0.20),
    "Ivory Coast": (0.95,1.00,2.2,0.35,0.50,0.22),"Ecuador":     (0.90,0.95,2.0,0.35,0.50,0.20),
    "Turkey":      (0.95,1.05,2.2,0.35,0.52,0.22),"Sweden":      (0.90,0.95,2.0,0.38,0.62,0.18),
    "Senegal":     (0.85,0.90,2.0,0.38,0.55,0.18),"Croatia":     (0.75,0.80,1.6,0.45,0.55,0.15),
    "South Korea": (0.95,1.00,2.2,0.35,0.50,0.22),"Canada":      (1.00,1.05,2.2,0.32,0.52,0.25),
    "Scotland":    (0.95,1.00,2.0,0.35,0.58,0.20),"Algeria":     (0.95,1.05,2.2,0.35,0.52,0.22),
    "Iran":        (0.90,0.95,2.0,0.38,0.52,0.20),"Australia":   (1.10,1.15,2.5,0.30,0.55,0.25),
    "Egypt":       (0.95,1.00,2.0,0.38,0.52,0.20),"Ghana":       (1.00,1.10,2.2,0.35,0.52,0.25),
    "Tunisia":     (1.00,1.05,2.2,0.35,0.52,0.22),"Paraguay":    (1.05,1.10,2.2,0.32,0.55,0.25),
    "Saudi Arabia":(1.05,1.15,2.5,0.30,0.50,0.28),"Czechia":     (1.00,1.05,2.2,0.35,0.58,0.22),
    "Bosnia":      (1.05,1.10,2.2,0.32,0.52,0.25),"Congo DR":    (1.05,1.15,2.5,0.30,0.50,0.28),
    "South Africa":(1.20,1.30,2.8,0.25,0.50,0.32),"New Zealand": (1.25,1.35,3.0,0.22,0.52,0.35),
    "Panama":      (1.20,1.25,2.8,0.25,0.52,0.32),"Uzbekistan":  (1.15,1.25,2.5,0.28,0.50,0.30),
    "Cabo Verde":  (1.20,1.30,2.8,0.25,0.52,0.32),"Jordan":      (1.30,1.40,3.0,0.20,0.50,0.38),
    "Iraq":        (1.25,1.35,2.8,0.22,0.50,0.35),"Qatar":       (1.30,1.45,3.2,0.18,0.48,0.40),
    "Curacao":     (1.45,1.60,3.5,0.15,0.45,0.45),"Haiti":       (1.50,1.65,3.8,0.12,0.42,0.50),
}

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — SQUAD QUALITY
# ═══════════════════════════════════════════════════════════════════════════════
MARKET_VALUE = {
    "France":1530,"England":1310,"Spain":1260,"Portugal":1120,"Germany":998,
    "Brazil":912,"Netherlands":837,"Argentina":818,"Norway":780,"Belgium":710,
    "Colombia":650,"Morocco":568,"Senegal":550,"Turkey":550,"Uruguay":480,
    "Japan":460,"Switzerland":450,"USA":444,"Austria":430,"Sweden":390,
    "Croatia":370,"Ivory Coast":617,"South Korea":280,"Ecuador":320,"Mexico":295,
    "Canada":228,"Scotland":320,"Algeria":200,"Egypt":190,"Czechia":310,
    "Iran":120,"Australia":180,"Tunisia":150,"Paraguay":140,"Saudi Arabia":160,
    "Bosnia":135,"South Africa":110,"Congo DR":105,"Uzbekistan":85,
    "Cabo Verde":72,"Panama":68,"New Zealand":65,"Jordan":22,"Iraq":25,
    "Qatar":23,"Curacao":30,"Haiti":18,"Ghana":250,"Ghana":250,
}

STARTING_XI_VALUE = {
    "France":1050,"England":950,"Spain":880,"Germany":720,"Portugal":820,
    "Brazil":680,"Netherlands":620,"Argentina":600,"Norway":580,"Belgium":520,
    "Colombia":450,"Ivory Coast":450,"Morocco":380,"Turkey":380,"Senegal":380,
    "Uruguay":360,"Japan":330,"Switzerland":330,"Austria":320,"USA":320,
    "Sweden":290,"Scotland":230,"Croatia":270,"Ecuador":220,"Czechia":220,
    "Canada":170,"South Korea":200,"Mexico":200,"Algeria":140,"Egypt":140,
    "Ghana":180,"Iran":90,"Australia":130,"Tunisia":110,"Paraguay":100,
    "Saudi Arabia":120,"Bosnia":95,"Congo DR":75,"South Africa":80,
    "Uzbekistan":62,"Cabo Verde":52,"Panama":50,"New Zealand":48,
    "Jordan":16,"Iraq":18,"Qatar":17,"Curacao":22,"Haiti":13,
}

TOP5_COUNT = {
    "France":22,"England":22,"Spain":19,"Germany":18,"Portugal":18,
    "Brazil":14,"Netherlands":15,"Belgium":14,"Argentina":12,"Norway":10,
    "Colombia":10,"Uruguay":10,"Morocco":8,"Switzerland":9,"Japan":9,
    "Sweden":8,"Ecuador":7,"Austria":8,"Turkey":7,"Senegal":7,"Croatia":6,
    "USA":7,"Canada":7,"Ivory Coast":8,"Ghana":6,"South Korea":5,"Mexico":3,
    "Scotland":6,"Algeria":5,"Egypt":4,"Iran":2,"Australia":4,"Czechia":5,
    "Tunisia":3,"Paraguay":3,"Saudi Arabia":2,"Bosnia":5,"South Africa":2,
    "Congo DR":3,"Uzbekistan":1,"Cabo Verde":2,"Panama":2,"New Zealand":1,
    "Jordan":0,"Iraq":0,"Qatar":0,"Curacao":2,"Haiti":0,
}

CL_PLAYERS = {
    "France":18,"England":18,"Spain":15,"Germany":14,"Portugal":16,
    "Netherlands":12,"Belgium":12,"Brazil":10,"Norway":8,"Switzerland":8,
    "Colombia":7,"Argentina":8,"Uruguay":6,"Ivory Coast":6,"Sweden":6,
    "Scotland":5,"USA":5,"Canada":5,"Japan":6,"Turkey":5,"Croatia":5,
    "Senegal":5,"South Korea":4,"Ecuador":4,"Algeria":4,"Czechia":4,
    "Mexico":1,"Austria":6,"Ghana":4,"Egypt":2,"Iran":1,"Australia":3,
    "Bosnia":3,"Tunisia":2,"Paraguay":2,"Cabo Verde":1,"Panama":1,
    "Saudi Arabia":1,"Congo DR":2,"South Africa":1,"Uzbekistan":0,
    "New Zealand":0,"Jordan":0,"Iraq":0,"Qatar":0,"Curacao":1,"Haiti":0,
}

AVG_CAPS = {
    "Belgium":65,"Brazil":58,"Argentina":60,"Portugal":55,"Uruguay":55,
    "Croatia":62,"Mexico":58,"France":52,"South Korea":52,"Japan":48,
    "Turkey":48,"Senegal":48,"Colombia":48,"Egypt":55,"Iran":52,"Qatar":52,
    "Germany":45,"England":42,"Morocco":42,"Netherlands":42,"Australia":42,
    "Scotland":42,"Cabo Verde":42,"Bosnia":45,"Panama":45,"Jordan":45,
    "Iraq":48,"Saudi Arabia":48,"Paraguay":52,"Czechia":42,"Tunisia":48,
    "Algeria":48,"Ghana":52,"Ecuador":40,"Norway":38,"Spain":38,
    "Austria":35,"USA":32,"Canada":32,"Sweden":55,"Switzerland":55,
    "Uzbekistan":38,"New Zealand":38,"Ivory Coast":48,"Congo DR":42,
    "South Africa":48,"Curacao":38,"Haiti":45,
}

WC_EXPERIENCE = {
    "Brazil":2.2,"Argentina":2.0,"Mexico":2.0,"Uruguay":2.0,"Germany":1.8,
    "France":1.8,"Croatia":1.8,"Spain":1.5,"Netherlands":1.5,"Belgium":1.5,
    "Japan":1.5,"South Korea":1.5,"Switzerland":1.5,"Saudi Arabia":1.2,
    "Morocco":1.2,"Iran":1.2,"Ghana":1.2,"Tunisia":1.2,"Paraguay":1.2,
    "Colombia":1.2,"Portugal":2.0,"Egypt":0.8,"Australia":1.2,
    "England":1.2,"USA":1.2,"Norway":0.5,"Austria":0.8,"Algeria":0.8,
    "Czechia":0.8,"Sweden":0.8,"Ecuador":1.0,"Turkey":1.0,"Senegal":1.0,
    "Canada":0.5,"Scotland":0.2,"Bosnia":0.5,"Congo DR":0.5,"Iraq":0.5,
    "Qatar":0.5,"South Africa":0.8,"Ivory Coast":1.2,"Uzbekistan":0.2,
    "Cabo Verde":0.2,"Jordan":0.2,"Curacao":0.2,"Haiti":0.5,
    "Panama":0.5,"New Zealand":0.5,
}

BENCH_STRENGTH = {
    "France":9,"Spain":9,"England":9,"Germany":8,"Argentina":8,"Brazil":8,
    "Portugal":8,"Netherlands":8,"Norway":7,"Belgium":7,"Colombia":7,
    "Morocco":7,"Uruguay":7,"Japan":7,"Switzerland":7,"USA":6,"Turkey":6,
    "Austria":6,"Senegal":6,"Croatia":6,"Sweden":6,"South Korea":5,
    "Ecuador":5,"Canada":5,"Mexico":5,"Scotland":5,"Ivory Coast":6,
    "Algeria":4,"Egypt":4,"Iran":4,"Australia":4,"Ghana":4,"Tunisia":4,
    "Czechia":5,"Saudi Arabia":4,"Bosnia":4,"Congo DR":3,"South Africa":3,
    "Paraguay":4,"Uzbekistan":3,"Cabo Verde":3,"Panama":3,"New Zealand":3,
    "Jordan":2,"Iraq":2,"Qatar":2,"Curacao":2,"Haiti":2,
}

SQUAD_AGE = {
    "France":26.5,"Spain":25.5,"England":26.8,"Germany":26.2,"Argentina":28.5,
    "Brazil":26.5,"Portugal":27.8,"Netherlands":26.5,"Norway":26.2,"Belgium":30.5,
    "Colombia":27.5,"Uruguay":28.0,"Morocco":27.0,"Japan":27.5,"Switzerland":28.5,
    "USA":26.5,"Austria":27.0,"Turkey":28.0,"Senegal":28.5,"South Korea":28.8,
    "Mexico":29.5,"Sweden":28.0,"Ecuador":27.5,"Canada":26.8,"Croatia":30.5,
    "Scotland":29.0,"Ivory Coast":28.0,"Algeria":29.0,"Iran":28.5,"Australia":27.5,
    "Egypt":29.0,"Ghana":27.5,"Tunisia":28.5,"Paraguay":28.0,"Saudi Arabia":28.5,
    "Czechia":28.5,"Bosnia":29.5,"Congo DR":27.5,"South Africa":28.0,
    "New Zealand":27.5,"Panama":29.0,"Uzbekistan":27.0,"Cabo Verde":28.0,
    "Jordan":28.5,"Iraq":28.0,"Qatar":28.5,"Curacao":28.0,"Haiti":28.0,
}

STARTING_XI_AGE = {
    "France":26.2,"Spain":25.0,"England":26.5,"Germany":25.8,"Argentina":28.8,
    "Brazil":26.5,"Portugal":27.8,"Netherlands":26.2,"Norway":26.0,"Belgium":30.2,
    "Colombia":27.5,"Uruguay":28.5,"Morocco":27.2,"Japan":27.2,"Switzerland":28.2,
    "USA":26.2,"Austria":26.8,"Turkey":28.0,"Senegal":28.2,"South Korea":28.5,
    "Mexico":29.5,"Sweden":28.0,"Ecuador":27.5,"Canada":26.5,"Croatia":30.8,
    "Scotland":29.0,"Ivory Coast":28.5,"Algeria":29.0,"Iran":28.5,"Australia":27.5,
    "Egypt":29.0,"Ghana":27.5,"Tunisia":28.5,"Paraguay":28.0,"Saudi Arabia":28.5,
    "Czechia":28.5,"Bosnia":29.5,"Congo DR":27.5,"South Africa":28.0,
    "New Zealand":27.5,"Panama":29.0,"Uzbekistan":27.0,"Cabo Verde":28.0,
    "Jordan":28.5,"Iraq":28.0,"Qatar":28.5,"Curacao":28.0,"Haiti":28.0,
}

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — GOALKEEPER STATS
# (save_pct, psxg_diff, cs_per_10, pen_save_pct, distribution, gk_errors_per_10)
# ═══════════════════════════════════════════════════════════════════════════════
GK_STATS = {
    "Argentina":   (0.82,+0.25,4.5,0.45,0.82,0.1),  # E. Martinez
    "England":     (0.76,+0.12,5.5,0.35,0.80,0.1),  # Pickford
    "Morocco":     (0.78,+0.20,5.5,0.45,0.82,0.1),  # Bono
    "Croatia":     (0.76,+0.12,4.0,0.50,0.78,0.2),  # Livakovic
    "Portugal":    (0.76,+0.15,4.5,0.45,0.85,0.1),  # Diogo Costa
    "France":      (0.78,+0.15,4.0,0.30,0.88,0.1),  # Maignan
    "Spain":       (0.74,+0.08,4.5,0.25,0.88,0.2),  # Unai Simon
    "Germany":     (0.76,+0.20,4.0,0.25,0.90,0.1),  # Neuer
    "Brazil":      (0.78,+0.18,4.0,0.25,0.90,0.1),  # Alisson
    "Netherlands": (0.74,+0.10,4.0,0.20,0.85,0.2),  # Verbruggen
    "Belgium":     (0.75,+0.08,3.5,0.20,0.82,0.2),  # Casteels
    "Japan":       (0.74,+0.05,4.0,0.30,0.78,0.2),
    "Switzerland": (0.75,+0.10,4.0,0.20,0.82,0.2),  # Kobel
    "Uruguay":     (0.74,+0.05,4.5,0.20,0.80,0.2),  # Rochet
    "Colombia":    (0.72,+0.02,3.5,0.15,0.78,0.3),
    "Norway":      (0.72,+0.05,3.5,0.15,0.78,0.3),
    "Mexico":      (0.74,+0.05,3.5,0.20,0.80,0.2),
    "USA":         (0.73,+0.03,3.5,0.20,0.80,0.2),  # Turner
    "Turkey":      (0.72,+0.02,3.5,0.15,0.78,0.3),
    "Senegal":     (0.72,+0.02,3.5,0.15,0.78,0.3),
    "Austria":     (0.73,+0.03,3.8,0.20,0.80,0.2),
    "Sweden":      (0.73,+0.05,3.5,0.20,0.80,0.2),  # Olsen
    "Scotland":    (0.72,+0.02,3.5,0.20,0.80,0.2),
    "South Korea": (0.72,+0.02,3.5,0.18,0.78,0.2),
    "Canada":      (0.72,+0.02,3.2,0.18,0.78,0.3),
    "Ecuador":     (0.70, 0.00,3.0,0.15,0.76,0.3),
    "Egypt":       (0.72,+0.02,3.5,0.15,0.78,0.3),
    "Algeria":     (0.70, 0.00,3.0,0.15,0.76,0.3),
    "Iran":        (0.70, 0.00,3.5,0.15,0.76,0.3),
    "Ghana":       (0.70, 0.00,3.0,0.15,0.75,0.3),
    "Australia":   (0.72,+0.02,3.0,0.18,0.80,0.2),  # Ryan
    "Saudi Arabia":(0.73,+0.05,3.5,0.25,0.80,0.2),  # Al-Owais
    "Czechia":     (0.72,+0.02,3.2,0.18,0.80,0.2),
    "Ivory Coast": (0.70, 0.00,3.0,0.15,0.75,0.3),
    "Tunisia":     (0.70, 0.00,3.0,0.15,0.75,0.3),
    "Paraguay":    (0.70, 0.00,3.0,0.15,0.75,0.3),
    "Bosnia":      (0.70, 0.00,3.0,0.15,0.75,0.3),
    "Congo DR":    (0.68,-0.05,2.5,0.12,0.72,0.4),
    "South Africa":(0.68,-0.05,2.5,0.12,0.72,0.4),
    "New Zealand": (0.68,-0.05,2.5,0.12,0.72,0.4),
    "Panama":      (0.68,-0.05,2.5,0.12,0.72,0.4),
    "Uzbekistan":  (0.67,-0.08,2.5,0.10,0.70,0.4),
    "Cabo Verde":  (0.68,-0.05,2.5,0.12,0.70,0.4),
    "Jordan":      (0.66,-0.10,2.0,0.10,0.68,0.5),
    "Iraq":        (0.66,-0.10,2.0,0.10,0.68,0.5),
    "Qatar":       (0.65,-0.12,1.8,0.08,0.65,0.5),
    "Curacao":     (0.63,-0.15,1.5,0.08,0.62,0.6),
    "Haiti":       (0.62,-0.18,1.5,0.05,0.60,0.7),
    "Scotland_":   (0.72,+0.02,3.5,0.20,0.80,0.2),
}

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — TACTICAL STATS
# (possession, ppda, aerial_win, sp_xg_att, directness, fullback_overlap)
# ═══════════════════════════════════════════════════════════════════════════════
TACTICAL = {
    "Spain":       (0.65,6.5,0.52,0.25,0.30,0.75),"France":      (0.55,9.5,0.55,0.28,0.50,0.65),
    "England":     (0.53,10.5,0.60,0.30,0.55,0.60),"Germany":     (0.58,8.0,0.58,0.22,0.45,0.65),
    "Argentina":   (0.52,12.0,0.52,0.18,0.55,0.55),"Brazil":      (0.58,9.0,0.50,0.18,0.42,0.70),
    "Portugal":    (0.55,9.0,0.53,0.24,0.49,0.67), "Netherlands": (0.55,8.5,0.55,0.22,0.48,0.65),
    "Norway":      (0.48,11.0,0.62,0.20,0.65,0.58),"Belgium":     (0.52,10.5,0.55,0.22,0.52,0.62),
    "Morocco":     (0.45,7.0,0.58,0.20,0.45,0.55), "Uruguay":     (0.48,12.5,0.58,0.22,0.58,0.55),
    "Colombia":    (0.50,11.0,0.50,0.18,0.52,0.60),"Japan":       (0.52,8.5,0.48,0.18,0.50,0.60),
    "Switzerland": (0.52,9.5,0.55,0.20,0.50,0.60), "USA":         (0.50,10.5,0.55,0.22,0.52,0.62),
    "Austria":     (0.52,7.5,0.55,0.20,0.48,0.62), "Mexico":      (0.50,11.5,0.52,0.18,0.50,0.58),
    "Turkey":      (0.50,10.5,0.55,0.18,0.52,0.58),"Senegal":     (0.48,11.0,0.55,0.18,0.52,0.55),
    "Croatia":     (0.50,12.0,0.55,0.22,0.52,0.55),"Sweden":      (0.48,11.5,0.62,0.20,0.58,0.58),
    "Ecuador":     (0.48,11.5,0.52,0.18,0.52,0.55),"South Korea": (0.48,10.5,0.50,0.15,0.52,0.58),
    "Canada":      (0.48,10.5,0.55,0.18,0.55,0.58),"Scotland":    (0.48,11.0,0.60,0.22,0.58,0.55),
    "Algeria":     (0.48,11.5,0.55,0.18,0.52,0.55),"Iran":        (0.45,13.0,0.55,0.18,0.55,0.50),
    "Australia":   (0.46,12.0,0.58,0.20,0.58,0.55),"Egypt":       (0.46,12.5,0.52,0.18,0.55,0.52),
    "Ghana":       (0.46,12.5,0.52,0.18,0.55,0.52),"Tunisia":     (0.45,13.0,0.52,0.18,0.55,0.50),
    "Paraguay":    (0.45,13.0,0.55,0.18,0.55,0.50),"Saudi Arabia":(0.46,13.0,0.52,0.18,0.55,0.50),
    "Czechia":     (0.48,12.0,0.58,0.20,0.52,0.55),"Bosnia":      (0.46,12.5,0.55,0.18,0.55,0.52),
    "Ivory Coast": (0.47,12.0,0.52,0.18,0.55,0.55),"Congo DR":    (0.44,13.5,0.52,0.18,0.58,0.50),
    "South Africa":(0.44,14.0,0.52,0.15,0.58,0.48),"New Zealand": (0.44,14.0,0.55,0.15,0.58,0.48),
    "Panama":      (0.43,14.0,0.52,0.15,0.60,0.48),"Uzbekistan":  (0.44,13.5,0.52,0.15,0.58,0.48),
    "Cabo Verde":  (0.43,14.0,0.52,0.15,0.60,0.48),"Jordan":      (0.42,14.5,0.50,0.12,0.62,0.45),
    "Iraq":        (0.42,14.5,0.50,0.12,0.62,0.45),"Qatar":       (0.42,14.5,0.48,0.12,0.62,0.45),
    "Curacao":     (0.40,15.0,0.48,0.10,0.65,0.42),"Haiti":       (0.38,15.5,0.46,0.08,0.68,0.40),
}

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 8 — PLAYER AVAILABILITY
# ═══════════════════════════════════════════════════════════════════════════════
INJURY_IMPACT = {
    "Brazil":     -0.06,"Spain":      -0.04,"Argentina":  -0.03,
    "Netherlands":-0.03,"Germany":    -0.02,"England":    -0.01,
    "Portugal":    0.00,"France":     -0.01,
}

KEY_PLAYER_AVAIL = {
    "Spain":0.82,"Brazil":0.82,"Argentina":0.92,"Netherlands":0.91,
    "Germany":0.96,"England":0.97,"France":0.98,"Portugal":1.00,
    "Norway":0.98,"Belgium":0.94,"Colombia":0.97,"Morocco":0.96,
    "Uruguay":0.97,"Japan":0.98,"Switzerland":0.98,"USA":0.98,
    "Turkey":0.97,"Croatia":0.96,"Senegal":0.97,"South Korea":0.97,
    "Mexico":0.98,"Austria":0.98,"Ecuador":0.97,"Ivory Coast":0.96,
    "Sweden":0.96,"Algeria":0.97,"Canada":0.97,"Scotland":0.97,
    "Iran":0.97,"Australia":0.97,"Egypt":0.97,"Ghana":0.97,
    "Tunisia":0.97,"Paraguay":0.97,"Saudi Arabia":0.97,"Czechia":0.97,
    "Bosnia":0.97,"Congo DR":0.97,"South Africa":0.97,"New Zealand":0.97,
    "Panama":0.97,"Uzbekistan":0.97,"Cabo Verde":0.97,"Jordan":0.97,
    "Iraq":0.97,"Qatar":0.97,"Curacao":0.97,"Haiti":0.97,
}

GK_AVAIL = {t: 1.00 for t in ELO}
GK_AVAIL.update({"Brazil":0.97,"Germany":0.97})

CB_AVAIL = {t: 1.00 for t in ELO}
CB_AVAIL.update({"Argentina":0.85,"Netherlands":0.92,"Brazil":0.88,"Spain":0.92})

ST_AVAIL = {t: 1.00 for t in ELO}
ST_AVAIL.update({"Brazil":0.88,"Spain":0.90,"Netherlands":0.93})

ROTATION_RISK = {
    "Spain":0.20,"France":0.25,"England":0.20,"Germany":0.25,"Argentina":0.20,
    "Brazil":0.30,"Portugal":0.25,"Netherlands":0.25,"Norway":0.25,"Belgium":0.25,
    "Colombia":0.20,"Morocco":0.20,"Uruguay":0.20,"Japan":0.20,"Switzerland":0.20,
    "USA":0.20,"Turkey":0.20,"Austria":0.20,"Senegal":0.20,"Croatia":0.20,
    "Sweden":0.20,"South Korea":0.15,"Ecuador":0.15,"Canada":0.15,"Mexico":0.20,
    "Scotland":0.15,"Ivory Coast":0.15,"Algeria":0.15,"Egypt":0.15,"Iran":0.15,
    "Australia":0.15,"Ghana":0.15,"Tunisia":0.15,"Czechia":0.15,"Saudi Arabia":0.15,
    "Bosnia":0.10,"Congo DR":0.10,"South Africa":0.10,"Paraguay":0.10,
    "Uzbekistan":0.10,"Cabo Verde":0.10,"Panama":0.10,"New Zealand":0.10,
    "Jordan":0.05,"Iraq":0.05,"Qatar":0.05,"Curacao":0.05,"Haiti":0.05,
}

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 9 — MATCH CONTEXT
# ═══════════════════════════════════════════════════════════════════════════════
TRAVEL_FATIGUE = {
    "Mexico":0.02,"USA":0.02,"Canada":0.02,
    "Brazil":0.01,"Argentina":0.01,"Colombia":0.01,"Uruguay":0.01,
    "Ecuador":0.00,"Paraguay":0.00,"Panama":0.01,"Haiti":0.00,"Curacao":0.00,
    "England":-0.01,"France":-0.01,"Spain":-0.01,"Germany":-0.01,
    "Portugal":-0.01,"Netherlands":-0.01,"Belgium":-0.01,"Norway":-0.01,
    "Switzerland":-0.01,"Austria":-0.01,"Croatia":-0.01,"Turkey":-0.01,
    "Sweden":-0.01,"Scotland":-0.01,"Algeria":-0.01,"Morocco":-0.01,
    "Senegal":-0.01,"Egypt":-0.01,"Ivory Coast":-0.01,"South Africa":-0.01,
    "Ghana":-0.01,"Tunisia":-0.01,"Congo DR":-0.01,"Cabo Verde":-0.01,
    "Japan":-0.01,"South Korea":-0.01,"Australia":-0.02,"Iran":-0.01,
    "Saudi Arabia":-0.01,"Iraq":-0.01,"Qatar":-0.01,"Jordan":-0.01,
    "Uzbekistan":-0.02,"New Zealand":-0.02,"Czechia":-0.01,"Bosnia":-0.01,
}

HOST_MULT = 1.10
HOSTS_ELO_BONUS = 80

GROUP_VENUES = {
    "A":{"altitude":100,"temp":22},"B":{"altitude":75,"temp":20},
    "C":{"altitude":90,"temp":24},"D":{"altitude":80,"temp":28},
    "E":{"altitude":200,"temp":25},"F":{"altitude":150,"temp":26},
    "G":{"altitude":180,"temp":27},"H":{"altitude":1600,"temp":22},
    "I":{"altitude":90,"temp":23},"J":{"altitude":2240,"temp":18},
    "K":{"altitude":120,"temp":24},"L":{"altitude":80,"temp":22},
}

def _team_group(team):
    for g, ms in GROUPS.items():
        if team in ms: return g
    return None

def altitude_factor(team):
    g = _team_group(team)
    if not g: return 1.0
    alt = GROUP_VENUES[g]["altitude"]
    return 1.0 - max(0.0, (alt - 1000) / 9000)

def temp_factor(team):
    g = _team_group(team)
    if not g: return 1.0
    t = GROUP_VENUES[g]["temp"]
    if t > 32: return 0.97
    if t < 8:  return 0.99
    return 1.0

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 10 — MANAGER & DISCIPLINE
# (tenure_yrs, tournament_exp, tactical_flex, sub_impact)
# ═══════════════════════════════════════════════════════════════════════════════
MANAGER = {
    "Spain":      (3,2,0.70,0.70),"France":     (13,4,0.60,0.70),
    "Argentina":  (8,2,0.80,0.80),"England":    (1,3,0.85,0.80),
    "Germany":    (3,1,0.90,0.80),"Brazil":     (1,1,0.65,0.65),
    "Portugal":   (3,2,0.75,0.75),"Netherlands":(2,3,0.70,0.70),
    "Belgium":    (3,1,0.70,0.65),"Morocco":    (3,1,0.80,0.80),
    "Japan":      (7,3,0.65,0.70),"Norway":     (4,1,0.65,0.65),
    "Uruguay":    (2,1,0.70,0.70),"USA":        (2,1,0.70,0.70),
    "Switzerland":(4,2,0.65,0.65),"Turkey":     (3,2,0.70,0.70),
    "Croatia":    (9,3,0.70,0.75),"Sweden":     (5,1,0.65,0.65),
    "Mexico":     (2,3,0.70,0.70),"Canada":     (2,2,0.75,0.75),
    "Austria":    (4,1,0.88,0.82),"Senegal":    (10,2,0.65,0.70),
    "Scotland":   (7,2,0.65,0.65),"Colombia":   (3,1,0.70,0.70),
    "Ecuador":    (3,1,0.65,0.65),"Ivory Coast":(3,1,0.65,0.65),
    "South Korea":(2,1,0.65,0.65),"Algeria":    (2,1,0.60,0.60),
    "Iran":       (2,2,0.65,0.65),"Australia":  (2,1,0.65,0.65),
    "Egypt":      (2,1,0.60,0.60),"Ghana":      (2,0,0.55,0.55),
    "Tunisia":    (2,1,0.60,0.60),"Paraguay":   (2,0,0.60,0.60),
    "Saudi Arabia":(3,3,0.70,0.65),"Czechia":   (2,1,0.65,0.65),
    "Bosnia":     (2,0,0.60,0.60),"Congo DR":   (2,0,0.55,0.55),
    "South Africa":(2,0,0.55,0.55),"Panama":    (3,1,0.65,0.65),
    "New Zealand":(2,0,0.55,0.55),"Uzbekistan": (2,0,0.55,0.55),
    "Cabo Verde": (2,0,0.55,0.55),"Jordan":     (2,0,0.55,0.55),
    "Iraq":       (2,0,0.55,0.55),"Qatar":      (2,1,0.60,0.60),
    "Curacao":    (2,0,0.55,0.55),"Haiti":      (2,0,0.50,0.50),
}

# (cards_per_match, red_card_risk, fouls_per_match)
DISCIPLINE = {
    "Spain":      (1.8,0.03,10.5),"Germany":    (1.8,0.03,10.0),
    "France":     (1.9,0.04,11.0),"England":    (1.9,0.04,11.0),
    "Japan":      (1.8,0.03,11.0),"Switzerland":(1.9,0.03,11.0),
    "Brazil":     (2.1,0.05,12.0),"Argentina":  (2.2,0.06,12.5),
    "Portugal":   (2.0,0.04,11.5),"Netherlands":(2.0,0.04,11.0),
    "Morocco":    (2.5,0.07,13.0),"Belgium":    (2.1,0.04,11.5),
    "Colombia":   (2.3,0.06,12.5),"Uruguay":    (2.4,0.07,13.0),
    "Norway":     (2.0,0.04,11.5),"Croatia":    (2.2,0.05,12.0),
    "Turkey":     (2.5,0.07,13.5),"Senegal":    (2.2,0.05,12.0),
    "Austria":    (2.0,0.04,11.5),"Sweden":     (2.0,0.04,11.5),
    "Mexico":     (2.2,0.05,12.5),"USA":        (2.0,0.04,11.5),
    "South Korea":(2.0,0.04,11.5),"Ecuador":    (2.2,0.05,12.0),
    "Scotland":   (2.1,0.05,12.0),"Algeria":    (2.3,0.06,12.5),
    "Canada":     (2.0,0.04,11.5),"Ivory Coast":(2.3,0.06,12.5),
    "Iran":       (2.2,0.05,12.0),"Australia":  (2.1,0.05,12.0),
    "Egypt":      (2.2,0.05,12.0),"Ghana":      (2.3,0.06,12.5),
    "Tunisia":    (2.2,0.05,12.0),"Paraguay":   (2.4,0.07,13.0),
    "Saudi Arabia":(2.2,0.05,12.0),"Czechia":   (2.0,0.04,11.5),
    "Bosnia":     (2.3,0.06,12.5),"Congo DR":   (2.3,0.06,12.5),
    "South Africa":(2.3,0.06,12.5),"New Zealand":(2.0,0.04,11.0),
    "Panama":     (2.3,0.06,12.5),"Uzbekistan": (2.2,0.05,12.0),
    "Cabo Verde": (2.2,0.05,12.0),"Jordan":     (2.3,0.06,12.5),
    "Iraq":       (2.3,0.06,12.5),"Qatar":      (2.3,0.06,12.5),
    "Curacao":    (2.4,0.07,13.0),"Haiti":      (2.4,0.07,13.5),
}

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 11 — KNOCKOUT & PRESSURE + PENALTY RECORDS
# (comeback_record, after_scoring_1st, extra_time_fitness, yc_accum_risk)
# ═══════════════════════════════════════════════════════════════════════════════
PRESSURE_STATS = {
    "Spain":      (0.72,0.88,0.88,0.20),"France":     (0.68,0.85,0.88,0.28),
    "Argentina":  (0.75,0.88,0.85,0.32),"England":    (0.65,0.82,0.88,0.28),
    "Germany":    (0.70,0.88,0.90,0.22),"Brazil":     (0.68,0.82,0.88,0.30),
    "Portugal":   (0.74,0.90,0.87,0.28),"Netherlands":(0.65,0.85,0.88,0.28),
    "Morocco":    (0.80,0.92,0.90,0.35),"Croatia":    (0.78,0.90,0.88,0.32),
    "Uruguay":    (0.75,0.90,0.85,0.38),"Belgium":    (0.62,0.82,0.85,0.28),
    "Japan":      (0.65,0.85,0.90,0.25),"Norway":     (0.65,0.85,0.88,0.28),
    "Switzerland":(0.65,0.85,0.90,0.25),"USA":        (0.65,0.85,0.88,0.28),
    "Austria":    (0.65,0.85,0.90,0.28),"Colombia":   (0.68,0.85,0.85,0.32),
    "Senegal":    (0.68,0.85,0.88,0.30),"Turkey":     (0.65,0.82,0.85,0.35),
    "Sweden":     (0.68,0.88,0.90,0.28),"South Korea":(0.70,0.85,0.90,0.28),
    "Mexico":     (0.62,0.82,0.85,0.30),"Scotland":   (0.62,0.82,0.85,0.30),
    "Canada":     (0.65,0.85,0.88,0.28),"Ecuador":    (0.62,0.82,0.85,0.30),
    "Algeria":    (0.62,0.82,0.85,0.32),"Iran":       (0.65,0.85,0.88,0.30),
    "Australia":  (0.65,0.85,0.88,0.28),"Croatia":    (0.78,0.90,0.88,0.32),
    "Egypt":      (0.62,0.82,0.85,0.30),"Ghana":      (0.60,0.80,0.83,0.35),
    "Tunisia":    (0.60,0.80,0.83,0.32),"Paraguay":   (0.62,0.82,0.85,0.35),
    "Saudi Arabia":(0.60,0.80,0.83,0.32),"Czechia":   (0.65,0.85,0.88,0.28),
    "Bosnia":     (0.60,0.80,0.83,0.32),"Congo DR":   (0.58,0.78,0.80,0.35),
    "South Africa":(0.55,0.75,0.78,0.38),"Ivory Coast":(0.62,0.82,0.85,0.32),
    "New Zealand":(0.55,0.75,0.78,0.30),"Panama":     (0.55,0.75,0.78,0.32),
    "Uzbekistan": (0.55,0.75,0.78,0.30),"Cabo Verde": (0.55,0.75,0.78,0.32),
    "Jordan":     (0.50,0.72,0.75,0.35),"Iraq":       (0.50,0.72,0.75,0.35),
    "Qatar":      (0.48,0.70,0.72,0.35),"Curacao":    (0.45,0.68,0.70,0.38),
    "Haiti":      (0.42,0.65,0.68,0.40),
}

PEN_RECORD = {
    "Germany":0.86,"Croatia":0.80,"Saudi Arabia":0.80,"Argentina":0.67,
    "South Korea":0.67,"USA":0.67,"Morocco":1.00,"Belgium":1.00,
    "Portugal":0.57,"Algeria":0.60,"Congo DR":0.60,"Brazil":0.53,
    "Uruguay":0.50,"Colombia":0.50,"Paraguay":0.50,"South Africa":0.50,
    "Egypt":0.54,"Ecuador":0.50,"Sweden":1.00,"England":0.30,
    "Spain":0.20,"France":0.44,"Netherlands":0.43,"Japan":0.43,
    "Mexico":0.45,"Tunisia":0.43,"Iran":0.33,"Senegal":0.50,
}

def pen_strength(team):
    base = PEN_RECORD.get(team, 0.52)
    gk_bonus = {
        "Argentina":0.08,"Germany":0.04,"Croatia":0.06,"France":0.03,
        "England":0.03,"Portugal":0.05,"Brazil":0.02,"Netherlands":0.02,
        "Morocco":0.03,"South Korea":0.02,"Saudi Arabia":0.04,
    }
    return min(0.92, base + gk_bonus.get(team, 0.0))

def group_difficulty(team):
    for g, ms in GROUPS.items():
        if team in ms:
            opp = [m for m in ms if m != team]
            return sum(ELO.get(m,1600) for m in opp)/3
    return 1600

# ═══════════════════════════════════════════════════════════════════════════════
# COMPOSITE STRENGTH ENGINE
# ═══════════════════════════════════════════════════════════════════════════════
_CACHE    = {}   # composite_strength cache (per team)
_EG_CACHE = {}   # expected_goals cache (per (ta, tb, neutral) — fully deterministic)

def composite_strength(team):
    # 1 — Core ratings
    elo  = ELO.get(team, 1600)
    fifa = FIFA_PTS.get(team, 1500)

    # 2 — Form
    f5  = form_score(team)
    f10 = form10_score(team)

    # 3 — Attack (xG, gpg, shots, sot, big_chances, sp_xg)
    xg, gpg, shots90, sot90, big_ch, sp_xg = ATTACK_STATS.get(team,(1.2,1.3,11,3.5,1.5,0.14))

    # 4 — Defense (xGA, gcpg, big_ch_all, cs_rate, aerial_def, def_errors)
    xga, gcpg, bca, cs, aer_def, def_err = DEFENSE_STATS.get(team,(1.1,1.2,2.5,0.30,0.52,0.30))

    # 5 — Squad quality
    mv    = MARKET_VALUE.get(team, 100)
    mv_xi = STARTING_XI_VALUE.get(team, 60)
    t5    = TOP5_COUNT.get(team, 3)
    cl    = CL_PLAYERS.get(team, 2)
    caps  = AVG_CAPS.get(team, 40)
    wc_e  = WC_EXPERIENCE.get(team, 0.5)
    bench = BENCH_STRENGTH.get(team, 4)
    xi_age= STARTING_XI_AGE.get(team, 27.5)

    # 6 — GK
    gk_sv, gk_psxg, gk_cs10, gk_pen_sv, gk_dist, gk_err = GK_STATS.get(team,(0.70,0.0,3.0,0.15,0.76,0.35))

    # 7 — Tactical
    poss, ppda, aer_att, sp_xg_t, direct, fb = TACTICAL.get(team,(0.47,12,0.52,0.16,0.55,0.52))

    # 8 — Availability
    inj   = INJURY_IMPACT.get(team, 0.0)
    kpa   = KEY_PLAYER_AVAIL.get(team, 0.97)
    gka   = GK_AVAIL.get(team, 1.0)
    cba   = CB_AVAIL.get(team, 1.0)
    sta   = ST_AVAIL.get(team, 1.0)

    # 9 — Context
    trav  = TRAVEL_FATIGUE.get(team, -0.01)
    alt_f = altitude_factor(team)
    tmp_f = temp_factor(team)

    # 10 — Manager
    mgr_t, mgr_e, tfl, sub_i = MANAGER.get(team,(2,0,0.60,0.60))

    # 11 — Discipline
    cards_pg, red_r, fouls_pg = DISCIPLINE.get(team,(2.2,0.05,12))

    # Knockout/pressure
    comeback, after_sc, et_fit, yc_r = PRESSURE_STATS.get(team,(0.60,0.80,0.83,0.30))

    # ── Normalize all to [0,1] ──────────────────────────────────────────────
    elo_n   = (elo  - 1450) / 750
    fifa_n  = (fifa - 1350) / 550
    f5_n    = f5
    f10_n   = f10
    xg_n    = min(xg   / 2.5, 1.0)
    gpg_n   = min(gpg  / 2.5, 1.0)
    sot_n   = min(sot90/ 8.0, 1.0)
    sh_n    = min(shots90/20.0,1.0)
    bch_n   = min(big_ch/5.0, 1.0)
    sp_n    = min(sp_xg/0.35, 1.0)
    xga_n   = max(0, 1 - xga / 2.0)
    gcpg_n  = max(0, 1 - gcpg/ 2.0)
    cs_n    = min(cs, 1.0)
    adef_n  = min(aer_def, 1.0)
    derr_n  = max(0, 1 - def_err/0.6)
    mv_n    = min(mv   /1600, 1.0)
    mvxi_n  = min(mv_xi/1100, 1.0)
    t5_n    = min(t5   / 22,  1.0)
    cl_n    = min(cl   / 18,  1.0)
    caps_n  = min(caps / 80,  1.0)
    wce_n   = min(wc_e / 3.0, 1.0)
    bench_n = min(bench/ 9.0, 1.0)
    age_f   = 1.0 - max(0, abs(xi_age - 26.5) * 0.012)
    gksv_n  = min(gk_sv /0.85, 1.0)
    gkpsx_n = (gk_psxg + 0.3)/0.6
    gkd_n   = min(gk_dist, 1.0)
    gke_n   = max(0, 1 - gk_err/1.0)
    poss_n  = min(poss /0.70, 1.0)
    press_n = max(0, 1 - ppda/15.0)
    aatt_n  = min(aer_att, 1.0)
    kpa_n   = kpa
    avail_n = (gka + cba + sta) / 3.0
    mgr_n   = min((mgr_t/8)*0.5 + (mgr_e/4)*0.5, 1.0)
    tfl_n   = tfl
    disc_n  = max(0, 1 - red_r*4)
    et_n    = et_fit
    cb_n    = comeback

    # ── ATTACK composite (weights sum ≈ 1.0) ────────────────────────────────
    attack = (
        0.14*elo_n + 0.07*fifa_n + 0.06*f5_n + 0.04*f10_n +
        0.11*xg_n  + 0.05*gpg_n  + 0.04*sot_n+ 0.03*sh_n  +
        0.04*bch_n + 0.04*sp_n   +
        0.08*mvxi_n+ 0.05*t5_n   + 0.03*cl_n +
        0.04*aatt_n+ 0.03*bench_n+ 0.04*kpa_n +
        0.03*poss_n+ 0.03*tfl_n  + 0.02*wce_n + 0.01*caps_n +
        0.02*mgr_n + 0.01*fb
    )

    # ── DEFENSE composite ────────────────────────────────────────────────────
    defense = (
        0.13*elo_n + 0.06*fifa_n + 0.05*f5_n  + 0.03*f10_n +
        0.11*xga_n + 0.06*gcpg_n + 0.05*cs_n  + 0.05*adef_n +
        0.03*derr_n+
        0.07*gksv_n+ 0.04*gkpsx_n+ 0.03*gke_n +
        0.06*mvxi_n+ 0.04*t5_n   + 0.05*press_n+
        0.04*avail_n+0.03*disc_n + 0.03*et_n  +
        0.02*mgr_n + 0.01*cb_n
    )

    attack  = max(0.01, attack  * (1 + inj + trav) * alt_f * tmp_f * age_f)
    defense = max(0.01, defense * (1 + inj*0.5 + trav*0.3) * alt_f)

    lam_att = 0.3 + attack  * 2.2
    def_fac = 0.4 + defense * 1.5
    return lam_att, def_fac

def strength(t):
    if t not in _CACHE: _CACHE[t] = composite_strength(t)
    return _CACHE[t]

# ═══════════════════════════════════════════════════════════════════════════════
# MATCH ENGINE
# ═══════════════════════════════════════════════════════════════════════════════
def expected_goals(ta, tb, neutral=False):
    _key = (ta, tb, neutral)
    if _key in _EG_CACHE:
        return _EG_CACHE[_key]
    la_a, df_a = strength(ta)
    la_b, df_b = strength(tb)

    lam_a = la_a / (df_b / 1.2)
    lam_b = la_b / (df_a / 1.2)

    # Elo diff
    ediff = ELO.get(ta,1600) - ELO.get(tb,1600)
    lam_a *= math.exp( ediff / 1200)
    lam_b *= math.exp(-ediff / 1200)

    # Tactical matchup: aerial strength vs opponent aerial weakness
    aer_a = TACTICAL.get(ta,(0.47,12,0.52,0.16,0.55,0.52))[2]
    aer_b = TACTICAL.get(tb,(0.47,12,0.52,0.16,0.55,0.52))[2]
    aer_bonus_a = max(0, (aer_a - aer_b) * 0.06)
    aer_bonus_b = max(0, (aer_b - aer_a) * 0.06)
    lam_a *= (1 + aer_bonus_a)
    lam_b *= (1 + aer_bonus_b)

    # Pressing: high pressing team vs low possession opponent
    ppda_a = TACTICAL.get(ta,(0.47,12,0.52,0.16,0.55,0.52))[1]
    ppda_b = TACTICAL.get(tb,(0.47,12,0.52,0.16,0.55,0.52))[1]
    poss_b = TACTICAL.get(tb,(0.47,12,0.52,0.16,0.55,0.52))[0]
    poss_a = TACTICAL.get(ta,(0.47,12,0.52,0.16,0.55,0.52))[0]
    if ppda_a < 9 and poss_b < 0.50:
        lam_a *= 1.03
    if ppda_b < 9 and poss_a < 0.50:
        lam_b *= 1.03

    # Group difficulty conditioning
    gd_a = group_difficulty(ta)
    gd_b = group_difficulty(tb)
    gd_boost = (gd_a - gd_b) / 8000
    lam_a *= (1 + gd_boost)
    lam_b *= (1 - gd_boost)

    # Host advantage
    if not neutral:
        if ta in HOSTS: lam_a *= HOST_MULT; lam_b *= 0.92
        if tb in HOSTS: lam_b *= HOST_MULT; lam_a *= 0.92

    result = max(0.30, min(4.5, lam_a)), max(0.30, min(4.5, lam_b))
    _EG_CACHE[_key] = result
    return result

_PCDF = {}   # Poisson CDF cache keyed by quantised lambda

def _build_pcdf(lam):
    cdf = []; cumsum = 0.0; pk = math.exp(-lam)
    for k in range(25):
        cumsum += pk; cdf.append(cumsum)
        if cumsum > 1 - 1e-9: break
        pk *= lam / (k + 1)
    return cdf

def poisson(lam):
    key = round(lam * 20)          # quantise to 0.05 steps
    if key not in _PCDF:
        _PCDF[key] = _build_pcdf(key / 20)
    return bisect.bisect_left(_PCDF[key], random.random())

def dc_tau(x, y, mu, nu, rho=-0.09):
    if x==0 and y==0: return 1 - mu*nu*rho
    if x==0 and y==1: return 1 + mu*rho
    if x==1 and y==0: return 1 + nu*rho
    if x==1 and y==1: return 1 - rho
    return 1.0

def simulate_penalty_shootout(ta, tb):
    pa, pb = pen_strength(ta), pen_strength(tb)
    def kicks(n=5):
        return sum(1 for _ in range(n) if random.random()<pa), \
               sum(1 for _ in range(n) if random.random()<pb)
    a, b = kicks()
    if a != b: return ta if a > b else tb
    for _ in range(10):
        ag = int(random.random()<pa); bg = int(random.random()<pb)
        if ag != bg: return ta if ag else tb
    return ta if pen_strength(ta) >= pen_strength(tb) else tb

_MOM_BOOST   = 0.25   # trailing team's rate multiplier per goal deficit
_MOM_RETREAT = 0.10   # leading  team's rate reduction  per goal lead

def simulate_match(ta, tb, neutral=False, knockout=False):
    la, lb = expected_goals(ta, tb, neutral)
    # Match-day noise: captures rotation, injuries, motivation, weather
    la *= max(0.35, random.gauss(1.0, 0.20))
    lb *= max(0.35, random.gauss(1.0, 0.20))

    # Phase 1 — first 60 min (≈67% of expected goals)
    ga = poisson(la * 0.67)
    gb = poisson(lb * 0.67)

    # Phase 2 — final 30 min: trailing side pushes, leading side sits back
    diff = ga - gb
    m    = min(abs(diff), 2)          # cap momentum effect at 2-goal deficit
    if diff > 0:                       # A leads: B presses, A defends
        la2 = la * 0.33 * (1 - _MOM_RETREAT * m)
        lb2 = lb * 0.33 * (1 + _MOM_BOOST   * m)
    elif diff < 0:                     # B leads: A presses, B defends
        la2 = la * 0.33 * (1 + _MOM_BOOST   * m)
        lb2 = lb * 0.33 * (1 - _MOM_RETREAT * m)
    else:                              # level: no adjustment
        la2 = la * 0.33
        lb2 = lb * 0.33

    ga += poisson(max(0.05, la2))
    gb += poisson(max(0.05, lb2))

    # Dixon-Coles low-score correction
    if ga <= 1 and gb <= 1:
        if random.random() > dc_tau(ga, gb, la, lb):
            ga, gb = poisson(la), poisson(lb)

    if knockout and ga == gb:
        et_a = PRESSURE_STATS.get(ta,(0.60,0.80,0.83,0.30))[2]
        et_b = PRESSURE_STATS.get(tb,(0.60,0.80,0.83,0.30))[2]
        ga += poisson(la * 0.28 * et_a)
        gb += poisson(lb * 0.28 * et_b)
        if ga == gb:
            return ga, gb, simulate_penalty_shootout(ta, tb)
    return ga, gb, None

# ═══════════════════════════════════════════════════════════════════════════════
# GROUP STAGE (returns standings + per-team W/D/L records)
# ═══════════════════════════════════════════════════════════════════════════════
def simulate_group(teams, actual=None):
    stats  = {t:{"pts":0,"gf":0,"ga":0,"gd":0,"w":0,"d":0,"l":0} for t in teams}
    match_results = []
    for a, b in combinations(teams, 2):
        if actual and (a, b) in actual:
            ga, gb = actual[(a, b)]
        elif actual and (b, a) in actual:
            gb, ga = actual[(b, a)]
        else:
            ga, gb, _ = simulate_match(a, b)
        stats[a]["gf"]+=ga; stats[a]["ga"]+=gb
        stats[b]["gf"]+=gb; stats[b]["ga"]+=ga
        stats[a]["gd"] = stats[a]["gf"]-stats[a]["ga"]
        stats[b]["gd"] = stats[b]["gf"]-stats[b]["ga"]
        if   ga > gb: stats[a]["pts"]+=3; stats[a]["w"]+=1; stats[b]["l"]+=1
        elif gb > ga: stats[b]["pts"]+=3; stats[b]["w"]+=1; stats[a]["l"]+=1
        else:         stats[a]["pts"]+=1; stats[b]["pts"]+=1; stats[a]["d"]+=1; stats[b]["d"]+=1
        match_results.append((a, b, ga, gb))
    st = [{"team":t,**s} for t,s in stats.items()]
    st.sort(key=lambda x:(x["pts"],x["gd"],x["gf"],random.random()), reverse=True)
    for i,r in enumerate(st): r["pos"] = i+1
    return st, match_results

def pick_thirds(thirds):
    thirds.sort(key=lambda x:(x["pts"],x["gd"],x["gf"],random.random()), reverse=True)
    return [t["team"] for t in thirds[:8]]

def build_r32(gr, bt):
    bracket = [
        ("A1","B2"),("C1","D2"),("E1","F2"),("G1","H2"),
        ("I1","J2"),("K1","L2"),("A2","B1"),("C2","D1"),
        ("E2","F1"),("G2","H1"),("I2","J1"),("K2","L1"),
    ]
    def gt(c): return gr[c[0]][int(c[1])-1]["team"]
    mu = [(gt(a),gt(b)) for a,b in bracket]
    for i in range(0,8,2): mu.append((bt[i],bt[i+1]))
    return mu

def ko_round(mu, stage_rec):
    w = []
    for a, b in mu:
        ga, gb, pen = simulate_match(a, b, neutral=True, knockout=True)
        winner = pen if pen else (a if ga>=gb else b)
        loser  = b if winner==a else a
        w.append(winner)
        stage_rec[winner].append("W")
        stage_rec[loser].append("L")
    return w

def pair(t): return [(t[i],t[i+1]) for i in range(0,len(t),2)]

# ═══════════════════════════════════════════════════════════════════════════════
# FULL TOURNAMENT — returns (placement_dict, gs_wdl, ko_records, match_log)
# gs_wdl[team]   = [W,D,L] across 3 group matches
# ko_records[team][stage_label] = list of "W"/"L" strings
# ═══════════════════════════════════════════════════════════════════════════════
def simulate_tournament(actual=None):
    gs_wdl   = {t:[0,0,0] for t in ELO}
    ko_rec   = {t:{"r32":[],"r16":[],"qf":[],"sf":[],"final":[]} for t in ELO}
    res      = {t:"eliminated_group" for t in ELO}

    gr = {}; thirds = []
    for g, ts in GROUPS.items():
        st, _ = simulate_group(ts, actual=actual)
        gr[g]  = st
        for row in st:
            t = row["team"]
            gs_wdl[t][0] += row["w"]
            gs_wdl[t][1] += row["d"]
            gs_wdl[t][2] += row["l"]
        thirds.append(st[2])
        res[st[3]["team"]] = "eliminated_group"

    bt = pick_thirds(thirds)
    for e in thirds:
        if e["team"] not in bt: res[e["team"]] = "eliminated_group"

    r32 = build_r32(gr, bt)
    r32w = ko_round(r32, {t:ko_rec[t]["r32"] for t in ELO})
    for a,b in r32:
        loser = b if a in r32w else a
        res[loser] = "r32"
    for w in r32w: res[w] = "r16"

    r16w = ko_round(pair(r32w), {t:ko_rec[t]["r16"] for t in ELO})
    for a,b in pair(r32w):
        loser = b if a in r16w else a
        res[loser] = "r16"
    for w in r16w: res[w] = "qf"

    qfw = ko_round(pair(r16w), {t:ko_rec[t]["qf"] for t in ELO})
    for a,b in pair(r16w):
        loser = b if a in qfw else a
        res[loser] = "qf"
    for w in qfw: res[w] = "sf"

    sfw = ko_round(pair(qfw), {t:ko_rec[t]["sf"] for t in ELO})
    for a,b in pair(qfw):
        loser = b if a in sfw else a
        res[loser] = "sf"
    for w in sfw: res[w] = "finalist"

    final_w = ko_round([tuple(sfw)], {t:ko_rec[t]["final"] for t in ELO})
    res[final_w[0]] = "winner"
    return res, gs_wdl, ko_rec

# ═══════════════════════════════════════════════════════════════════════════════
# MONTE CARLO
# ═══════════════════════════════════════════════════════════════════════════════
ROUNDS = ["eliminated_group","r32","r16","qf","sf","finalist","winner"]

# ── Multiprocessing worker ────────────────────────────────────────────────────
def _sim_chunk(args):
    """Run a chunk of tournament simulations in a worker process.
    args = (n_chunk, actual_results_dict). Returns plain dicts (picklable)."""
    n_chunk, actual = args
    random.seed()
    teams = list(ELO.keys())
    counts   = {t: {r: 0 for r in ROUNDS} for t in teams}
    gs_acc   = {t: [0, 0, 0] for t in teams}
    ko_win   = {t: {"r32":0,"r16":0,"qf":0,"sf":0,"final":0} for t in teams}
    ko_reach = {t: {"r32":0,"r16":0,"qf":0,"sf":0,"final":0} for t in teams}
    for _ in range(n_chunk):
        res, gs_wdl, ko_rec = simulate_tournament(actual=actual)
        for t, s in res.items():
            counts[t][s] += 1
        for t in teams:
            g = gs_wdl[t]
            gs_acc[t][0] += g[0]; gs_acc[t][1] += g[1]; gs_acc[t][2] += g[2]
            for stg in ("r32","r16","qf","sf","final"):
                games = ko_rec[t][stg]
                if games:
                    ko_reach[t][stg] += 1
                    ko_win[t][stg]   += games.count("W")
    return counts, gs_acc, ko_win, ko_reach

def run_simulations(n=50_000, actual=None):
    """Run n full tournament simulations. actual = {(home,away):(gh,ga)} of known results."""
    actual    = actual or {}
    teams     = list(ELO.keys())

    # Avoid spawning child processes when running inside Streamlit — workers
    # re-import Streamlit's __main__ on Windows spawn, adding 5-10s per worker.
    _in_streamlit = "streamlit.runtime.scriptrunner" in sys.modules

    if _in_streamlit:
        all_results = [_sim_chunk((n, actual))]
    else:
        n_workers = min(os.cpu_count() or 4, 8)
        base      = n // n_workers
        chunks    = [base] * n_workers
        chunks[-1] += n - sum(chunks)
        job_args  = [(c, actual) for c in chunks]
        try:
            with ProcessPoolExecutor(max_workers=n_workers) as ex:
                all_results = list(ex.map(_sim_chunk, job_args))
        except Exception:
            all_results = [_sim_chunk((n, actual))]

    # Merge results from all workers
    counts   = {t: {r: 0 for r in ROUNDS} for t in teams}
    gs_acc   = {t: [0, 0, 0] for t in teams}
    ko_win   = {t: {"r32":0,"r16":0,"qf":0,"sf":0,"final":0} for t in teams}
    ko_reach = {t: {"r32":0,"r16":0,"qf":0,"sf":0,"final":0} for t in teams}
    for c, gs, kw, kr in all_results:
        for t in teams:
            for r in ROUNDS:
                counts[t][r] += c[t].get(r, 0)
            for i in range(3):
                gs_acc[t][i] += gs[t][i]
            for stg in ("r32","r16","qf","sf","final"):
                ko_win[t][stg]   += kw[t][stg]
                ko_reach[t][stg] += kr[t][stg]

    probs = {}
    for team in ELO:
        p = {r: round(counts[team][r]/n*100,2) for r in ROUNDS}
        p["p_r16"]   = round(sum(counts[team][r] for r in ["r16","qf","sf","finalist","winner"])/n*100,1)
        p["p_qf"]    = round(sum(counts[team][r] for r in ["qf","sf","finalist","winner"])/n*100,1)
        p["p_sf"]    = round(sum(counts[team][r] for r in ["sf","finalist","winner"])/n*100,1)
        p["p_final"] = round(sum(counts[team][r] for r in ["finalist","winner"])/n*100,1)
        p["p_win"]   = round(counts[team]["winner"]/n*100,2)
        la,df = strength(team)
        p["attack_lam"]=round(la,3); p["def_factor"]=round(df,3)
        p["elo"]=ELO.get(team,0); p["fifa_pts"]=FIFA_PTS.get(team,0)
        p["form"]=round(form_score(team),3)
        p["market_M"]=MARKET_VALUE.get(team,0)
        p["top5_count"]=TOP5_COUNT.get(team,0)
        p["pen_str"]=round(pen_strength(team),3)
        p["grp_diff"]=round(group_difficulty(team),0)
        p["host"]=team in HOSTS
        # Stage W/D/L
        p["gs_w"]=round(gs_acc[team][0]/n,2)
        p["gs_d"]=round(gs_acc[team][1]/n,2)
        p["gs_l"]=round(gs_acc[team][2]/n,2)
        for stg in ["r32","r16","qf","sf","final"]:
            reach = ko_reach[team][stg]
            if reach > 0:
                p[f"{stg}_wpct"] = round(ko_win[team][stg]/reach*100,1)
                p[f"{stg}_lpct"] = round((reach-ko_win[team][stg])/reach*100,1)
                p[f"{stg}_reach"]= round(reach/n*100,1)
            else:
                p[f"{stg}_wpct"]=0.0; p[f"{stg}_lpct"]=0.0; p[f"{stg}_reach"]=0.0
        probs[team] = p
    return probs

# ═══════════════════════════════════════════════════════════════════════════════
# GAME-WISE MATCH PREDICTIONS
# ═══════════════════════════════════════════════════════════════════════════════
def predict_match(ta, tb, sims=20_000):
    wa=wb=d=0; gA=gB=0
    scores = defaultdict(int)
    for _ in range(sims):
        ga,gb,pen = simulate_match(ta,tb,neutral=False,knockout=False)
        gA+=ga; gB+=gb; scores[(ga,gb)]+=1
        if   ga>gb: wa+=1
        elif gb>ga: wb+=1
        else:       d +=1
    la, lb = expected_goals(ta,tb,neutral=False)
    modal  = max(scores, key=scores.get)
    return {
        "win_a":round(wa/sims*100,1), "draw":round(d/sims*100,1),
        "win_b":round(wb/sims*100,1), "xg_a":round(la,2), "xg_b":round(lb,2),
        "avg_a":round(gA/sims,2),     "avg_b":round(gB/sims,2),
        "modal":modal,
    }

def print_game_predictions(sims=20_000):
    print("\n" + "═"*82)
    print("  ⚽  GROUP STAGE GAME-WISE PREDICTIONS  (Monte Carlo match simulations)")
    print("═"*82)
    for grp, teams in GROUPS.items():
        matches = list(combinations(teams, 2))
        avg_elo = sum(ELO.get(t,1600) for t in teams)/4
        print(f"\n  ── GROUP {grp}  [avg Elo {avg_elo:.0f}] ──────────────────────────────────────────")
        print(f"  {'Match':<38} {'Win%':>6} {'Draw%':>6} {'Win%':>6}  {'xG':>8}  {'Modal score'}")
        print(f"  {'─'*78}")
        for ta, tb in matches:
            r = predict_match(ta, tb, sims)
            fa,fb = FLAGS.get(ta,""), FLAGS.get(tb,"")
            matchup = f"{fa}{ta} vs {tb}{fb}"
            score_str = f"{r['modal'][0]}-{r['modal'][1]}"
            xg_str    = f"{r['xg_a']:.2f}-{r['xg_b']:.2f}"
            print(f"  {ta:<17} vs {tb:<17}  "
                  f"{r['win_a']:>5.1f}%  {r['draw']:>5.1f}%  {r['win_b']:>5.1f}%"
                  f"  {xg_str:>9}  {score_str}")
    print("\n" + "═"*82 + "\n")

# ═══════════════════════════════════════════════════════════════════════════════
# STAGE W/L/D TABLE
# ═══════════════════════════════════════════════════════════════════════════════
def print_stage_records(probs, top_n=24):
    srt = sorted(probs.items(), key=lambda x:x[1]["p_win"], reverse=True)[:top_n]
    print("\n" + "═"*108)
    print("  📊  STAGE-BY-STAGE WIN/LOSS RECORD  (group avg W-D-L | knockout W%-L% if reached)")
    print("═"*108)
    print(f"  {'Team':<20} {'Group (W-D-L)':^15}  {'R32 W%-L%':^12}  {'R16 W%-L%':^12}  {'QF W%-L%':^12}  {'SF W%-L%':^12}  {'Final W%-L%':^12}")
    print("─"*108)
    for t, p in srt:
        fl = FLAGS.get(t,"  ")
        gs = f"{p['gs_w']:.1f}-{p['gs_d']:.1f}-{p['gs_l']:.1f}"
        def ko(s):
            if p[f"{s}_reach"] < 0.5: return "  —  "
            return f"{p[f'{s}_wpct']:.0f}%-{p[f'{s}_lpct']:.0f}%"
        print(f"  {fl} {t:<17}  {gs:^14}  {ko('r32'):^12}  {ko('r16'):^12}  {ko('qf'):^12}  {ko('sf'):^12}  {ko('final'):^12}")
    print("═"*108 + "\n")

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN RESULTS TABLE
# ═══════════════════════════════════════════════════════════════════════════════
def bar(p, w=26): f=int(round(p/100*w)); return "█"*f+"░"*(w-f)

def print_results(probs, top_n=48):
    srt = sorted(probs.items(), key=lambda x:x[1]["p_win"], reverse=True)
    print("\n"+"═"*98)
    print("  🌍  FIFA WORLD CUP 2026 — 80-VARIABLE MONTE CARLO SIMULATOR v4  🌍")
    print("═"*98)
    print(f"  {'#':>3}  {'Team':<18} {'Elo':>5} {'FIFA':>5} {'Form':>5} {'€M':>6}  {'Win%':>6}  {'Final%':>7}  {'SF%':>5}  {'QF%':>5}  {'R32%':>5}")
    print("─"*98)
    for i,(t,p) in enumerate(srt[:top_n],1):
        fl=FLAGS.get(t,"  "); hs="★" if p["host"] else " "
        print(f"  {i:>3}. {fl} {t:<15}{hs} {p['elo']:>5} {p['fifa_pts']:>5} "
              f"{p['form']:>5.2f} {p['market_M']:>5}M "
              f"  {p['p_win']:>5.1f}%  {p['p_final']:>6.1f}%  "
              f"{p['p_sf']:>4.1f}%  {p['p_qf']:>4.1f}%  {p['p_r16']:>4.1f}%")
    print("─"*98)
    print("  ★=Host  Form=last-5 weighted  Variables: Elo·FIFA·Form10·xG/xGA·Shots·BigChances")
    print("  Set-pieces·Squad value·CL/T5 count·GK stats·Pressing·Aerial·Availability·Manager·Discipline")
    print("\n"+"─"*72)
    print("  🏆  WIN PROBABILITY — TOP 12")
    print("─"*72)
    for t,p in srt[:12]:
        fl=FLAGS.get(t,"  ")
        print(f"  {fl} {t:<18}  {bar(p['p_win'])}  {p['p_win']:>5.2f}%")

    print("\n"+"─"*98)
    print("  📊  GROUP STAGE QUALIFICATION RATES  (% reaching Round of 32)")
    print("─"*98)
    for grp, teams in GROUPS.items():
        avg_elo = sum(ELO.get(t,1600) for t in teams)/4
        print(f"\n  Group {grp}  [avg Elo: {avg_elo:.0f}]:")
        for t in sorted(teams, key=lambda x: probs.get(x,{}).get("p_r16",0), reverse=True):
            fl=FLAGS.get(t,"  ")
            pct=probs.get(t,{}).get("p_r16",0)
            print(f"    {fl} {t:<18}  {bar(pct,20)}  {pct:>5.1f}%  "
                  f"[Elo:{ELO.get(t,0):>4} xG:{ATTACK_STATS.get(t,(0,0,0,0,0,0))[0]:.2f} "
                  f"Form:{form_score(t):.2f} Pen:{pen_strength(t):.2f}]")
    print("\n"+"═"*98+"\n")

def print_breakdown(probs):
    print(f"\n{'─'*108}")
    print("  ALL 48 TEAMS — FULL VARIABLE BREAKDOWN")
    print(f"{'─'*108}")
    print(f"  {'Team':<18} {'Elo':>5} {'FIFA':>5} {'Form':>5} {'xG':>5} {'xGA':>5} {'GKsv':>5} {'€M':>6} {'T5':>3} {'CL':>3} {'Pen':>5}  {'Win%':>6}  {'QF%':>5}")
    print(f"  {'─'*106}")
    for t in sorted(ELO, key=lambda x: probs.get(x,{}).get("p_win",0), reverse=True):
        fl=FLAGS.get(t,"  ")
        xg=ATTACK_STATS.get(t,(0,)*6)[0]
        xga=DEFENSE_STATS.get(t,(0,)*6)[0]
        gksv=GK_STATS.get(t,(0,)*6)[0]
        p=probs.get(t,{})
        print(f"  {fl} {t:<16}  {ELO.get(t,0):>5} {FIFA_PTS.get(t,0):>5} "
              f"{form_score(t):>5.2f} {xg:>5.2f} {xga:>5.2f} {gksv:>5.2f} "
              f"{MARKET_VALUE.get(t,0):>5}M {TOP5_COUNT.get(t,0):>3} "
              f"{CL_PLAYERS.get(t,0):>3} {pen_strength(t):>5.2f}"
              f"  {p.get('p_win',0):>5.2f}%  {p.get('p_qf',0):>4.1f}%")
    print()

def print_team_detail(team, probs):
    if team not in ELO: print(f"'{team}' not found."); return
    p=probs.get(team,{}); fl=FLAGS.get(team,"  ")
    xg,gpg,s90,sot90,bc,spxg = ATTACK_STATS.get(team,(0,)*6)
    xga,gcpg,bca,cs,aerd,derr = DEFENSE_STATS.get(team,(0,)*6)
    gksv,gkpsxg,gkcs,gkpen,gkdist,gkerr = GK_STATS.get(team,(0,)*6)
    poss,ppda,aer,spd,direct,fb = TACTICAL.get(team,(0,)*6)
    mgrt,mgre,tfl,subi = MANAGER.get(team,(0,)*4)
    cards,redr,fouls = DISCIPLINE.get(team,(0,)*3)
    print(f"\n{'═'*72}")
    print(f"  {fl}  {team.upper()}  — 80-Variable Profile")
    print(f"{'═'*72}")
    print(f"  CATEGORY 1 — TEAM STRENGTH")
    print(f"    Elo: {ELO.get(team,0)}  FIFA pts: {FIFA_PTS.get(team,0)}")
    print(f"    Form (last 5): {'  '.join(FORM_RESULTS.get(team,[]))} → {form_score(team):.2f}")
    W10,D10,L10=FORM_10.get(team,(5,3,2))
    print(f"    Last 10:  {W10}W {D10}D {L10}L  (score: {form10_score(team):.2f})")
    print(f"    Goal diff last 10: ~{W10*2-L10*1}")
    print(f"    Clean sheet rate: {cs:.0%}")
    print(f"  CATEGORY 4+5 — ATTACK / DEFENSE")
    print(f"    xG/game: {xg:.2f}  Goals/game: {gpg:.2f}  Shots/90: {s90:.1f}  SOT/90: {sot90:.1f}")
    print(f"    Big chances created: {bc:.1f}/game  Set-piece xG: {spxg:.2f}")
    print(f"    xGA/game: {xga:.2f}  Conceded/game: {gcpg:.2f}  Def errors/10: {derr:.2f}")
    print(f"  CATEGORY 6 — GOALKEEPER")
    print(f"    Save%: {gksv:.0%}  PSxG diff: {gkpsxg:+.2f}  Pen saves: {gkpen:.0%}  Dist: {gkdist:.0%}")
    print(f"  CATEGORY 7 — TACTICAL")
    print(f"    Possession: {poss:.0%}  PPDA: {ppda:.1f}  Aerial win: {aer:.0%}")
    print(f"    Set-piece xG: {spd:.2f}  Directness: {direct:.2f}  FB overlap: {fb:.2f}")
    print(f"  CATEGORY 2 — SQUAD QUALITY")
    print(f"    Market value: €{MARKET_VALUE.get(team,0)}M  XI value: €{STARTING_XI_VALUE.get(team,0)}M")
    print(f"    Top-5 league: {TOP5_COUNT.get(team,0)}  CL players: {CL_PLAYERS.get(team,0)}")
    print(f"    Avg caps: {AVG_CAPS.get(team,0)}  WC exp: {WC_EXPERIENCE.get(team,0):.1f}  Bench: {BENCH_STRENGTH.get(team,0)}/10")
    print(f"    Squad age: {SQUAD_AGE.get(team,0):.1f}  XI age: {STARTING_XI_AGE.get(team,0):.1f}")
    print(f"  CATEGORY 11 — MANAGER & DISCIPLINE")
    print(f"    Tenure: {mgrt}yr  Tournament exp: {mgre}  Tact flex: {tfl:.2f}  Sub impact: {subi:.2f}")
    print(f"    Cards/game: {cards:.1f}  Red card risk: {redr:.0%}  Fouls/game: {fouls:.1f}")
    print(f"  CATEGORY 10 — PRESSURE")
    cb,asc,etf,ycr = PRESSURE_STATS.get(team,(0,)*4)
    print(f"    Comeback rec: {cb:.0%}  After scoring 1st: {asc:.0%}  ET fitness: {etf:.0%}")
    print(f"    Penalty strength: {pen_strength(team):.2f}  YC accum risk: {ycr:.0%}")
    la,df=strength(team)
    print(f"\n  Composite →  Attack λ: {la:.3f}   Defense factor: {df:.3f}")
    print(f"\n  Tournament probabilities:")
    for lbl,key in [("Win","p_win"),("Final","p_final"),("SF","p_sf"),("QF","p_qf"),("R32","p_r16")]:
        v=p.get(key,0)
        print(f"    {lbl:<8} {bar(v,24)}  {v:.1f}%")
    print(f"\n  Stage records (W-D-L / W%-L%):")
    print(f"    Group stage:  {p.get('gs_w',0):.1f}W  {p.get('gs_d',0):.1f}D  {p.get('gs_l',0):.1f}L")
    for stg,lbl in [("r32","R32"),("r16","R16"),("qf","QF"),("sf","SF"),("final","Final")]:
        if p.get(f"{stg}_reach",0) > 0.5:
            print(f"    {lbl:<8}      {p[f'{stg}_wpct']:.0f}% win  {p[f'{stg}_lpct']:.0f}% loss  (reached {p[f'{stg}_reach']:.1f}% of sims)")
    print(f"{'═'*72}\n")

def match_preview(ta, tb, n=30_000):
    if ta not in ELO or tb not in ELO: print("Team not found."); return
    wa=wb=pa=pb=0; gA=gB=0; scores=defaultdict(int)
    for _ in range(n):
        ga,gb,pen = simulate_match(ta,tb,neutral=True,knockout=True)
        gA+=ga; gB+=gb; scores[(ga,gb)]+=1
        if pen:
            if pen==ta: pa+=1
            else: pb+=1
        elif ga>gb: wa+=1
        elif gb>ga: wb+=1
    la,lb = expected_goals(ta,tb,neutral=True)
    modal = max(scores, key=scores.get)
    fl_a,fl_b = FLAGS.get(ta,""), FLAGS.get(tb,"")
    print(f"\n{'═'*70}")
    print(f"  ⚽  HEAD-TO-HEAD  ({n:,} sims) — 80 variables")
    print(f"{'═'*70}")
    print(f"  {fl_a} {ta}  vs  {fl_b} {tb}")
    print(f"  Elo:    {ELO.get(ta,0):>4}  vs  {ELO.get(tb,0):>4}  (diff {ELO.get(ta,0)-ELO.get(tb,0):+})")
    print(f"  FIFA:   {FIFA_PTS.get(ta,0):>4}  vs  {FIFA_PTS.get(tb,0):>4}")
    print(f"  Form5:  {form_score(ta):.2f}  vs  {form_score(tb):.2f}")
    print(f"  MktVal: €{MARKET_VALUE.get(ta,0)}M  vs  €{MARKET_VALUE.get(tb,0)}M")
    print(f"  xG/gm:  {ATTACK_STATS.get(ta,(0,)*6)[0]:.2f}  vs  {ATTACK_STATS.get(tb,(0,)*6)[0]:.2f}")
    print(f"  GK sv%: {GK_STATS.get(ta,(0,)*6)[0]:.2f}  vs  {GK_STATS.get(tb,(0,)*6)[0]:.2f}")
    print(f"  PPDA:   {TACTICAL.get(ta,(0,)*6)[1]:.1f}  vs  {TACTICAL.get(tb,(0,)*6)[1]:.1f}")
    print(f"  Pen:    {pen_strength(ta):.2f}  vs  {pen_strength(tb):.2f}")
    print(f"{'─'*70}")
    print(f"  xG model:  {ta}: {la:.2f}   {tb}: {lb:.2f}")
    print(f"  {ta:<22} win: {(wa+pa)/n*100:>6.2f}%")
    print(f"  Draw (90 min):          {(n-wa-wb-pa-pb)/n*100:>6.2f}%")
    print(f"  {tb:<22} win: {(wb+pb)/n*100:>6.2f}%")
    print(f"  Goes to penalties:      {(pa+pb)/n*100:>6.2f}%")
    print(f"  Avg goals: {ta}: {gA/n:.2f}   {tb}: {gB/n:.2f}")
    print(f"  Most likely score: {modal[0]}-{modal[1]}  (occurred {scores[modal]/n*100:.1f}% of sims)")
    print(f"{'═'*70}\n")


# ═══════════════════════════════════════════════════════════════════════════════
# MATPLOTLIB VISUALIZATIONS
# ═══════════════════════════════════════════════════════════════════════════════
def generate_charts(probs):
    if not HAS_MPL:
        print("  matplotlib not installed — skipping charts"); return
    srt = sorted(probs.items(), key=lambda x:x[1]["p_win"], reverse=True)

    # ── Chart 1: Win Probabilities (top 20) ──────────────────────────────────
    fig, ax = plt.subplots(figsize=(12,8))
    top20 = srt[:20]
    teams = [t for t,_ in reversed(top20)]
    wins  = [p["p_win"] for _,p in reversed(top20)]
    colors= plt.cm.RdYlGn(np.linspace(0.25,0.85,20))[::-1]
    bars  = ax.barh(teams, wins, color=colors, edgecolor="white", linewidth=0.6)
    for bar_,val in zip(bars,wins):
        ax.text(bar_.get_width()+0.15, bar_.get_y()+bar_.get_height()/2,
                f"{val:.1f}%", va="center", ha="left", fontsize=9, fontweight="bold")
    ax.set_xlabel("Win Probability (%)", fontsize=11)
    ax.set_title("FIFA World Cup 2026 — Win Probability\n80-Variable Monte Carlo (50,000 simulations)",
                 fontsize=13, fontweight="bold", pad=12)
    ax.axvline(x=5, color="gray", linestyle="--", alpha=0.5, linewidth=0.8)
    ax.set_xlim(0, max(wins)*1.18)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    plt.tight_layout()
    plt.savefig("wc2026_win_probs.png", dpi=160, bbox_inches="tight")
    plt.close(); print("  Saved: wc2026_win_probs.png")

    # ── Chart 2: Stage Probability Heatmap (top 24) ──────────────────────────
    top24 = srt[:24]
    stages_labels = ["R32","R16","QF","SF","Final","Win"]
    stages_keys   = ["p_r16","p_qf","p_sf","p_final","p_final","p_win"]
    # recompute correctly
    data = []
    row_labels = []
    for t,p in top24:
        data.append([p["p_r16"],p["p_qf"],p["p_sf"],p["p_final"],p["p_win"]])
        row_labels.append(t)
    data = np.array(data)
    fig,ax = plt.subplots(figsize=(10,10))
    im = ax.imshow(data, cmap="YlOrRd", aspect="auto", vmin=0, vmax=100)
    ax.set_xticks(range(5)); ax.set_xticklabels(["R32%","QF%","SF%","Final%","Win%"], fontsize=10)
    ax.set_yticks(range(24)); ax.set_yticklabels(row_labels, fontsize=9)
    for i in range(24):
        for j,val in enumerate(data[i]):
            color = "white" if val > 55 else "black"
            ax.text(j,i,f"{val:.0f}",ha="center",va="center",fontsize=8,color=color,fontweight="bold")
    plt.colorbar(im, ax=ax, label="Probability (%)", shrink=0.6)
    ax.set_title("Stage Progression Probability — Top 24 Teams\nFIFA World Cup 2026", fontsize=12, fontweight="bold", pad=10)
    plt.tight_layout()
    plt.savefig("wc2026_stage_matrix.png", dpi=160, bbox_inches="tight")
    plt.close(); print("  Saved: wc2026_stage_matrix.png")

    # ── Chart 3: Group Qualification Rates ───────────────────────────────────
    fig, axes = plt.subplots(3,4, figsize=(16,10))
    axes = axes.flatten()
    for idx,(grp,teams) in enumerate(GROUPS.items()):
        ax = axes[idx]
        pcts = [probs.get(t,{}).get("p_r16",0) for t in teams]
        c = ["#2ecc71","#2ecc71","#e74c3c","#e74c3c"]
        bars = ax.bar(range(4), pcts, color=c, edgecolor="white", width=0.6)
        ax.set_xticks(range(4)); ax.set_xticklabels([t[:10] for t in teams], fontsize=7, rotation=20, ha="right")
        ax.set_title(f"Group {grp}  [avg Elo {sum(ELO.get(t,0) for t in teams)//4}]", fontsize=9, fontweight="bold")
        ax.set_ylim(0,100); ax.set_ylabel("%", fontsize=8)
        ax.axhline(50, color="gray", linestyle="--", linewidth=0.7, alpha=0.6)
        for bar_,val in zip(bars,pcts):
            ax.text(bar_.get_x()+bar_.get_width()/2, bar_.get_height()+1.5,
                    f"{val:.0f}%", ha="center", va="bottom", fontsize=7.5, fontweight="bold")
        ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    fig.suptitle("Group Stage Qualification Rates (R32) — FIFA World Cup 2026\n"
                 "Green = likely qualify, Red = likely eliminated", fontsize=12, fontweight="bold")
    plt.tight_layout(rect=[0,0,1,0.95])
    plt.savefig("wc2026_groups.png", dpi=160, bbox_inches="tight")
    plt.close(); print("  Saved: wc2026_groups.png")

    # ── Chart 4: Stage W/D/L grouped bars (top 12) ───────────────────────────
    top12 = srt[:12]
    t_names = [t for t,_ in top12]
    gs_w = [p["gs_w"] for _,p in top12]
    gs_d = [p["gs_d"] for _,p in top12]
    gs_l = [p["gs_l"] for _,p in top12]
    x = np.arange(12); w = 0.25
    fig,ax = plt.subplots(figsize=(13,6))
    ax.bar(x-w, gs_w, w, label="Wins",  color="#27ae60", edgecolor="white")
    ax.bar(x,   gs_d, w, label="Draws", color="#f39c12", edgecolor="white")
    ax.bar(x+w, gs_l, w, label="Losses",color="#e74c3c", edgecolor="white")
    ax.set_xticks(x); ax.set_xticklabels([t[:12] for t in t_names], rotation=30, ha="right", fontsize=9)
    ax.set_ylabel("Expected matches", fontsize=10)
    ax.set_title("Expected Group Stage W/D/L Record — Top 12 Teams\nFIFA World Cup 2026 (50,000 simulations)", fontsize=12, fontweight="bold")
    ax.legend(fontsize=9); ax.set_ylim(0, 3.2)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.axhline(1, color="gray", linestyle=":", alpha=0.4)
    ax.axhline(2, color="gray", linestyle=":", alpha=0.4)
    ax.axhline(3, color="gray", linestyle=":", alpha=0.4)
    plt.tight_layout()
    plt.savefig("wc2026_stage_wdl.png", dpi=160, bbox_inches="tight")
    plt.close(); print("  Saved: wc2026_stage_wdl.png")

    print("  All 4 charts generated in current directory.\n")


# ═══════════════════════════════════════════════════════════════════════════════
# GOLDEN BOOT & GOLDEN BALL
# ═══════════════════════════════════════════════════════════════════════════════
PLAYERS = [
    ("Kylian Mbappe",      "France",     "ST",  1.10,0.65,7.5,27,12,0.05,1.00),
    ("Harry Kane",         "England",    "ST",  0.92,0.70,6.5,31, 6,0.05,1.00),
    ("Erling Haaland",     "Norway",     "ST",  1.05,0.75,4.5,26, 0,0.08,1.00),
    ("Lamine Yamal",       "Spain",      "RW",  0.55,0.45,9.5,18, 0,0.25,0.85),
    ("Lionel Messi",       "Argentina",  "CAM", 0.86,0.45,9.8,39,13,0.20,0.80),
    ("Cristiano Ronaldo",  "Portugal",   "ST",  0.40,0.38,5.0,41, 8,0.15,0.85),
    ("Julian Alvarez",     "Argentina",  "ST",  0.75,0.55,6.5,25, 4,0.05,0.90),
    ("Vinicius Jr",        "Brazil",     "LW",  0.72,0.38,7.5,25, 0,0.10,0.95),
    ("Raphinha",           "Brazil",     "RW",  0.65,0.48,7.0,28, 0,0.05,1.00),
    ("Kai Havertz",        "Germany",    "ST",  0.60,0.52,6.8,26, 0,0.05,0.95),
    ("Michael Olise",      "France",     "RW",  0.68,0.42,8.5,24, 0,0.08,0.90),
    ("Mikel Oyarzabal",    "Spain",      "ST",  0.55,0.45,7.0,29, 0,0.08,0.90),
    ("Lautaro Martinez",   "Argentina",  "ST",  0.65,0.60,5.5,27, 3,0.05,0.90),
    ("Jude Bellingham",    "England",    "CM",  0.45,0.42,9.0,22, 0,0.05,1.00),
    ("Bukayo Saka",        "England",    "RW",  0.55,0.48,8.5,23, 0,0.05,0.95),
    ("Florian Wirtz",      "Germany",    "CAM", 0.55,0.45,9.0,22, 0,0.05,0.95),
    ("Jamal Musiala",      "Germany",    "CM",  0.50,0.40,8.8,22, 0,0.05,0.95),
    ("Martin Odegaard",    "Norway",     "CM",  0.42,0.38,9.2,27, 0,0.08,0.95),
    ("Bruno Fernandes",    "Portugal",   "CAM", 0.35,0.28,9.5,31, 0,0.05,1.00),
    ("Pedri",              "Spain",      "CM",  0.28,0.22,9.2,23, 0,0.10,0.90),
    ("Viktor Gyokeres",    "Sweden",     "ST",  1.05,0.65,5.5,27, 0,0.08,1.00),
    ("Alexander Isak",     "Sweden",     "ST",  0.85,0.58,6.0,26, 0,0.10,0.95),
    ("Jonathan David",     "Canada",     "ST",  0.82,0.65,5.5,25, 0,0.05,1.00),
    ("Cody Gakpo",         "Netherlands","LW",  0.52,0.48,6.5,26, 3,0.05,0.95),
    ("Darwin Nunez",       "Uruguay",    "ST",  0.62,0.55,5.5,26, 0,0.10,0.90),
    ("Mohamed Salah",      "Egypt",      "RW",  0.65,0.48,8.0,33, 0,0.10,1.00),
    ("Federico Valverde",  "Uruguay",    "CM",  0.48,0.40,8.0,26, 0,0.05,1.00),
    ("Son Heung-min",      "South Korea","RW",  0.60,0.45,7.5,34, 0,0.12,0.95),
    ("Romelu Lukaku",      "Belgium",    "ST",  0.58,0.48,4.5,31, 3,0.10,0.90),
    ("Ousmane Dembele",    "France",     "RW",  0.48,0.35,7.8,27, 1,0.10,0.90),
    ("Rafael Leao",        "Portugal",   "LW",  0.60,0.38,7.5,26, 0,0.08,0.95),
    # ── Brazil ───────────────────────────────────────────────────────────────
    ("Rodrygo",            "Brazil",     "RW",  0.68,0.42,7.5,25, 0,0.08,0.95),
    ("Endrick",            "Brazil",     "ST",  0.62,0.40,5.5,19, 0,0.10,0.85),
    ("Lucas Paqueta",      "Brazil",     "CAM", 0.30,0.25,8.5,28, 0,0.08,0.95),
    # ── Belgium ──────────────────────────────────────────────────────────────
    ("Kevin De Bruyne",    "Belgium",    "CM",  0.38,0.30,9.5,34, 0,0.12,0.85),
    ("Jeremy Doku",        "Belgium",    "RW",  0.52,0.38,8.5,23, 0,0.08,0.95),
    ("Yannick Carrasco",   "Belgium",    "LW",  0.40,0.32,7.5,32, 0,0.10,0.85),
    # ── Netherlands ──────────────────────────────────────────────────────────
    ("Xavi Simons",        "Netherlands","CAM", 0.45,0.35,9.0,23, 0,0.08,0.90),
    ("Memphis Depay",      "Netherlands","ST",  0.52,0.45,7.0,31, 1,0.12,0.80),
    ("Tijjani Reijnders",  "Netherlands","CM",  0.35,0.28,7.5,27, 0,0.08,0.95),
    # ── Colombia ─────────────────────────────────────────────────────────────
    ("James Rodriguez",    "Colombia",   "CAM", 0.28,0.30,8.5,34, 6,0.12,0.85),
    ("Luis Diaz",          "Colombia",   "LW",  0.52,0.35,7.5,28, 0,0.08,1.00),
    ("Jhon Duran",         "Colombia",   "ST",  0.62,0.40,5.0,21, 0,0.05,0.90),
    ("Richard Rios",       "Colombia",   "CM",  0.20,0.18,7.5,25, 0,0.05,0.95),
    # ── Morocco ──────────────────────────────────────────────────────────────
    ("Achraf Hakimi",      "Morocco",    "RW",  0.42,0.30,8.0,26, 0,0.05,1.00),
    ("Hakim Ziyech",       "Morocco",    "CAM", 0.28,0.35,8.5,32, 0,0.10,0.85),
    ("Youssef En-Nesyri",  "Morocco",    "ST",  0.55,0.45,5.5,28, 1,0.05,0.95),
    ("Sofiane Boufal",     "Morocco",    "LW",  0.28,0.25,7.5,31, 0,0.10,0.80),
    # ── Mexico ───────────────────────────────────────────────────────────────
    ("Hirving Lozano",     "Mexico",     "RW",  0.42,0.38,7.0,30, 0,0.10,0.90),
    ("Santiago Gimenez",   "Mexico",     "ST",  0.78,0.45,5.0,24, 0,0.05,0.95),
    ("Raul Jimenez",       "Mexico",     "ST",  0.42,0.35,5.0,34, 2,0.15,0.80),
    ("Edson Alvarez",      "Mexico",     "CM",  0.18,0.12,7.0,28, 0,0.05,1.00),
    # ── Japan ────────────────────────────────────────────────────────────────
    ("Takefusa Kubo",      "Japan",      "RW",  0.48,0.35,8.5,24, 0,0.08,0.95),
    ("Kaoru Mitoma",       "Japan",      "LW",  0.45,0.38,8.0,28, 0,0.08,1.00),
    ("Junya Ito",          "Japan",      "RW",  0.38,0.35,7.5,32, 0,0.10,0.90),
    ("Wataru Endo",        "Japan",      "CM",  0.15,0.10,7.0,32, 0,0.08,0.95),
    # ── Croatia ──────────────────────────────────────────────────────────────
    ("Luka Modric",        "Croatia",    "CM",  0.22,0.22,9.5,40, 1,0.15,0.85),
    ("Andrej Kramaric",    "Croatia",    "ST",  0.62,0.50,6.5,34, 2,0.08,0.90),
    ("Mateo Kovacic",      "Croatia",    "CM",  0.18,0.16,8.0,31, 0,0.10,0.95),
    ("Ivan Perisic",       "Croatia",    "LW",  0.32,0.28,7.0,36, 6,0.12,0.80),
    # ── Switzerland ──────────────────────────────────────────────────────────
    ("Breel Embolo",       "Switzerland","ST",  0.52,0.48,5.5,28, 0,0.08,0.90),
    ("Granit Xhaka",       "Switzerland","CM",  0.18,0.14,7.5,33, 0,0.08,1.00),
    ("Xherdan Shaqiri",    "Switzerland","CAM", 0.28,0.32,7.5,33, 2,0.12,0.80),
    ("Ruben Vargas",       "Switzerland","LW",  0.38,0.32,7.0,27, 0,0.08,0.90),
    # ── Ecuador ──────────────────────────────────────────────────────────────
    ("Moises Caicedo",     "Ecuador",    "CM",  0.15,0.10,7.5,24, 0,0.05,1.00),
    ("Enner Valencia",     "Ecuador",    "ST",  0.48,0.52,5.0,36, 3,0.12,0.80),
    ("Jeremy Sarmiento",   "Ecuador",    "LW",  0.32,0.28,7.5,23, 0,0.10,0.85),
    ("Kevin Rodriguez",    "Ecuador",    "RW",  0.35,0.30,7.0,26, 0,0.08,0.85),
    # ── Senegal ──────────────────────────────────────────────────────────────
    ("Sadio Mane",         "Senegal",    "LW",  0.52,0.45,7.5,33, 0,0.12,0.90),
    ("Ismaila Sarr",       "Senegal",    "RW",  0.38,0.35,7.5,27, 0,0.08,0.90),
    ("Iliman Ndiaye",      "Senegal",    "CAM", 0.42,0.38,8.0,25, 0,0.08,0.90),
    ("Pape Matar Sarr",    "Senegal",    "CM",  0.18,0.12,7.5,23, 0,0.05,0.90),
    # ── Austria ──────────────────────────────────────────────────────────────
    ("Marcel Sabitzer",    "Austria",    "CM",  0.32,0.28,7.5,31, 0,0.08,0.95),
    ("Christoph Baumgartner","Austria",  "CAM", 0.42,0.38,7.5,25, 0,0.08,0.90),
    ("Michael Gregoritsch","Austria",    "ST",  0.52,0.45,5.5,31, 0,0.08,0.85),
    ("Patrick Wimmer",     "Austria",    "RW",  0.38,0.30,7.5,24, 0,0.08,0.85),
    # ── Turkey ───────────────────────────────────────────────────────────────
    ("Hakan Calhanoglu",   "Turkey",     "CM",  0.22,0.20,9.0,31, 0,0.08,0.95),
    ("Arda Guler",         "Turkey",     "CAM", 0.52,0.38,9.0,21, 0,0.08,0.90),
    ("Ferdi Kadioglu",     "Turkey",     "LW",  0.32,0.25,7.5,25, 0,0.08,0.90),
    ("Kenan Yildiz",       "Turkey",     "RW",  0.45,0.35,8.5,20, 0,0.05,0.85),
    # ── Australia ────────────────────────────────────────────────────────────
    ("Mathew Leckie",      "Australia",  "RW",  0.32,0.30,7.0,34, 0,0.08,0.90),
    ("Mitchell Duke",      "Australia",  "ST",  0.42,0.38,5.0,34, 0,0.10,0.80),
    ("Riley McGree",       "Australia",  "CM",  0.25,0.20,7.5,26, 0,0.08,0.90),
    ("Cameron Devlin",     "Australia",  "CM",  0.22,0.18,6.5,27, 0,0.08,0.85),
    # ── Ghana ────────────────────────────────────────────────────────────────
    ("Mohammed Kudus",     "Ghana",      "CAM", 0.52,0.42,8.0,25, 0,0.08,0.95),
    ("Jordan Ayew",        "Ghana",      "ST",  0.38,0.35,6.5,33, 0,0.10,0.85),
    ("Andre Ayew",         "Ghana",      "RW",  0.32,0.28,7.0,35, 2,0.12,0.75),
    ("Abdul Fatawu",       "Ghana",      "RW",  0.45,0.32,8.0,21, 0,0.05,0.85),
    # ── Iran ─────────────────────────────────────────────────────────────────
    ("Mehdi Taremi",       "Iran",       "ST",  0.62,0.55,6.0,33, 3,0.10,1.00),
    ("Sardar Azmoun",      "Iran",       "ST",  0.52,0.48,6.5,30, 2,0.12,0.85),
    ("Alireza Jahanbakhsh","Iran",       "RW",  0.28,0.25,7.5,32, 0,0.10,0.85),
    ("Ali Gholizadeh",     "Iran",       "LW",  0.32,0.28,7.5,29, 0,0.08,0.85),
    # ── Ivory Coast ──────────────────────────────────────────────────────────
    ("Simon Adingra",      "Ivory Coast","RW",  0.42,0.38,8.0,23, 0,0.08,0.90),
    ("Sebastien Haller",   "Ivory Coast","ST",  0.52,0.48,5.5,31, 0,0.12,0.85),
    ("Franck Kessie",      "Ivory Coast","CM",  0.18,0.15,7.0,29, 0,0.08,0.90),
    ("Nicolas Pepe",       "Ivory Coast","RW",  0.32,0.28,7.5,30, 0,0.10,0.80),
    # ── Scotland ─────────────────────────────────────────────────────────────
    ("Scott McTominay",    "Scotland",   "CM",  0.38,0.35,7.5,28, 0,0.05,1.00),
    ("Andrew Robertson",   "Scotland",   "LW",  0.22,0.18,7.0,31, 0,0.08,0.95),
    ("Ryan Christie",      "Scotland",   "CAM", 0.38,0.32,7.5,29, 0,0.08,0.85),
    ("Lyndon Dykes",       "Scotland",   "ST",  0.38,0.35,4.5,30, 0,0.08,0.85),
    # ── Algeria ──────────────────────────────────────────────────────────────
    ("Riyad Mahrez",       "Algeria",    "RW",  0.42,0.38,8.5,35, 0,0.12,0.85),
    ("Youcef Atal",        "Algeria",    "RW",  0.32,0.28,7.5,29, 0,0.10,0.85),
    ("Houssem Aouar",      "Algeria",    "CAM", 0.28,0.22,8.0,27, 0,0.08,0.85),
    ("Islam Slimani",      "Algeria",    "ST",  0.38,0.42,5.5,37, 0,0.15,0.70),
    # ── Paraguay ─────────────────────────────────────────────────────────────
    ("Miguel Almiron",     "Paraguay",   "CAM", 0.32,0.28,7.5,31, 0,0.08,0.95),
    ("Carlos Alcaraz",     "Paraguay",   "CM",  0.32,0.25,7.5,23, 0,0.05,0.90),
    ("Julio Enciso",       "Paraguay",   "RW",  0.38,0.32,8.0,22, 0,0.08,0.85),
    ("Omar Alderete",      "Paraguay",   "CM",  0.15,0.10,6.5,28, 0,0.08,0.85),
    # ── Tunisia ──────────────────────────────────────────────────────────────
    ("Wahbi Khazri",       "Tunisia",    "CAM", 0.38,0.32,7.5,33, 0,0.10,0.80),
    ("Ellyes Skhiri",      "Tunisia",    "CM",  0.15,0.10,7.0,30, 0,0.08,0.90),
    ("Youssef Msakni",     "Tunisia",    "CAM", 0.28,0.25,7.5,35, 0,0.12,0.75),
    ("Naim Sliti",         "Tunisia",    "RW",  0.32,0.28,7.0,33, 0,0.10,0.80),
    # ── Saudi Arabia ─────────────────────────────────────────────────────────
    ("Mohammed Al-Dawsari","Saudi Arabia","LW",  0.42,0.38,7.5,31, 1,0.08,0.90),
    ("Saleh Al-Shehri",    "Saudi Arabia","ST",  0.42,0.38,5.5,31, 1,0.08,0.90),
    ("Sami Al-Najei",      "Saudi Arabia","CM",  0.15,0.12,6.5,27, 0,0.08,0.85),
    ("Abdullah Al-Hamdan", "Saudi Arabia","ST",  0.38,0.32,5.5,26, 0,0.05,0.80),
    # ── Czechia ──────────────────────────────────────────────────────────────
    ("Patrik Schick",      "Czechia",    "ST",  0.62,0.52,5.5,30, 2,0.10,0.90),
    ("Tomas Soucek",       "Czechia",    "CM",  0.22,0.20,6.5,30, 0,0.08,0.95),
    ("Antonin Barak",      "Czechia",    "CAM", 0.32,0.28,7.5,30, 0,0.08,0.85),
    ("Tomas Holes",        "Czechia",    "CM",  0.12,0.08,6.5,29, 0,0.08,0.85),
    # ── South Africa ─────────────────────────────────────────────────────────
    ("Percy Tau",          "South Africa","LW",  0.32,0.28,7.5,31, 0,0.08,0.90),
    ("Bongani Zungu",      "South Africa","CM",  0.15,0.10,6.5,32, 0,0.10,0.80),
    ("Evidence Makgopa",   "South Africa","ST",  0.42,0.35,5.5,26, 0,0.08,0.90),
    ("Themba Zwane",       "South Africa","CAM", 0.28,0.22,7.5,34, 0,0.10,0.80),
    # ── Bosnia ───────────────────────────────────────────────────────────────
    ("Edin Dzeko",         "Bosnia",     "ST",  0.32,0.32,5.5,39, 0,0.20,0.70),
    ("Miralem Pjanic",     "Bosnia",     "CM",  0.18,0.14,8.5,35, 0,0.15,0.75),
    ("Haris Seferovic",    "Bosnia",     "ST",  0.38,0.32,5.0,33, 0,0.10,0.80),
    ("Ermedin Demirovic",  "Bosnia",     "ST",  0.52,0.42,6.0,27, 0,0.08,0.90),
    # ── Qatar ────────────────────────────────────────────────────────────────
    ("Akram Afif",         "Qatar",      "LW",  0.38,0.35,8.0,28, 0,0.08,0.95),
    ("Almoez Ali",         "Qatar",      "ST",  0.42,0.40,5.5,28, 5,0.05,1.00),
    ("Hassan Al-Haydos",   "Qatar",      "CAM", 0.28,0.25,7.5,34, 0,0.10,0.90),
    ("Ismaeel Mohammad",   "Qatar",      "CM",  0.15,0.10,6.5,27, 0,0.08,0.85),
    # ── Congo DR ─────────────────────────────────────────────────────────────
    ("Theo Bongonda",      "Congo DR",   "RW",  0.38,0.32,7.5,29, 0,0.08,0.85),
    ("Cedric Bakambu",     "Congo DR",   "ST",  0.42,0.38,5.5,34, 0,0.10,0.80),
    ("Yoane Wissa",        "Congo DR",   "ST",  0.48,0.38,6.5,29, 0,0.08,0.90),
    ("Chancel Mbemba",     "Congo DR",   "CM",  0.10,0.08,5.5,31, 0,0.08,0.85),
    # ── Uzbekistan ───────────────────────────────────────────────────────────
    ("Eldor Shomurodov",   "Uzbekistan", "ST",  0.48,0.42,5.5,29, 0,0.08,0.95),
    ("Otabek Shukurov",    "Uzbekistan", "CM",  0.18,0.14,7.0,28, 0,0.08,0.85),
    ("Khasan Mukhammad",   "Uzbekistan", "RW",  0.28,0.22,7.5,25, 0,0.08,0.85),
    ("Jaloliddin Masharipov","Uzbekistan","CAM", 0.22,0.18,8.0,30, 0,0.08,0.85),
    # ── Jordan ───────────────────────────────────────────────────────────────
    ("Musa Al-Taamari",    "Jordan",     "RW",  0.32,0.28,7.5,27, 0,0.08,0.90),
    ("Yazan Al-Naimat",    "Jordan",     "ST",  0.38,0.32,5.5,25, 0,0.08,0.85),
    ("Baha Faisal",        "Jordan",     "CM",  0.18,0.15,6.5,25, 0,0.08,0.85),
    # ── Iraq ─────────────────────────────────────────────────────────────────
    ("Mohanad Ali",        "Iraq",       "ST",  0.42,0.38,5.5,26, 0,0.08,0.85),
    ("Aymen Hussein",      "Iraq",       "ST",  0.38,0.32,5.5,28, 0,0.08,0.85),
    ("Ali Jasim",          "Iraq",       "RW",  0.30,0.25,7.5,22, 0,0.05,0.85),
    # ── New Zealand ──────────────────────────────────────────────────────────
    ("Chris Wood",         "New Zealand","ST",  0.38,0.38,4.5,33, 0,0.10,0.90),
    ("Clayton Lewis",      "New Zealand","CM",  0.22,0.18,7.0,27, 0,0.08,0.85),
    ("Elijah Just",        "New Zealand","RW",  0.28,0.22,7.0,24, 0,0.08,0.80),
    # ── Cabo Verde ───────────────────────────────────────────────────────────
    ("Garry Rodrigues",    "Cabo Verde", "RW",  0.28,0.25,7.5,34, 0,0.10,0.80),
    ("Julio Tavares",      "Cabo Verde", "ST",  0.28,0.25,5.5,37, 0,0.15,0.70),
    ("Ryan Mendes",        "Cabo Verde", "LW",  0.25,0.20,7.0,35, 0,0.12,0.75),
    # ── Curacao ──────────────────────────────────────────────────────────────
    ("Leandro Bacuna",     "Curacao",    "CM",  0.18,0.15,7.0,33, 0,0.10,0.80),
    ("Jurien Gaari",       "Curacao",    "ST",  0.28,0.22,5.0,28, 0,0.10,0.80),
    ("Cuco Martina",       "Curacao",    "RW",  0.10,0.08,5.5,35, 0,0.12,0.75),
    # ── Panama ───────────────────────────────────────────────────────────────
    ("Rolando Blackburn",  "Panama",     "ST",  0.32,0.30,5.5,28, 0,0.08,0.85),
    ("Ismael Diaz",        "Panama",     "ST",  0.42,0.32,5.5,23, 0,0.08,0.85),
    ("Alberto Quintero",   "Panama",     "LW",  0.28,0.25,7.0,36, 0,0.15,0.75),
    # ── Haiti ────────────────────────────────────────────────────────────────
    ("Frantzdy Pierrot",   "Haiti",      "ST",  0.38,0.32,5.5,27, 0,0.08,0.85),
    ("James Lea Siliki",   "Haiti",      "CM",  0.22,0.18,7.0,29, 0,0.08,0.85),
    ("Duckens Nazon",      "Haiti",      "ST",  0.32,0.28,5.5,32, 0,0.10,0.80),
]

NARRATIVE_BONUS = {
    "Lionel Messi":0.90,"Cristiano Ronaldo":0.85,"Kylian Mbappe":0.80,
    "Lamine Yamal":0.95,"Erling Haaland":0.75,"Harry Kane":0.70,
    "Jude Bellingham":0.72,"Bruno Fernandes":0.78,"Martin Odegaard":0.65,
}

BOOT_MARKET = {
    "Kylian Mbappe":0.152,"Harry Kane":0.125,"Erling Haaland":0.092,
    "Viktor Gyokeres":0.048,"Mikel Oyarzabal":0.044,"Julian Alvarez":0.042,
    "Raphinha":0.035,"Lautaro Martinez":0.038,"Kai Havertz":0.030,
    "Jonathan David":0.031,"Michael Olise":0.025,"Lamine Yamal":0.024,
    "Lionel Messi":0.022,"Darwin Nunez":0.020,"Cody Gakpo":0.018,
    "Cristiano Ronaldo":0.018,"Vinicius Jr":0.016,"Alexander Isak":0.015,
}

BALL_MARKET = {
    "Lamine Yamal":0.12,"Kylian Mbappe":0.10,"Michael Olise":0.10,
    "Lionel Messi":0.07,"Vinicius Jr":0.07,"Harry Kane":0.06,
    "Jude Bellingham":0.04,"Erling Haaland":0.04,"Bruno Fernandes":0.04,
    "Pedri":0.04,"Florian Wirtz":0.03,"Jamal Musiala":0.03,
    "Martin Odegaard":0.03,"Federico Valverde":0.02,"Bukayo Saka":0.02,
}

def simulate_golden_awards(tournament_probs, n=20_000):
    boot_counts = defaultdict(int); ball_counts = defaultdict(int)
    games_by_round = {"eliminated_group":2.5,"r32":3.0,"r16":4.0,"qf":5.0,"sf":6.0,"finalist":7.0,"winner":7.0}
    round_order    = ["eliminated_group","r32","r16","qf","sf","finalist","winner"]
    for _ in range(n):
        team_round = {}
        for team,p in tournament_probs.items():
            roll = random.random()*100; cumul=0; chosen="eliminated_group"
            for rnd in reversed(round_order):
                cumul += p.get(rnd,0)
                if roll <= cumul: chosen=rnd; break
            team_round[team] = chosen
        p_goals={}; p_ball={}
        for row in PLAYERS:
            name,team,pos,club_gpg,intl_gpg,creat,age,wc_ped,inj_risk,start_cert = row
            gp = games_by_round.get(team_round.get(team,"eliminated_group"),2.5)
            if random.random() < inj_risk: gp *= 0.4
            gp *= start_cert
            age_f = 1.0 if age<=32 else max(0.6,1.0-(age-32)*0.06)
            gpg = (intl_gpg*0.65 + club_gpg*0.35)*age_f
            goals = poisson(max(0.01, gpg*gp))
            p_goals[name] = goals
            tadv = round_order.index(team_round.get(team,"eliminated_group"))/(len(round_order)-1)
            big  = (goals*(tadv**1.2))/max(1,gp)*3
            narr = NARRATIVE_BONUS.get(name,0.50)
            p_ball[name] = (0.30*min(goals/8,1)+0.22*(creat/10)*(tadv**0.5)+
                            0.28*tadv+0.12*min(big/3,1)+0.08*narr)
        mg = max(p_goals.values()); cands=[n2 for n2,g in p_goals.items() if g==mg]
        bw = max(cands, key=lambda x: next((r[4] for r in PLAYERS if r[0]==x),0))
        boot_counts[bw]+=1; ball_counts[max(p_ball,key=p_ball.get)]+=1
    def blend(mc,mk,wm=0.60): return wm*mc+(1-wm)*mk
    tot_b=sum(boot_counts.values()) or 1; tot_bl=sum(ball_counts.values()) or 1
    bp={name:round(blend(boot_counts[name]/tot_b, BOOT_MARKET.get(name,0.005))*100,2) for name,*_ in PLAYERS}
    blp={name:round(blend(ball_counts[name]/tot_bl,BALL_MARKET.get(name,0.005))*100,2) for name,*_ in PLAYERS}
    return bp, blp

def print_golden_awards(boot_probs, ball_probs):
    boot_s = sorted(boot_probs.items(),key=lambda x:x[1],reverse=True)[:20]
    ball_s = sorted(ball_probs.items(),key=lambda x:x[1],reverse=True)[:20]
    def gp(name): return next((r for r in PLAYERS if r[0]==name),None)
    print("\n"+"═"*80)
    print("  ⚽  GOLDEN BOOT PROBABILITY  (model 60% + market 40%)")
    print("═"*80)
    print(f"  {'Player':<24} {'Team':<12} {'ClubGPG':>7} {'IntGPG':>7}  {'Prob%':>6}  Bar")
    print("─"*80)
    for name,prob in boot_s:
        p=gp(name)
        if not p: continue
        _,team,_,cgpg,igpg,_,_,_,_,_ = p
        fl=FLAGS.get(team,"  ")
        print(f"  {name:<24} {fl}{team:<9} {cgpg:>7.2f} {igpg:>7.2f}  {prob:>5.1f}%  {bar(prob,20)}")
    print("─"*80)
    print("  Model: Poisson(intl×0.65+club×0.35 × games × age_curve) + market blend")
    print("\n"+"═"*80)
    print("  🌟  GOLDEN BALL PROBABILITY  (model 60% + market 40%)")
    print("═"*80)
    print(f"  {'Player':<24} {'Team':<12} {'Creat':>6} {'Narr':>6} {'Prob%':>6}  Bar")
    print("─"*80)
    for name,prob in ball_s:
        p=gp(name)
        if not p: continue
        _,team,_,_,_,creat,_,_,_,_ = p
        fl=FLAGS.get(team,"  "); narr=NARRATIVE_BONUS.get(name,0.50)
        print(f"  {name:<24} {fl}{team:<9} {creat:>6.1f} {narr:>6.2f}  {prob:>5.1f}%  {bar(prob,20)}")
    print("─"*80)
    print("  Model: Goals(30%)+Creativity(22%)+TeamAdvance(28%)+BigMoments(12%)+Narrative(8%)")
    print("═"*80+"\n")

# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="WC 2026 80-Variable Simulator v4")
    parser.add_argument("--sims",      type=int, default=50_000)
    parser.add_argument("--json",      action="store_true")
    parser.add_argument("--top",       type=int, default=48)
    parser.add_argument("--match",     nargs=2, metavar=("A","B"))
    parser.add_argument("--team",      type=str)
    parser.add_argument("--breakdown", action="store_true")
    parser.add_argument("--games",     action="store_true")
    parser.add_argument("--stages",    action="store_true")
    parser.add_argument("--charts",    action="store_true")
    args = parser.parse_args()

    if args.match:
        a = next((t for t in ELO if t.lower()==args.match[0].lower()),None)
        b = next((t for t in ELO if t.lower()==args.match[1].lower()),None)
        if not a or not b: print("Team not found."); return
        match_preview(a, b); return

    if args.games:
        print_game_predictions(sims=min(args.sims, 20_000)); return

    print(f"\n  ⚽  Running {args.sims:,} simulations across 80+ variables…")
    probs = run_simulations(args.sims)

    if args.breakdown:
        print_breakdown(probs); return

    if args.team:
        m = next((t for t in ELO if t.lower()==args.team.lower()),None)
        if not m: print(f"'{args.team}' not found."); return
        print_team_detail(m, probs); return

    print_results(probs, top_n=args.top)

    if args.stages:
        print_stage_records(probs)

    print("  🏅  Simulating Golden Boot & Golden Ball…")
    boot_probs, ball_probs = simulate_golden_awards(probs, n=min(args.sims,20_000))
    print_golden_awards(boot_probs, ball_probs)

    if args.charts:
        print("  📊  Generating charts…")
        generate_charts(probs)

    if args.json:
        with open("results_v4.json","w") as f:
            json.dump({"tournament":probs,"golden_boot":boot_probs,"golden_ball":ball_probs},f,indent=2)
        print("  📄  results_v4.json exported\n")

if __name__ == "__main__":
    main()
