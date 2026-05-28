#!/usr/bin/env python3
"""
nfpl_proxy.py — tiny HTTP proxy that fetches live availability from OnRes.
Listens on 127.0.0.1:5003.  Nginx proxies /api/availability here.

Run as a service:
    sudo systemctl enable --now nfpl-proxy
"""

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

AJAX_URL  = "https://www.onressystems.com/Reservations/AjaxServices.ashx"
BOOK_URL  = "https://www.onressystems.com/reservations/?property=north-frontenac-park-lands"
VENDOR_ID = "281"

FULL_PRODLIST = (
    "2688,2697,2698,2699,2700,2702,2703,2704,2689,2707,14710,2709,14711,2710,2711,"
    "2690,2691,2693,2694,14781,14782,2695,2696,15303,17244,"
    "2723,2732,2733,2734,2735,2736,2738,2739,2740,2741,2724,2743,2744,2745,2746,"
    "2747,2748,2749,2750,2751,2725,2752,2753,2755,2757,2758,2759,2760,2761,2726,"
    "2762,2764,2765,2767,2768,2769,2771,2727,2772,2773,2774,2775,2776,2777,2778,"
    "2779,2780,2781,2728,2782,2783,2784,2785,2786,2787,2788,2789,2790,2791,2729,"
    "2792,2793,2794,2795,2796,2797,2798,2730,2731,"
    "12676,12695,"
    "2617,2626,17102,17784,2618,2619,2620,2621,2622,17334,2624,2625,"
    "2627,2628,2629,2630,2631,"
    "2632,2641,2642,2643,2644,16792,17344,17345,2646,2647,2648,2649,2650,"
    "2633,2634,2635,2636,2637,2638,2639,"
    "2800,2801,2802,2803,2804,2805,2806,2807,2808,2810,2811,2812,3812,3813,"
    "2651,2660,2661,2662,2652,2653,2654,2655,2656,17125,2658,15731,"
    "2664,2665,2666,2667,2668,2669,2670,2671,17343,"
    "2672,2681,2682,2673,2674,2675,2676,2677,2678,2679,2680"
).replace("\n", "")

SITE_NAMES = {
    2617: "Govan Site 1 - VEHICLE ACCESS SITE",
    2618: "Govan Site 2",
    2619: "Govan Site 3",
    2620: "Govan Site 4",
    2621: "Govan Site 5",
    2622: "Govan Site 6",
    2624: "Govan Site 8",
    2625: "Govan Site 9",
    2626: "Govan Site 10 - VEHICLE ACCESS SITE",
    2627: "Granite Site 1 - VEHICLE ACCESS SITE",
    2628: "Granite Site 2 - VEHICLE ACCESS SITE",
    2629: "Granite Site 3 - VEHICLE ACCESS SITE",
    2630: "Hungry Site 1 - VEHICLE ACCESS SITE",
    2631: "Hungry Site 2 - VEHICLE ACCESS SITE",
    2634: "Kashwakamak Site 3",
    2635: "Kashwakamak Site 4",
    2636: "Kashwakamak Site 5",
    2637: "Kashwakamak Site 6",
    2638: "Kashwakamak Site 7",
    2639: "Kashwakamak Site 8",
    2641: "Kashwakamak Site 10",
    2642: "Kashwakamak Site 11",
    2643: "Kashwakamak Site 12 - VEHICLE ACCESS SITE",
    2644: "Kashwakamak Site 13",
    2646: "Kashwakamak Site 15",
    2647: "Kashwakamak Site 16",
    2649: "Kashwakamak Site 18",
    2650: "Kashwakamak Site 19",
    2651: "Mair Site 1",
    2652: "Mair Site 2",
    2653: "Mair Site 3",
    2654: "Mair Site 4",
    2655: "Mair Site 5",
    2656: "Mair Site 6",
    2658: "Mair Site 8",
    2660: "Mair Site 10",
    2661: "Mair Site 11",
    2662: "Mair Site 12 - VEHICLE ACCESS SITE",
    2664: "Redhorse Site 1",
    2665: "Redhorse Site 2",
    2666: "Redhorse Site 3",
    2667: "Redhorse Site 4",
    2668: "Redhorse Site 5",
    2669: "Redhorse Site 6",
    2670: "Redhorse Site 7",
    2671: "Redhorse Site 8 - VEHICLE ACCESS SITE",
    2672: "Round Schooner Site 1",
    2673: "Round Schooner Site 2",
    2674: "Round Schooner Site 3",
    2675: "Round Schooner Site 4",
    2676: "Round Schooner Site 5",
    2677: "Round Schooner Site 6",
    2678: "Round Schooner Site 7",
    2679: "Round Schooner Site 8",
    2681: "Round Schooner Site 10",
    2682: "Round Schooner Site 11",
    2688: "Big Gull Site 01",
    2689: "Big Gull Site 02",
    2690: "Big Gull Site 3",
    2691: "Big Gull Site 4",
    2693: "Big Gull Site 6",
    2694: "Big Gull Site 7",
    2695: "Big Gull Site 8",
    2696: "Big Gull Site 9",
    2697: "Big Gull Site 10",
    2698: "Big Gull Site 11",
    2699: "Big Gull Site 12",
    2700: "Big Gull Site 13",
    2702: "Big Gull Site 15",
    2703: "Big Gull Site 16",
    2704: "Big Gull Site 17",
    2707: "Big Gull Site 20",
    2709: "Big Gull Site 22",
    2710: "Big Gull Site 23",
    2711: "Big Gull Site 24",
    2723: "Crotch Site 1 - VEHICLE ACCESS SITE",
    2724: "Crotch Site 2 - VEHICLE ACCESS SITE",
    2725: "Crotch Site 3 - VEHICLE ACCESS SITE",
    2726: "Crotch Site 4 - VEHICLE ACCESS SITE",
    2727: "Crotch Site 5",
    2728: "Crotch Site 6",
    2729: "Crotch Site 7",
    2730: "Crotch Site 8",
    2731: "Crotch Site 9",
    2732: "Crotch Site 10",
    2734: "Crotch Site 12",
    2735: "Crotch Site 13",
    2736: "Crotch Site 14",
    2738: "Crotch Site 16",
    2739: "Crotch Site 17",
    2740: "Crotch Site 18",
    2741: "Crotch Site 19",
    2743: "Crotch Site 21",
    2744: "Crotch Site 22",
    2745: "Crotch Site 23",
    2746: "Crotch Site 24",
    2747: "Crotch Site 25",
    2748: "Crotch Site 26",
    2749: "Crotch Site 27",
    2750: "Crotch Site 28",
    2751: "Crotch Site 29",
    2752: "Crotch Site 30",
    2753: "Crotch Site 31",
    2755: "Crotch Site 33",
    2757: "Crotch Site 35",
    2758: "Crotch Site 36",
    2759: "Crotch Site 37",
    2760: "Crotch Site 38",
    2761: "Crotch Site 39",
    2762: "Crotch Site 40",
    2764: "Crotch Site 42",
    2765: "Crotch Site 43",
    2767: "Crotch Site 45",
    2768: "Crotch Site 46",
    2769: "Crotch Site 47",
    2771: "Crotch Site 49",
    2772: "Crotch Site 50",
    2773: "Crotch Site 51",
    2774: "Crotch Site 52",
    2775: "Crotch Site 53",
    2776: "Crotch Site 54",
    2777: "Crotch Site 55",
    2778: "Crotch Site 56",
    2779: "Crotch Site 57",
    2780: "Crotch Site 58",
    2781: "Crotch Site 59",
    2782: "Crotch Site 60",
    2783: "Crotch Site 61",
    2784: "Crotch Site 62",
    2785: "Crotch Site 63",
    2786: "Crotch Site 64",
    2787: "Crotch Site 65",
    2788: "Crotch Site 66",
    2789: "Crotch Site 67",
    2790: "Crotch Site 68",
    2791: "Crotch Site 69",
    2792: "Crotch Site 70",
    2793: "Crotch Site 71",
    2794: "Crotch Site 72",
    2795: "Crotch Site 73",
    2796: "Crotch Site 74",
    2797: "Crotch Site 75",
    2798: "Crotch Site 76",
    2800: "Long Schooner 12",
    2801: "Long Schooner 13",
    2802: "Long Schooner 14",
    2803: "Long Schooner 15",
    2804: "Long Schooner 16",
    2805: "Long Schooner 17",
    2806: "Long Schooner 18",
    2807: "Long Schooner 19",
    2808: "Long Schooner 20",
    2810: "Long Schooner 22 - VEHICLE ACCESS SITE",
    2811: "Long Schooner 23 - VEHICLE ACCESS SITE",
    2812: "Long Schooner 24 - VEHICLE ACCESS SITE",
    3812: "Long Schooner 25 - VEHICLE ACCESS SITE",
    3813: "Long Schooner 26 - VEHICLE ACCESS SITE",
    12676: "Fortune Site 29 - VEHICLE ACCESS SITE",
    12695: "Fortune Site 30 - VEHICLE ACCESS SITE",
    14710: "Big Gull Site 21A",
    14711: "Big Gull Site 22A",
    14781: "Big Gull Site 7A",
    14782: "Big Gull Site 7B",
    15303: "Big Gull Site 21",
    15731: "Mair Site 9",
    16792: "Kashwakamak Site 14",
    17102: "Govan Site 11",
    17125: "Mair Site 7",
    17244: "Big Gull Site 25",
    17334: "Govan Site 7",
    17343: "Redhorse Site 9",
    17344: "Kashwakamak Site 14A",
    17345: "Kashwakamak Site 14B",
    17784: "Govan Site 12 - VEHICLE ACCESS SITE",
}

LAKE_ORDER = ["Big Gull","Crotch","Fortune","Govan","Granite",
              "Hungry","Kashwakamak","Long Schooner","Mair","Redhorse","Round Schooner"]


SITE_POSITIONS = {
    2617: (45.13691, -76.80487),
    2618: (45.12769, -76.7986),
    2619: (45.13167, -76.80197),
    2620: (45.13134, -76.79914),
    2621: (45.13522, -76.79549),
    2622: (45.1319, -76.79702),
    2624: (45.13145, -76.79017),
    2625: (45.13403, -76.79046),
    2626: (45.1385, -76.803),
    2627: (45.066273, -76.85697),
    2628: (45.06502, -76.85843),
    2629: (45.06491, -76.85874),
    2630: (45.10013, -76.83119),
    2631: (45.099417, -76.832317),
    2634: (44.83168, -77.09184),
    2635: (44.83186, -77.08862),
    2636: (44.83956, -77.08308),
    2637: (44.84233, -77.07875),
    2638: (44.84218, -77.08193),
    2639: (44.84425, -77.08321),
    2641: (44.86304, -77.04897),
    2642: (44.86336, -77.04874),
    2643: (44.86929, -77.0524),
    2644: (44.86323, -77.0481),
    2646: (44.865582, -77.014245),
    2647: (44.860793, -77.023896),
    2649: (44.88582, -76.96811),
    2650: (44.88675, -76.96855),
    2651: (45.10672, -76.82527),
    2652: (45.10664, -76.82662),
    2653: (45.10633, -76.82734),
    2654: (45.10801, -76.83564),
    2655: (45.10911, -76.83651),
    2656: (45.11114, -76.83507),
    2658: (45.11106, -76.83085),
    2660: (45.10973, -76.82826),
    2661: (45.10917, -76.8278),
    2662: (45.11171, -76.82468),
    2664: (45.09087, -76.81668),
    2665: (45.0948, -76.81025),
    2666: (45.09846, -76.80719),
    2667: (45.10095, -76.80317),
    2668: (45.0993, -76.80521),
    2669: (45.09451, -76.80083),
    2670: (45.08866, -76.81738),
    2671: (45.08908, -76.81843),
    2672: (45.12542, -76.9914),
    2673: (45.12491, -76.99352),
    2674: (45.1219, -76.99792),
    2675: (45.11824, -76.99567),
    2676: (45.11684, -76.99341),
    2677: (45.11497, -76.99187),
    2678: (45.1152, -76.98019),
    2679: (45.12173, -76.9831),
    2681: (45.12609, -76.98631),
    2682: (45.12609, -76.984),
    2688: (44.82865, -77.05801),
    2689: (44.8288, -77.05702),
    2690: (44.82636, -77.04908),
    2691: (44.82859, -77.03921),
    2693: (44.82504, -77.00662),
    2694: (44.82487, -77.00151),
    2695: (44.82112, -76.97895),
    2696: (44.82047, -76.97935),
    2697: (44.82643, -76.94195),
    2698: (44.82633, -76.94107),
    2699: (44.83547, -76.96626),
    2700: (44.82879, -76.93538),
    2702: (44.83272, -76.94675),
    2703: (44.834, -76.94096),
    2704: (44.8298, -76.93607),
    2707: (44.82709, -76.92602),
    2709: (44.83637, -76.90427),
    2710: (44.84483, -76.91268),
    2711: (44.84805, -76.89412),
    2723: (44.96499, -76.8238),
    2724: (44.96403, -76.82315),
    2725: (44.96306, -76.82154),
    2726: (44.96289, -76.82053),
    2727: (44.95659, -76.80766),
    2728: (44.95617, -76.80732),
    2729: (44.95468, -76.80479),
    2730: (44.95207, -76.80265),
    2731: (44.95228, -76.79814),
    2732: (44.94512, -76.79009),
    2734: (44.93978, -76.79021),
    2735: (44.93607, -76.78635),
    2736: (44.93557, -76.78493),
    2738: (44.93582, -76.7759),
    2739: (44.93197, -76.78283),
    2740: (44.92893, -76.78437),
    2741: (44.92948, -76.78654),
    2743: (44.93001, -76.79285),
    2744: (44.92869, -76.79255),
    2745: (44.92752, -76.78883),
    2746: (44.92186, -76.79142),
    2747: (44.91995, -76.79133),
    2748: (44.91565, -76.8032),
    2749: (44.90488, -76.81792),
    2750: (44.90368, -76.8145),
    2751: (44.90064, -76.80386),
    2752: (44.89992, -76.79699),
    2753: (44.90076, -76.79337),
    2755: (44.89703, -76.79412),
    2757: (44.901486, -76.787287),
    2758: (44.88688, -76.79551),
    2759: (44.88325, -76.80367),
    2760: (44.88326, -76.80701),
    2761: (44.88106, -76.8041),
    2762: (44.87582, -76.79905),
    2764: (44.8962, -76.82641),
    2765: (44.89273, -76.83349),
    2767: (44.89838, -76.82178),
    2768: (44.89761, -76.82027),
    2769: (44.89503, -76.8156),
    2771: (44.8936, -76.81148),
    2772: (44.89332, -76.81197),
    2773: (44.89263, -76.81101),
    2774: (44.89374, -76.80471),
    2775: (44.89372, -76.80331),
    2776: (44.89547, -76.80129),
    2777: (44.89521, -76.80059),
    2778: (44.89663, -76.80127),
    2779: (44.89771, -76.80228),
    2780: (44.89793, -76.80458),
    2781: (44.90172, -76.8134),
    2782: (44.919383, -76.80616),
    2783: (44.9212, -76.81569),
    2784: (44.91728, -76.82891),
    2785: (44.92163, -76.82719),
    2786: (44.92336, -76.80895),
    2787: (44.92293, -76.80659),
    2788: (44.92366, -76.80402),
    2789: (44.93062, -76.8081),
    2790: (44.93584, -76.80616),
    2791: (44.94365, -76.80029),
    2792: (44.94724, -76.79943),
    2793: (44.95096, -76.80842),
    2794: (44.95155, -76.80865),
    2795: (44.95331, -76.81284),
    2796: (44.95314, -76.81325),
    2797: (44.95311, -76.81385),
    2798: (44.95627, -76.81479),
    2800: (45.10997, -76.97452),
    2801: (45.10756, -76.9737),
    2802: (45.10759, -76.97525),
    2803: (45.10655, -76.97473),
    2804: (45.10585, -76.97465),
    2805: (45.10441, -76.98065),
    2806: (45.10355, -76.98186),
    2807: (45.10151, -76.98108),
    2808: (45.1022, -76.97977),
    2810: (45.09691, -76.99069),
    2811: (45.09677, -76.99043),
    2812: (45.09649, -76.99031),
    3812: (45.09617, -76.99078),
    3813: (45.09626, -76.99018),
    12676: (45.08314, -77.01854),
    12695: (45.08333, -77.01823),
    14710: (44.83534, -76.90924),
    14711: (44.83905, -76.89959),
    14781: (44.821217, -76.9822),
    14782: (44.82174, -76.98109),
    15303: (44.83206, -76.90569),
    15731: (45.111729, -76.828415),
    16792: (44.86828, -77.04016),
    17102: (45.138356, -76.799727),
    17125: (45.110978, -76.831177),
    17244: (44.84107, -76.89815),
    17334: (45.13054, -76.7961),
    17343: (45.09146, -76.80878),
    17344: (44.86687, -77.04411),
    17345: (44.86713, -77.03995),
    17784: (45.134444, -76.808889),
}

SITE_LABELS = {
    2617:'1',2618:'2',2619:'3',2620:'4',2621:'5',2622:'6',2624:'8',2625:'9',
    2626:'10',2627:'1',2628:'2',2629:'3',2630:'1',2631:'2',2634:'3',2635:'4',
    2636:'5',2637:'6',2638:'7',2639:'8',2641:'10',2642:'11',2643:'12',2644:'13',
    2646:'15',2647:'16',2649:'18',2650:'19',2651:'1',2652:'2',2653:'3',2654:'4',
    2655:'5',2656:'6',2658:'8',2660:'10',2661:'11',2662:'12',2664:'1',2665:'2',
    2666:'3',2667:'4',2668:'5',2669:'6',2670:'7',2671:'8',2672:'1',2673:'2',
    2674:'3',2675:'4',2676:'5',2677:'6',2678:'7',2679:'8',2681:'10',2682:'11',
    2688:'1',2689:'2',2690:'3',2691:'4',2693:'6',2694:'7',2695:'8',2696:'9',
    2697:'10',2698:'11',2699:'12',2700:'13',2702:'15',2703:'16',2704:'17',
    2707:'20',2709:'22',2710:'23',2711:'24',2723:'1',2724:'2',2725:'3',2726:'4',
    2727:'5',2728:'6',2729:'7',2730:'8',2731:'9',2732:'10',2734:'12',2735:'13',
    2736:'14',2738:'16',2739:'17',2740:'18',2741:'19',2743:'21',2744:'22',
    2745:'23',2746:'24',2747:'25',2748:'26',2749:'27',2750:'28',2751:'29',
    2752:'30',2753:'31',2755:'33',2757:'35',2758:'36',2759:'37',2760:'38',
    2761:'39',2762:'40',2764:'42',2765:'43',2767:'45',2768:'46',2769:'47',
    2771:'49',2772:'50',2773:'51',2774:'52',2775:'53',2776:'54',2777:'55',
    2778:'56',2779:'57',2780:'58',2781:'59',2782:'60',2783:'61',2784:'62',
    2785:'63',2786:'64',2787:'65',2788:'66',2789:'67',2790:'68',2791:'69',
    2792:'70',2793:'71',2794:'72',2795:'73',2796:'74',2797:'75',2798:'76',
    2800:'12',2801:'13',2802:'14',2803:'15',2804:'16',2805:'17',2806:'18',
    2807:'19',2808:'20',2810:'22',2811:'23',2812:'24',3812:'25',3813:'26',
    12676:'29',12695:'30',14710:'21A',14711:'22A',14781:'7A',14782:'7B',
    15303:'21',15731:'9',16792:'14',17102:'11',17125:'7',17244:'25',17334:'7',
    17343:'9',17344:'14A',17345:'14B',17784:'12',
}

# Load site positions and labels from JSON file (no restart needed for coordinate updates)
_site_data_path = os.path.join(os.path.dirname(__file__), "site-data.json")
try:
    with open(_site_data_path) as f:
        _site_data = json.load(f)
    SITE_POSITIONS = {int(pid): (d['lat'], d['lng']) for pid, d in _site_data.items()}
    SITE_LABELS = {int(pid): d['label'] for pid, d in _site_data.items()}
except Exception as e:
    print(f"Warning: could not load site-data.json: {e}")


# Load site positions and labels from JSON file (no restart needed for coordinate updates)
_site_data_path = os.path.join(os.path.dirname(__file__), "site-data.json")
try:
    with open(_site_data_path) as f:
        _site_data = json.load(f)
    # Override SITE_POSITIONS and SITE_LABELS from JSON
    SITE_POSITIONS = {int(pid): (d['lat'], d['lng']) for pid, d in _site_data.items()}
    SITE_LABELS = {int(pid): d['label'] for pid, d in _site_data.items()}
except Exception as e:
    print(f"Warning: could not load site-data.json: {e}")
    # Fall back to hardcoded values above



def lake_of(name):
    for l in LAKE_ORDER:
        if name.startswith(l):
            return l
    return name.split(" Site")[0]


def fetch_availability():
    post_data = urllib.parse.urlencode({
        "testMode": "false", "vendorId": VENDOR_ID, "sessionToken": "",
        "reqType": "GET_AVAIL_DATES", "productList": FULL_PRODLIST,
        "rooms": "1", "adults": "2", "children": "0",
        "youth": "0", "senior": "0", "code": "",
    }).encode("utf-8")
    req = urllib.request.Request(
        AJAX_URL, data=post_data, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "Referer": BOOK_URL, "User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        outer = json.loads(resp.read().decode("utf-8"))
    avail_dates = json.loads(outer["sResult"])["listAvailDates"]

    # sorted site list with position + label
    by_lake = {l: [] for l in LAKE_ORDER}
    for pid, name in sorted(SITE_NAMES.items()):
        lake = lake_of(name)
        pos  = SITE_POSITIONS.get(pid)
        entry = {"id": pid, "name": name, "lake": lake,
                 "label": SITE_LABELS.get(pid, "?")}
        if pos:
            entry["lat"] = pos[0]
            entry["lng"] = pos[1]
        by_lake.setdefault(lake, []).append(entry)
    sites = []
    for l in LAKE_ORDER:
        sites.extend(by_lake.get(l, []))

    return {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "dates":     [d["sDate"] for d in avail_dates],
        "sites":     sites,
        "avail":     {d["sDate"]: d["listProductIDs"] for d in avail_dates},
    }


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/api/availability":
            self.send_response(404); self.end_headers(); return
        try:
            data  = fetch_availability()
            body  = json.dumps(data, separators=(",", ":")).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type",  "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control",  "no-store")
            self.end_headers()
            self.wfile.write(body)
            print(f"[{datetime.now().isoformat(timespec='seconds')}] served {len(data['dates'])} dates")
        except Exception as e:
            err = str(e).encode()
            self.send_response(502)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(err)))
            self.end_headers()
            self.wfile.write(err)
            print(f"ERROR: {e}")

    def log_message(self, *_):
        pass  # silence default access log


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 5004), Handler)
    print(f"[{datetime.now().isoformat(timespec='seconds')}] nfpl-proxy listening on :5004")
    server.serve_forever()
