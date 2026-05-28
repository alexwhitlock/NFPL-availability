#!/usr/bin/env python3
"""
check_nfpl.py  —  North Frontenac Parklands availability checker
Checks sites available for Jul 17–19 2026 (2 nights).
Emails only when NEW sites appear since the last run.
First run reports all currently available sites as a baseline.

Cron (5am daily on t3600):
    0 5 * * * /usr/bin/python3 /home/alex/scripts/check_nfpl.py >> /home/alex/logs/nfpl.log 2>&1
"""

import json
import smtplib
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

# ── CONFIG ────────────────────────────────────────────────────────────────────

CHECK_IN  = "2026-07-17"
CHECK_OUT = "2026-07-19"   # exclusive end — nights checked: Jul 17 and Jul 18

SMTP_HOST     = "smtp.gmail.com"
SMTP_PORT     = 587
SMTP_USER     = "alexmwhitlock@gmail.com"   # Gmail account
try:
    from config import SMTP_PASSWORD
except ImportError:
    import os
    SMTP_PASSWORD = os.environ.get("NFPL_SMTP_PASSWORD", "")
NOTIFY_TO     = "alexmwhitlock@gmail.com"

STATE_FILE    = Path(__file__).parent / "nfpl_state.json"
BOOKING_URL   = "https://www.onressystems.com/reservations/?property=north-frontenac-park-lands"
AJAX_URL      = "https://www.onressystems.com/Reservations/AjaxServices.ashx"
VENDOR_ID     = "281"

# ── FULL PRODUCT LIST (all 174 sites) ────────────────────────────────────────

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
).replace("\n", "").replace(" ", "")

# ── SITE NAME LOOKUP (prodId -> human name, from mapview?vendorid=281) ────────

SITE_NAMES = {
    2617: 'Govan Site 1 - VEHICLE ACCESS SITE',
    2618: 'Govan Site 2',
    2619: 'Govan Site 3',
    2620: 'Govan Site 4',
    2621: 'Govan Site 5',
    2622: 'Govan Site 6',
    2624: 'Govan Site 8',
    2625: 'Govan Site 9',
    2626: 'Govan Site 10 - VEHICLE ACCESS SITE',
    2627: 'Granite Site 1 - VEHICLE ACCESS SITE',
    2628: 'Granite Site 2 - VEHICLE ACCESS SITE',
    2629: 'Granite Site 3 - VEHICLE ACCESS SITE',
    2630: 'Hungry Site 1 - VEHICLE ACCESS SITE',
    2631: 'Hungry Site 2 - VEHICLE ACCESS SITE',
    2634: 'Kashwakamak Site 3',
    2635: 'Kashwakamak Site 4',
    2636: 'Kashwakamak Site 5',
    2637: 'Kashwakamak Site 6',
    2638: 'Kashwakamak Site 7',
    2639: 'Kashwakamak Site 8',
    2641: 'Kashwakamak Site 10',
    2642: 'Kashwakamak Site 11',
    2643: 'Kashwakamak Site 12 - VEHICLE ACCESS SITE',
    2644: 'Kashwakamak Site 13',
    2646: 'Kashwakamak Site 15',
    2647: 'Kashwakamak Site 16',
    2649: 'Kashwakamak Site 18',
    2650: 'Kashwakamak Site 19',
    2651: 'Mair Site 1',
    2652: 'Mair Site 2',
    2653: 'Mair Site 3',
    2654: 'Mair Site 4',
    2655: 'Mair Site 5',
    2656: 'Mair Site 6',
    2658: 'Mair Site 8',
    2660: 'Mair Site 10',
    2661: 'Mair Site 11',
    2662: 'Mair Site 12 - VEHICLE ACCESS SITE',
    2664: 'Redhorse Site 1',
    2665: 'Redhorse Site 2',
    2666: 'Redhorse Site 3',
    2667: 'Redhorse Site 4',
    2668: 'Redhorse Site 5',
    2669: 'Redhorse Site 6',
    2670: 'Redhorse Site 7',
    2671: 'Redhorse Site 8 - VEHICLE ACCESS SITE',
    2672: 'Round Schooner Site 1',
    2673: 'Round Schooner Site 2',
    2674: 'Round Schooner Site 3',
    2675: 'Round Schooner Site 4',
    2676: 'Round Schooner Site 5',
    2677: 'Round Schooner Site 6',
    2678: 'Round Schooner Site 7',
    2679: 'Round Schooner Site 8',
    2681: 'Round Schooner Site 10',
    2682: 'Round Schooner Site 11',
    2688: 'Big Gull Site 01',
    2689: 'Big Gull Site 02',
    2690: 'Big Gull Site 3',
    2691: 'Big Gull Site 4',
    2693: 'Big Gull Site 6',
    2694: 'Big Gull Site 7',
    2695: 'Big Gull Site 8',
    2696: 'Big Gull Site 9',
    2697: 'Big Gull Site 10',
    2698: 'Big Gull Site 11',
    2699: 'Big Gull Site 12',
    2700: 'Big Gull Site 13',
    2702: 'Big Gull Site 15',
    2703: 'Big Gull Site 16',
    2704: 'Big Gull Site 17',
    2707: 'Big Gull Site 20',
    2709: 'Big Gull Site 22',
    2710: 'Big Gull Site 23',
    2711: 'Big Gull Site 24',
    2723: 'Crotch Site 1 - VEHICLE ACCESS SITE',
    2724: 'Crotch Site 2 - VEHICLE ACCESS SITE',
    2725: 'Crotch Site 3 - VEHICLE ACCESS SITE',
    2726: 'Crotch Site 4 - VEHICLE ACCESS SITE',
    2727: 'Crotch Site 5',
    2728: 'Crotch Site 6',
    2729: 'Crotch Site 7',
    2730: 'Crotch Site 8',
    2731: 'Crotch Site 9',
    2732: 'Crotch Site 10',
    2734: 'Crotch Site 12',
    2735: 'Crotch Site 13',
    2736: 'Crotch Site 14',
    2738: 'Crotch Site 16',
    2739: 'Crotch Site 17',
    2740: 'Crotch Site 18',
    2741: 'Crotch Site 19',
    2743: 'Crotch Site 21',
    2744: 'Crotch Site 22',
    2745: 'Crotch Site 23',
    2746: 'Crotch Site 24',
    2747: 'Crotch Site 25',
    2748: 'Crotch Site 26',
    2749: 'Crotch Site 27',
    2750: 'Crotch Site 28',
    2751: 'Crotch Site 29',
    2752: 'Crotch Site 30',
    2753: 'Crotch Site 31',
    2755: 'Crotch Site 33',
    2757: 'Crotch Site 35',
    2758: 'Crotch Site 36',
    2759: 'Crotch Site 37',
    2760: 'Crotch Site 38',
    2761: 'Crotch Site 39',
    2762: 'Crotch Site 40',
    2764: 'Crotch Site 42',
    2765: 'Crotch Site 43',
    2767: 'Crotch Site 45',
    2768: 'Crotch Site 46',
    2769: 'Crotch Site 47',
    2771: 'Crotch Site 49',
    2772: 'Crotch Site 50',
    2773: 'Crotch Site 51',
    2774: 'Crotch Site 52',
    2775: 'Crotch Site 53',
    2776: 'Crotch Site 54',
    2777: 'Crotch Site 55',
    2778: 'Crotch Site 56',
    2779: 'Crotch Site 57',
    2780: 'Crotch Site 58',
    2781: 'Crotch Site 59',
    2782: 'Crotch Site 60',
    2783: 'Crotch Site 61',
    2784: 'Crotch Site 62',
    2785: 'Crotch Site 63',
    2786: 'Crotch Site 64',
    2787: 'Crotch Site 65',
    2788: 'Crotch Site 66',
    2789: 'Crotch Site 67',
    2790: 'Crotch Site 68',
    2791: 'Crotch Site 69',
    2792: 'Crotch Site 70',
    2793: 'Crotch Site 71',
    2794: 'Crotch Site 72',
    2795: 'Crotch Site 73',
    2796: 'Crotch Site 74',
    2797: 'Crotch Site 75',
    2798: 'Crotch Site 76',
    2800: 'Long Schooner 12',
    2801: 'Long Schooner 13',
    2802: 'Long Schooner 14',
    2803: 'Long Schooner 15',
    2804: 'Long Schooner 16',
    2805: 'Long Schooner 17',
    2806: 'Long Schooner 18',
    2807: 'Long Schooner 19',
    2808: 'Long Schooner 20',
    2810: 'Long Schooner 22 - VEHICLE ACCESS SITE',
    2811: 'Long Schooner 23 - VEHICLE ACCESS SITE',
    2812: 'Long Schooner 24 - VEHICLE ACCESS SITE',
    3812: 'Long Schooner 25 - VEHICLE ACCESS SITE',
    3813: 'Long Schooner 26 - VEHICLE ACCESS SITE',
    12676: 'Fortune Site 29 - VEHICLE ACCESS SITE',
    12695: 'Fortune Site 30 - VEHICLE ACCESS SITE',
    14710: 'Big Gull Site 21A',
    14711: 'Big Gull Site 22A',
    14781: 'Big Gull Site 7A',
    14782: 'Big Gull Site 7B',
    15303: 'Big Gull Site 21',
    15731: 'Mair Site 9',
    16792: 'Kashwakamak Site 14',
    17102: 'Govan Site 11',
    17125: 'Mair Site 7',
    17244: 'Big Gull Site 25',
    17334: 'Govan Site 7',
    17343: 'Redhorse Site 9',
    17344: 'Kashwakamak Site 14A',
    17345: 'Kashwakamak Site 14B',
    17784: 'Govan Site 12 - VEHICLE ACCESS SITE *NEW*',
}


def site_name(prod_id: int) -> str:
    return SITE_NAMES.get(prod_id, f"Site #{prod_id}")


def fetch_available_ids() -> set[int]:
    """
    POST to OnRes AjaxServices to get all dates with availability.
    Returns product IDs available on every night of the stay
    (i.e. available on Jul 17 AND Jul 18 for a Jul 17-19 booking).
    """
    from datetime import date, timedelta

    checkin  = date.fromisoformat(CHECK_IN)
    checkout = date.fromisoformat(CHECK_OUT)
    nights   = [(checkin + timedelta(days=i)).isoformat()
                for i in range((checkout - checkin).days)]

    post_data = urllib.parse.urlencode({
        "testMode":    "false",
        "vendorId":    VENDOR_ID,
        "sessionToken": "",
        "reqType":     "GET_AVAIL_DATES",
        "productList": FULL_PRODLIST,
        "rooms":       "1",
        "adults":      "2",
        "children":    "0",
        "youth":       "0",
        "senior":      "0",
        "code":        "",
    }).encode("utf-8")

    req = urllib.request.Request(
        AJAX_URL,
        data=post_data,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer":      BOOKING_URL,
            "User-Agent":   "Mozilla/5.0",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        outer = json.loads(resp.read().decode("utf-8"))

    if outer["iResultCode"] != 0:
        raise RuntimeError(f"API error: {outer}")

    avail_dates = json.loads(outer["sResult"])["listAvailDates"]
    date_map = {d["sDate"]: set(d["listProductIDs"]) for d in avail_dates}

    available = None
    for night in nights:
        ids_on_night = date_map.get(night, set())
        available = ids_on_night if available is None else available & ids_on_night

    return available or set()


def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return set(json.load(f))
    return None  # None = first run


def save_state(ids: set[int]):
    with open(STATE_FILE, "w") as f:
        json.dump(sorted(ids), f)


def send_email(subject: str, body: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = SMTP_USER
    msg["To"]      = NOTIFY_TO
    msg.attach(MIMEText(body, "plain"))
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(SMTP_USER, SMTP_PASSWORD)
        smtp.sendmail(SMTP_USER, NOTIFY_TO, msg.as_string())
    print(f"  Email sent: {subject}")


def format_site_list(ids: set[int]) -> str:
    names = sorted(site_name(i) for i in ids)
    return "\n".join(f"  * {n}" for n in names)


def main():
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*55}")
    print(f"NFPL checker  {ts}")
    print(f"Dates: {CHECK_IN} to {CHECK_OUT}")
    print(f"{'='*55}")

    known = load_state()
    first_run = (known is None)

    try:
        available = fetch_available_ids()
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    print(f"Available sites: {len(available)}")
    for pid in sorted(available):
        print(f"  {pid}: {site_name(pid)}")

    if first_run:
        save_state(available)
        if available:
            body = (
                f"NF Parklands checker — first run baseline\n"
                f"Dates: {CHECK_IN} to {CHECK_OUT}\n\n"
                f"Currently available ({len(available)}):\n"
                f"{format_site_list(available)}\n\n"
                f"Book: {BOOKING_URL}"
            )
            send_email(
                f"[NFPL] First run — {len(available)} sites available Jul 17-19",
                body,
            )
        else:
            print("  No sites available. Baseline saved as empty.")
        return

    new_sites  = available - known
    gone_sites = known - available

    if gone_sites:
        print(f"  Gone since last run: {sorted(gone_sites)}")

    if new_sites:
        body = (
            f"New campsites opened at North Frontenac Parklands!\n"
            f"Dates: {CHECK_IN} to {CHECK_OUT}\n\n"
            f"NEW ({len(new_sites)}):\n"
            f"{format_site_list(new_sites)}\n\n"
            f"All currently available ({len(available)}):\n"
            f"{format_site_list(available)}\n\n"
            f"Book now: {BOOKING_URL}"
        )
        send_email(
            f"[NFPL] {len(new_sites)} NEW site(s) open Jul 17-19",
            body,
        )
    else:
        print("  No new sites since last run — no email sent.")

    save_state(available)


if __name__ == "__main__":
    main()
