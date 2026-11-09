"""Commons items for the caption pilot (spec 2026-11-04-caption-pilot section 4.2). No model call.

    python -I pick_captions.py <project_dir> crawl   # event categories under "<Month> 2026 events", July to October
    python -I pick_captions.py <project_dir> files   # file metadata of those categories, filtered by licence and date
    python -I pick_captions.py <project_dir> events  # thumbnails and one sheet per event category for the agents
    python -I pick_captions.py <project_dir> chunks     # one short metadata file per agent (30 sheets each)
    python -I pick_captions.py <project_dir> assemble   # agent choices to items with one changed fact each
    python -I pick_captions.py <project_dir> large      # 1000 px photos and credits of the assembled items
    python -I pick_captions.py <project_dir> pass2      # inputs for the agents' 1000 px check (16 items each)
    python -I pick_captions.py <project_dir> repair     # new false values or other photos for failed items
    python -I pick_captions.py <project_dir> review     # review.html with every item that passed the check
    python -I pick_captions.py <project_dir> final [ids to drop]   # items.json: 80 kept items, facts in turn
    python -I pick_captions.py <project_dir> verite-sheets   # 1000 px VERITE photos and text-label sheets

Everything goes to data/captions/commons/, or with --set confirm (after the command) to data/captions/commons_confirm/:
new category branches and November, leaving out every category and photo of the exploration set.
Requests to the Commons API wait 2 s between calls.
"""

import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from pathlib import Path

API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "vlm-text-trust-research/0.1 (academic study; one request per 2 s)"}
MONTHS = ("July", "August", "September", "October")
MAX_DEPTH = 4
SKIP = re.compile(r"Wiki Loves|Wiki Science|WikiProject|Photographs by|Videos|Audio|Maps|Logos|Media by", re.I)
MIN_FILES = 4  # direct files a category needs before its files are listed
LICENCES = re.compile(r"^(CC0|Public domain|PD.*|CC BY(-SA)? \d\.\d.*)$", re.I)
START = "2026-07-01"
META_KEYS = ("LicenseShortName", "LicenseUrl", "Artist", "Credit", "ImageDescription", "DateTimeOriginal",
             "Categories", "Restrictions", "GPSLatitude", "GPSLongitude", "ObjectName")


# "commons" is the exploration set (spec 2026-11-04 section 4.2). "commons_confirm" is the confirmation set:
# new category branches and November, without any category or photo the exploration set has seen.
SET = "commons"
CONFIRM_ROOTS = ("Category:2026 sports events", "Category:2026 concerts", "Category:2026 parades",
                 "Category:2026 festivals", "Category:2026 in association football", "Category:November 2026 events")


def out_dir(root):
    path = Path(root) / "data" / "captions" / SET
    path.mkdir(parents=True, exist_ok=True)
    return path


def _explored(root):
    """Category titles and photo page ids of the exploration set, which the confirmation set must not reuse."""
    base = Path(root) / "data" / "captions" / "commons"
    titles = {c["title"] for c in json.loads((base / "categories.json").read_text(encoding="utf-8"))}
    pageids = {f["pageid"] for line in (base / "files.jsonl").read_text(encoding="utf-8").splitlines()
               for f in json.loads(line)["files"]}
    return titles, pageids


def get(params):
    params = {**params, "format": "json", "formatversion": "2"}
    for _ in range(6):
        time.sleep(2)
        try:
            req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 503):
                raise
            time.sleep(30)
        except urllib.error.URLError:
            time.sleep(30)
    raise RuntimeError("Commons API kept refusing")


def members(title, kind, extra, max_pages=None):
    """Members of one category, following continuation (up to `max_pages` requests when given)."""
    cont, pages, calls = {}, [], 0
    while True:
        d = get({"action": "query", "generator": "categorymembers", "gcmtitle": title, "gcmtype": kind,
                 "gcmlimit": 50 if kind == "file" else 500, **extra, **cont})
        pages += d.get("query", {}).get("pages", [])
        calls += 1
        if "continue" not in d or (max_pages and calls >= max_pages):
            return pages
        cont = d["continue"]


def crawl(root):
    seen, rows = set(), []
    if SET == "commons":
        queue, explored = deque((f"Category:{m} 2026 events", 0, None, m) for m in MONTHS), set()
    else:
        queue, explored = deque((title, 0, None, "confirm") for title in CONFIRM_ROOTS), _explored(root)[0]
    while queue:
        title, depth, parent, month = queue.popleft()
        if title in seen:
            continue
        seen.add(title)
        for p in members(title, "subcat", {"prop": "categoryinfo"}):
            sub = p["title"]
            if sub in seen or SKIP.search(sub):
                continue
            info = p.get("categoryinfo", {})
            if sub not in explored:  # an explored category may still lead to new ones below it
                rows.append({"title": sub, "files": info.get("files", 0), "subcats": info.get("subcats", 0),
                             "depth": depth + 1, "parent": title, "month": month})
            if depth + 1 < MAX_DEPTH and info.get("subcats", 0):
                queue.append((sub, depth + 1, title, month))
        print(f"{len(seen)} visited, {len(rows)} found, queue {len(queue)}", flush=True)
    unique = {r["title"]: r for r in rows}
    (out_dir(root) / "categories.json").write_text(json.dumps(list(unique.values()), ensure_ascii=False, indent=1),
                                                   encoding="utf-8")
    print(len(unique), "categories,", sum(r["files"] >= MIN_FILES for r in unique.values()), f"with {MIN_FILES}+ files")


def plain(value):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value or "")).strip()


def keep(page):
    """Licence, date and type filter of spec section 4.2. Returns the stored record or None."""
    info = (page.get("imageinfo") or [{}])[0]
    meta = {k: plain(v.get("value")) for k, v in info.get("extmetadata", {}).items() if k in META_KEYS}
    taken = meta.get("DateTimeOriginal", "")[:10]
    if info.get("mime") not in ("image/jpeg", "image/png") or not LICENCES.match(meta.get("LicenseShortName", "")):
        return None
    if not re.match(r"\d{4}-\d\d-\d\d", taken) or taken < START or info.get("timestamp", "")[:10] < START:
        return None
    if "personality" in meta.get("Restrictions", "").lower() or min(info.get("width", 0), info.get("height", 0)) < 600:
        return None
    return {"title": page["title"], "pageid": page["pageid"], "width": info["width"], "height": info["height"],
            "uploaded": info["timestamp"], "taken": taken, "thumb": info.get("thumburl"), "url": info.get("url"),
            "page": info.get("descriptionurl"), **{k: meta.get(k, "") for k in META_KEYS}}


# Spec section 4.2 leaves out photos whose main subject is an identifiable person. Categories about people
# (players, portraits, conference attendees, one band at a festival) are skipped before their files are listed.
PERSON = re.compile(r"players|managers|referees|coaches|squads|people at|people of|portrait|wikimania|wikipedia|"
                    r"wikimedia|conference|edit-a-thon|meetup|line-ups|winners|\bin (19|20)\d\d$", re.I)
MAX_PAGES = 2  # files listed per category: 100 is plenty for a sheet of 12


def _bare(title):
    return re.sub(r"\s+", " ", re.sub(r"\b(19|20)\d\d\b", "", (title or "").replace("Category:", ""))).strip().lower()


def person_category(row):
    title, parent = row["title"].replace("Category:", ""), (row["parent"] or "").replace("Category:", "")
    if PERSON.search(title) or PERSON.search(parent) or re.search(r" by [A-Z]", title):
        return True
    parts = re.split(r" [-–] ", title)
    return len(parts) == 2 and _bare(parts[1]) != "" and _bare(parts[1]) in _bare(parent)


def files(root):
    cats = json.loads((out_dir(root) / "categories.json").read_text(encoding="utf-8"))
    path = out_dir(root) / "files.jsonl"
    done = set()
    if path.exists():
        done = {json.loads(line)["category"] for line in path.read_text(encoding="utf-8").splitlines()}
    todo = [c for c in cats if c["files"] >= MIN_FILES and c["title"] not in done and not person_category(c)]
    explored = _explored(root)[1] if SET != "commons" else set()
    extra = {"prop": "imageinfo", "iiprop": "url|size|mime|timestamp|extmetadata", "iiurlwidth": 320,
             "iiextmetadatafilter": "|".join(META_KEYS)}
    with path.open("a", encoding="utf-8") as f:
        for i, cat in enumerate(todo, 1):
            pages = members(cat["title"], "file", extra, MAX_PAGES)
            kept = [r for r in map(keep, pages) if r and r["pageid"] not in explored]
            record = {"category": cat["title"], "listed": len(pages), "files": kept}
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            f.flush()
            print(f"{i}/{len(todo)} {cat['title']}: {len(kept)}/{len(pages)} kept", flush=True)


SHEET_PHOTOS = 12  # photos per event sheet, 4 x 3
THUMB = 320


def fetch(url, target):
    if target.exists():
        return True
    for _ in range(4):
        time.sleep(0.5)  # one at a time; thumbnails are small cached files
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                target.write_bytes(r.read())
            return True
        except urllib.error.HTTPError as e:
            if e.code not in (429, 503):
                return False
            time.sleep(30)
        except urllib.error.URLError:
            time.sleep(30)
    return False


def events(root):
    """Event categories with 2+ kept photos, each file in its deepest category; one sheet per event."""
    import random

    from PIL import Image, ImageDraw

    out = out_dir(root)
    depth = {c["title"]: c["depth"] for c in json.loads((out / "categories.json").read_text(encoding="utf-8"))}
    parents = {c["title"]: c["parent"] for c in json.loads((out / "categories.json").read_text(encoding="utf-8"))}
    home = {}
    for line in (out / "files.jsonl").read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        for f in record["files"]:
            best = home.get(f["pageid"])
            if best is None or depth[record["category"]] > depth[best[0]]:
                home[f["pageid"]] = (record["category"], f)
    by_event = {}
    for category, f in home.values():
        by_event.setdefault(category, []).append(f)
    rng = random.Random(20261105)
    thumbs = out / "thumbs"
    sheets = out / "sheets"
    thumbs.mkdir(exist_ok=True)
    sheets.mkdir(exist_ok=True)
    index = []
    for number, category in enumerate(sorted(c for c, fs in by_event.items() if len(fs) >= 2)):
        chosen = sorted(by_event[category], key=lambda f: f["pageid"])
        rng.shuffle(chosen)
        chosen = sorted(chosen[:SHEET_PHOTOS], key=lambda f: f["taken"])
        name = f"ev{number:03d}"
        sheet = Image.new("RGB", (4 * THUMB, 3 * (THUMB + 20)), "white")
        draw = ImageDraw.Draw(sheet)
        photos = []
        for position, f in enumerate(chosen):
            target = thumbs / f"{f['pageid']}.jpg"
            if not (f["thumb"] and fetch(f["thumb"], target)):
                continue
            left, top = (position % 4) * THUMB, (position // 4) * (THUMB + 20)
            with Image.open(target) as image:
                image = image.convert("RGB")
                image.thumbnail((THUMB - 6, THUMB - 6))
                sheet.paste(image, (left + 3, top + 20))
            draw.text((left + 4, top + 4), f"{position + 1}: {f['pageid']}", fill="black")
            photos.append({"n": position + 1, "pageid": f["pageid"], "taken": f["taken"],
                           "description": f["ImageDescription"][:300], "object": f["ObjectName"],
                           "licence": f["LicenseShortName"], "gps": bool(f["GPSLatitude"]),
                           "categories": f["Categories"][:300]})
        sheet.save(sheets / f"{name}.jpg", quality=88)
        index.append({"sheet": name, "category": category, "parent": parents.get(category),
                      "photos_in_category": len(by_event[category]), "photos": photos})
        print(name, category, len(photos), flush=True)
    (out / "events.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(index), "event sheets")


PASS1_SHEETS = 30  # event sheets per agent


def chunks(root):
    """Short metadata files for the agents, one per group of sheets."""
    out = out_dir(root)
    index = json.loads((out / "events.json").read_text(encoding="utf-8"))
    for k in range(0, len(index), PASS1_SHEETS):
        part = [{**e, "category": e["category"].replace("Category:", ""),
                 "parent": (e["parent"] or "").replace("Category:", ""),
                 "photos": [{**p, "description": p["description"][:200], "categories": p["categories"][:200]}
                            for p in e["photos"]]}
                for e in index[k:k + PASS1_SHEETS]]
        name = out / f"pass1_input_{k // PASS1_SHEETS + 1}.json"
        name.write_text(json.dumps(part, ensure_ascii=False, indent=1), encoding="utf-8")
        print(name.name, part[0]["sheet"], part[-1]["sheet"], len(part))


SEED = 20261105
DRAW = 96  # items assembled before the 1000 px check, above the 80 of spec section 4.2 so rejections are absorbed
GROUP_CAP = 28
CONFIRM_SIZES = {"draw": 120, "group_cap": 40, "final": 90}  # confirmation spec section 3: aim 90, accept 60
CONFIRM_SEED = 20261108


def _size(name):
    return CONFIRM_SIZES[name] if SET != "commons" else {"draw": DRAW, "group_cap": GROUP_CAP, "final": FINAL}[name]
SLOTS = ("event", "place", "date")
# Agents copied the metadata literally; MetLife Stadium is in East Rutherford (ev107 and ev009 are one match).
PLACE_FIX = {"Rutherford, New Jersey, United States": "East Rutherford, New Jersey, United States"}
# Sheets that are part of an event another sheet already covers (category or parent category is that event).
SAME_EVENT = {"ev107": "ev009", "ev163": "ev137", "ev187": "ev137", "ev240": "ev057", "ev242": "ev058"}
# The same for the confirmation sheets, which are numbered from ev000 again; there one town on one day is one event
# (support races of one meeting count once, home matches on other days do not), the rule used against exploration.
CONFIRM_SAME_EVENT = {"ev147": "ev146",  # one hill climb over two days
                      # second round: events of one championship, and a double-header kept as the sheet in use
                      "ev026": "ev025", "ev028": "ev025", "ev032": "ev025", "ev034": "ev025", "ev035": "ev025",
                      "ev167": "ev152", "ev168": "ev152", "ev208": "ev209"}
MONTH_NAMES = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
               "November", "December")


def day(iso):
    year, month, date = (int(x) for x in iso.split("-"))
    return f"{date} {MONTH_NAMES[month - 1]} {year}"


def caption(event, place, date):
    return f"Photograph shows {event} in {place} on {date}."


def _days_apart(a, b):
    from datetime import date

    return abs((date.fromisoformat(a) - date.fromisoformat(b)).days)


def _differs(item, donor, slot):
    if slot == "event":
        return donor["event"].lower() != item["event"].lower()
    if slot == "place":
        return donor["place"].split(",")[0].strip().lower() != item["place"].split(",")[0].strip().lower()
    return _days_apart(donor["date"], item["date"]) >= 7


def _pick_donor(item, pool, slot, used, rng):
    """Same kind first for place, date and the other photo; another kind of the same group for the event."""
    others = [d for d in pool if d["sheet"] != item["sheet"] and d["group"] == item["group"]
              and (d["event"], d["place"]) != (item["event"], item["place"])
              and _differs(item, d, slot or "place")]  # the other photo comes from another town
    same_kind = [d for d in others if d["kind"].lower() == item["kind"].lower()]
    other_kind = [d for d in others if d["kind"].lower() != item["kind"].lower()]
    ranked = (other_kind or same_kind) if slot == "event" else (same_kind or other_kind)
    if not ranked:
        return None
    low = min(used[d["sheet"]] for d in ranked)
    return rng.choice(sorted((d for d in ranked if used[d["sheet"]] == low), key=lambda d: d["sheet"]))


def _numbered(out, prefix):
    """Agent outputs in the order written (pass1_2 before pass1_10), so a later file overrides an earlier one."""
    found = [f for f in out.glob(f"{prefix}_*.json") if re.fullmatch(rf"{prefix}_\d+\.json", f.name)]
    return sorted(found, key=lambda f: int(f.stem.split("_")[-1]))


def _pool(out):
    """Usable events from the agent choices (pass1_N.json), one per real event. A later usable choice for a sheet
    replaces an earlier one; a later refusal does not remove a usable event (no new item photo found)."""
    sheets = {e["sheet"]: e for e in json.loads((out / "events.json").read_text(encoding="utf-8"))}
    latest = {}
    for f in _numbered(out, "pass1"):
        for p in json.loads(f.read_text(encoding="utf-8")):
            if p.get("use") or p["sheet"] not in latest:
                latest[p["sheet"]] = p
    picks = [p for p in latest.values() if p.get("use")]
    pool, seen = [], set()
    same_event = SAME_EVENT if out.name == "commons" else CONFIRM_SAME_EVENT
    for p in sorted(picks, key=lambda p: p["sheet"]):
        photos = {ph["n"]: ph for ph in sheets[p["sheet"]]["photos"]}
        if p["main"] not in photos or p["alt"] not in photos or p["main"] == p["alt"]:
            print("skip, photo numbers do not match the sheet:", p["sheet"])
            continue
        p = {**p, "place": PLACE_FIX.get(p["place"], p["place"])}
        key = ((p["event"].lower(), p["place"].lower()) if out.name == "commons"
               else (_town(p["place"]), photos[p["main"]]["taken"]))
        if key in seen or p["sheet"] in same_event:
            print("skip, same event as another sheet:", p["sheet"], same_event.get(p["sheet"], "same words"))
            continue
        seen.add(key)
        pool.append({**p, "main_photo": photos[p["main"]], "alt_photo": photos[p["alt"]],
                     "date": photos[p["main"]]["taken"]})
    if out.name != "commons":  # confirmation spec section 3: no event of the exploration set again
        explored = {(_town(p["place"]), p["date"]) for p in _pool(out.parent / "commons")}
        again = [p["sheet"] for p in pool if (_town(p["place"]), p["date"]) in explored]
        print("skip, same town and day as an exploration event:", again)
        pool = [p for p in pool if p["sheet"] not in again]
    return pool


def _item(item_id, p, slot, donor, other):
    values = {"event": p["event"], "place": p["place"], "date": day(p["date"])}
    false_values = {**values, slot: donor[slot] if slot != "date" else day(donor["date"])}
    return {
        "item_id": item_id, "sheet": p["sheet"], "group": p["group"], "kind": p["kind"],
        "changed": slot, "donor": donor["sheet"], "other_sheet": other["sheet"],
        "photo": f"c{p['main_photo']['pageid']}", "other_photo": f"c{other['alt_photo']['pageid']}",
        "true_caption": caption(**values), "false_caption": caption(**false_values),
        "true_value": values[slot], "false_value": false_values[slot], "taken": p["date"],
        "sources": {f"c{p['main_photo']['pageid']}": p["main_photo"]["pageid"],
                    f"c{other['alt_photo']['pageid']}": other["alt_photo"]["pageid"]},
    }


def assemble(root):
    """Agent choices to items: one changed fact per item, balanced, and an other-event photo."""
    import random
    from collections import Counter

    out = out_dir(root)
    pool = _pool(out)
    rng = random.Random(SEED if SET == "commons" else CONFIRM_SEED)
    order = sorted(pool, key=lambda p: p["sheet"])
    rng.shuffle(order)
    chosen, per_group = [], Counter()
    for p in order:
        if per_group[p["group"]] < _size("group_cap") and len(chosen) < _size("draw"):
            chosen.append(p)
            per_group[p["group"]] += 1
    chosen.sort(key=lambda p: (p["group"], order.index(p)))
    offset = rng.randrange(len(SLOTS))
    used_value, used_photo, items = Counter(), Counter(), []
    for number, p in enumerate(chosen):
        slot = SLOTS[(number + offset) % len(SLOTS)]
        donor = _pick_donor(p, pool, slot, used_value, rng)
        other = _pick_donor(p, pool, None, used_photo, rng)
        if donor is None or other is None:
            print("skip, no donor in the group:", p["sheet"], p["group"], slot)
            continue
        used_value[donor["sheet"]] += 1
        used_photo[other["sheet"]] += 1
        items.append(_item(f"c{len(items) + 1:03d}", p, slot, donor, other))
    (out / "assembled.json").write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(pool), "usable events,", len(items), "items")
    print("groups", Counter(i["group"] for i in items).most_common())
    print("changed", Counter(i["changed"] for i in items).most_common())


def large(root):
    """1000 px photos of the assembled items and their credits (spec section 4.2)."""
    from PIL import Image

    sys.path.insert(0, str(Path(root) / "src"))
    from vtrust.caption_sample import prepare_photo

    out = out_dir(root)
    items = json.loads((out / "assembled.json").read_text(encoding="utf-8"))
    meta = {}
    for line in (out / "files.jsonl").read_text(encoding="utf-8").splitlines():
        for f in json.loads(line)["files"]:
            meta[f["pageid"]] = f
    raw_dir, photo_dir = out / "large", Path(root) / "data" / "captions" / "photos"
    raw_dir.mkdir(exist_ok=True)
    photo_dir.mkdir(parents=True, exist_ok=True)
    credits = {}
    for item in items:
        for photo, pageid in item["sources"].items():
            f = meta[pageid]
            # The API returns 330 px thumbnails for iiurlwidth=320, so the width is replaced whatever it is.
            thumb = bool(f["width"] > 1280 and f["thumb"])
            url = re.sub(r"/\d+px-", "/1280px-", f["thumb"]) if thumb else f["url"]
            suffix = Path(urllib.parse.urlparse(url).path).suffix.lower() or ".jpg"
            raw = raw_dir / f"{pageid}_{'w1280' if thumb else 'orig'}{suffix}"
            if not fetch(url, raw):
                print("failed", photo, url)
                continue
            with Image.open(raw) as image:
                if max(image.size) < min(1000, max(f["width"], f["height"])):
                    raise SystemExit(f"{photo}: downloaded {image.size}, file is {f['width']} x {f['height']}")
            prepare_photo(raw, photo_dir / f"{photo}.jpg")  # always, so a corrected download replaces an old copy
            credits[photo] = {"title": f["title"], "page": f["page"], "artist": f["Artist"],
                              "licence": f["LicenseShortName"], "licence_url": f["LicenseUrl"], "taken": f["taken"]}
    (out / "credits.json").write_text(json.dumps(credits, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(credits), "photos with credits")


PASS2_ITEMS = 16  # items per agent in the 1000 px check


def _pass2_rows(root, items):
    out = out_dir(root)
    sheets = {e["sheet"]: e for e in json.loads((out / "events.json").read_text(encoding="utf-8"))}
    photo_dir = (Path(root) / "data" / "captions" / "photos").resolve()

    def about(sheet, pageid):
        photo = next(p for p in sheets[sheet]["photos"] if p["pageid"] == pageid)
        return {"category": sheets[sheet]["category"].replace("Category:", ""), "taken": photo["taken"],
                "description": photo["description"][:300]}

    rows = [{k: item[k] for k in ("item_id", "changed", "true_caption", "false_caption", "true_value",
                                  "false_value")}
            | {"photo_file": str(photo_dir / f"{item['photo']}.jpg"),
               "photo_meta": about(item["sheet"], item["sources"][item["photo"]]),
               "other_photo_file": str(photo_dir / f"{item['other_photo']}.jpg"),
               "other_photo_meta": about(item["other_sheet"], item["sources"][item["other_photo"]])}
            for item in items]
    return rows


def pass2(root):
    """Inputs for the 1000 px check: captions, the changed fact, both photos and their metadata."""
    out = out_dir(root)
    rows = _pass2_rows(root, json.loads((out / "assembled.json").read_text(encoding="utf-8")))
    for k in range(0, len(rows), PASS2_ITEMS):
        name = out / f"pass2_input_{k // PASS2_ITEMS + 1}.json"
        name.write_text(json.dumps(rows[k:k + PASS2_ITEMS], ensure_ascii=False, indent=1), encoding="utf-8")
        print(name.name, rows[k]["item_id"], rows[min(k + PASS2_ITEMS, len(rows)) - 1]["item_id"])


# Items that failed the 1000 px check in a way a new false value or a new other photo fixes (LOG 2026-11-06).
REPAIR_VALUE = ("c006", "c021", "c028", "c033", "c039", "c063", "c078")
REPAIR_OTHER = ("c006", "c015", "c024", "c026", "c028", "c030", "c064", "c068")
# The same for the confirmation items (LOG 2026-11-09).
CONFIRM_REPAIR_VALUE = ("c003", "c009", "c012", "c018", "c021", "c024")
CONFIRM_REPAIR_OTHER = ("c015", "c020", "c023", "c028", "c032", "c033", "c038", "c042", "c044", "c050", "c053",
                        "c060")
STOP_WORDS = {"a", "an", "the", "with", "in", "of", "and", "outdoor", "open", "air", "street", "live", "large",
              "night", "time", "town", "city", "traditional", "village"}


def _words(event):
    return set(re.findall(r"[a-z]+", event.lower())) - STOP_WORDS


def _town(place):
    return place.split(",")[0].strip().lower()


def repair(root):
    """New false values or other photos for the items in REPAIR_VALUE and REPAIR_OTHER, then their check inputs."""
    import random
    from collections import Counter

    out = out_dir(root)
    backup = out / "assembled_r0.json"
    if backup.exists():
        raise SystemExit(f"{backup} exists: the repair has been made")
    items = json.loads((out / "assembled.json").read_text(encoding="utf-8"))
    backup.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    pool = {p["sheet"]: p for p in _pool(out)}
    repair_value, repair_other = ((REPAIR_VALUE, REPAIR_OTHER) if SET == "commons"
                                  else (CONFIRM_REPAIR_VALUE, CONFIRM_REPAIR_OTHER))
    bad_other = {i["other_sheet"] for i in items if i["item_id"] in repair_other}
    used_value, used_photo = Counter(i["donor"] for i in items), Counter(i["other_sheet"] for i in items)
    rng = random.Random((SEED if SET == "commons" else CONFIRM_SEED) + 1)
    repaired = []
    for number, i in enumerate(items):
        if i["item_id"] not in repair_value + repair_other:
            continue
        p, slot = pool[i["sheet"]], i["changed"]
        donor, other = pool[i["donor"]], pool[i["other_sheet"]]
        if i["item_id"] in repair_value:
            candidates = [d for d in pool.values() if d["sheet"] != donor["sheet"]]
            if slot == "event":  # no shared content word, so the false event cannot be a near-synonym
                candidates = [d for d in candidates if not _words(d["event"]) & _words(p["event"])]
                if SET != "commons" and p["group"] == "music":  # every music event is a concert or festival, and
                    # the 1000 px check found a festival a fair description of a concert stage (LOG 2026-11-09)
                    candidates = [{**d, "group": p["group"]} for d in candidates if d["group"] != "music"]
            if slot == "place":
                candidates = [d for d in candidates if _town(d["place"]) != _town(donor["place"])]
            new = _pick_donor(p, candidates, slot, used_value, rng)
            if new is None:
                print("no new value for", i["item_id"])
            else:
                used_value[donor["sheet"]] -= 1
                used_value[new["sheet"]] += 1
                donor = new
        if i["item_id"] in repair_other:
            candidates = [d for d in pool.values() if d["sheet"] not in bad_other]
            new = _pick_donor(p, candidates, None, used_photo, rng)
            if new is None:
                print("no new other photo for", i["item_id"])
            else:
                used_photo[other["sheet"]] -= 1
                used_photo[new["sheet"]] += 1
                other = new
        items[number] = _item(i["item_id"], p, slot, donor, other)
        repaired.append(items[number])
        print(i["item_id"], slot, "|", items[number]["false_value"], "| other", other["sheet"])
    (out / "assembled.json").write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    name = out / f"pass2_input_{len(list(out.glob('pass2_input_*.json'))) + 1}.json"
    name.write_text(json.dumps(_pass2_rows(root, repaired), ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(repaired), "items repaired; check inputs in", name.name)


# Confirmation set, second round (RESEARCH_PLAN 2026-11-09): sheets the agents dropped for want of a town get the
# Commons categories above them, and the items whose own photo shows one person get another photo of their sheet.
PLACE_REASON = re.compile(r"town|city|place|venue|location", re.I)
CONFIRM_NEW_MAIN = ("c019", "c034", "c040", "c046", "c047", "c049", "c057")


def _ancestors(title, levels=2):
    """Visible categories above a category, `levels` steps up, nearest first."""
    found, layer = [], [title]
    for _ in range(levels):
        above = []
        for t in layer:
            d = get({"action": "query", "titles": t, "prop": "categories", "clshow": "!hidden", "cllimit": "max"})
            for page in d.get("query", {}).get("pages", []):
                for c in page.get("categories", []):
                    if c["title"] not in found and c["title"] != title:
                        found.append(c["title"])
                        above.append(c["title"])
        layer = above
    return [t.replace("Category:", "") for t in found]


def _sheet_row(e):
    photos = [{**p, "description": p["description"][:200], "categories": p["categories"][:200]} for p in e["photos"]]
    return {**e, "category": e["category"].replace("Category:", ""),
            "parent": (e["parent"] or "").replace("Category:", ""), "photos": photos}


def rescue(root):
    """Agent inputs for the second round: dropped-for-place sheets with their ancestor categories, and the sheets
    of CONFIRM_NEW_MAIN with the photo that failed."""
    out = out_dir(root)
    if SET == "commons":
        raise SystemExit("rescue is for the confirmation set")
    sheets = {e["sheet"]: e for e in json.loads((out / "events.json").read_text(encoding="utf-8"))}
    latest = {p["sheet"]: p for f in _numbered(out, "pass1") for p in json.loads(f.read_text(encoding="utf-8"))}
    dropped = sorted(k for k, p in latest.items() if not p["use"] and PLACE_REASON.search(p["reason"]))
    rows = []
    for k in dropped:
        rows.append({**_sheet_row(sheets[k]), "ancestors": _ancestors(sheets[k]["category"])})
        print(k, len(rows[-1]["ancestors"]), "ancestor categories", flush=True)
    number = len(_numbered(out, "pass1_input")) + 1
    half = -(-len(rows) // 2)
    for part in (rows[:half], rows[half:]):
        name = out / f"pass1_input_{number}.json"
        name.write_text(json.dumps(part, ensure_ascii=False, indent=1), encoding="utf-8")
        print(name.name, part[0]["sheet"], part[-1]["sheet"], len(part))
        number += 1
    items = {i["item_id"]: i for i in json.loads((out / "assembled.json").read_text(encoding="utf-8"))}
    rows = []
    for item_id in CONFIRM_NEW_MAIN:
        i = items[item_id]
        pick = latest[i["sheet"]]
        rows.append({**_sheet_row(sheets[i["sheet"]]), "failed_main": pick["main"],
                     **{k: pick[k] for k in ("alt", "group", "kind", "event", "place")}})
    name = out / f"pass1_input_{number}.json"
    name.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(name.name, "new item photos for", len(rows), "sheets")


def _event_candidates(p, pool):
    """False events with no shared content word; for music from the other groups, since every music event is a
    concert or festival and the 1000 px check found a festival a fair description of a concert stage."""
    found = [d for d in pool if not _words(d["event"]) & _words(p["event"])]
    if p["group"] == "music":
        found = [d for d in found if d["group"] != "music"]
    return found


def _any_group(p, candidates, slot, used, rng):
    """_pick_donor within the group, else from every group (a group with one event has no donor of its own)."""
    donor = _pick_donor(p, candidates, slot, used, rng)
    if donor is None:
        donor = _pick_donor(p, [{**d, "group": p["group"]} for d in candidates], slot, used, rng)
    return donor


def extend(root):
    """Second round: rebuild items whose event, photos or values changed, and add one item per new event (the
    changed fact that is rarest among the kept items so far), then their 1000 px check inputs."""
    import random
    from collections import Counter

    out = out_dir(root)
    if SET == "commons":
        raise SystemExit("extend is for the confirmation set")
    backup = out / "assembled_r1.json"
    if backup.exists():
        raise SystemExit(f"{backup} exists: the second round has been made")
    items, checks = _checked(out)
    items = list(items.values())
    backup.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    pool = {p["sheet"]: p for p in _pool(out)}
    first = json.loads((out / "assembled_r0.json").read_text(encoding="utf-8"))
    bad_other = {i["other_sheet"] for i in first if i["item_id"] in CONFIRM_REPAIR_OTHER}
    changed, added = [], []
    for number, i in enumerate(items):
        if i["sheet"] not in pool:
            raise SystemExit(f"{i['item_id']}: sheet {i['sheet']} left the pool")
        new = _item(i["item_id"], pool[i["sheet"]], i["changed"], pool[i["donor"]], pool[i["other_sheet"]])
        if new != i:
            items[number] = new
            changed.append(new)
            print("rebuilt", i["item_id"], i["changed"], "| photo", i["photo"], "->", new["photo"],
                  "| other", i["other_photo"], "->", new["other_photo"])
    rebuilt = {i["item_id"] for i in changed}
    kept = Counter(i["changed"] for i in items if checks[i["item_id"]]["keep"] or i["item_id"] in rebuilt)
    used_value, used_photo = Counter(i["donor"] for i in items), Counter(i["other_sheet"] for i in items)
    rng = random.Random(CONFIRM_SEED + 2)
    taken = {i["sheet"] for i in items}
    fresh = sorted((p for k, p in pool.items() if k not in taken), key=lambda p: p["sheet"])
    rng.shuffle(fresh)
    values = list(pool.values())
    for p in fresh:
        slot = min(SLOTS, key=lambda s: (kept[s], SLOTS.index(s)))
        donor = _any_group(p, _event_candidates(p, values) if slot == "event" else values, slot, used_value, rng)
        other = _any_group(p, [d for d in values if d["sheet"] not in bad_other], None, used_photo, rng)
        if donor is None or other is None:
            print("skip, no donor:", p["sheet"], p["group"], slot)
            continue
        used_value[donor["sheet"]] += 1
        used_photo[other["sheet"]] += 1
        kept[slot] += 1
        new = _item(f"c{len(items) + 1:03d}", p, slot, donor, other)
        items.append(new)
        added.append(new)
        print("new", new["item_id"], p["sheet"], p["group"], slot, "|", new["false_value"], "| other", other["sheet"])
    (out / "assembled.json").write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    name = out / f"pass2_input_{len(_numbered(out, 'pass2_input')) + 1}.json"
    name.write_text(json.dumps(_pass2_rows(root, changed + added), ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(changed), "rebuilt,", len(added), "new; check inputs in", name.name, "| changed facts", dict(kept))


FINAL = 80  # spec section 4.2
PAGE_STYLE = """
:root { --ink: #1f2328; --muted: #5d6670; --line: #d8dde3; --surface: #ffffff; --page: #f6f7f8; }
@media (prefers-color-scheme: dark) {
  :root { --ink: #e8eaed; --muted: #a3acb6; --line: #3a4048; --surface: #22262b; --page: #16191c; }
}
* { box-sizing: border-box; }
body { margin: 0; padding: 24px 16px 64px; background: var(--page); color: var(--ink);
       font: 15px/1.6 "Malgun Gothic", system-ui, sans-serif; }
main { max-width: 1100px; margin: 0 auto; }
p { margin: 0 0 12px; max-width: 80ch; }
.card { background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 12px;
        margin-top: 12px; }
h2 { font-size: 16px; margin: 0 0 8px; }
small, .note { font-weight: 400; color: var(--muted); }
.row { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; margin-bottom: 8px; }
figure { margin: 0; }
figure a { display: block; background: #fff; border-radius: 4px; }
img { display: block; width: 100%; height: 340px; object-fit: contain; }
figcaption { margin-top: 4px; font-size: 13px; color: var(--muted); text-align: center; }
@media (max-width: 640px) { img { height: 180px; } }
"""


def _checked(out):
    items = {i["item_id"]: i for i in json.loads((out / "assembled.json").read_text(encoding="utf-8"))}
    checks = {c["item_id"]: c for f in _numbered(out, "pass2") for c in json.loads(f.read_text(encoding="utf-8"))}
    missing = sorted(set(items) - set(checks))
    if missing:
        raise SystemExit(f"no 1000 px check for {missing}")
    return items, checks


def _strip(text):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", text or "")).strip()


def review(root):
    """One page with every item that passed the 1000 px check (spec section 4.2: the user sees every item)."""
    import html

    out = out_dir(root)
    items, checks = _checked(out)
    credits = json.loads((out / "credits.json").read_text(encoding="utf-8"))
    kept = [i for i in items.values() if checks[i["item_id"]]["keep"]]

    def figure(photo, label):
        c = credits[photo]
        credit = (f'{html.escape(_strip(c["artist"]))}, <a href="{html.escape(c["page"])}" target="_blank">'
                  f'{html.escape(c["licence"])}</a>')
        return (f'<figure><a href="../photos/{photo}.jpg" target="_blank"><img loading="lazy" '
                f'src="../photos/{photo}.jpg" alt="{label}"></a><figcaption>{label}<br><small>{credit}</small>'
                "</figcaption></figure>")

    def card(i):
        c = checks[i["item_id"]]
        seen = "사진으로 확인할 수 있음" if c["checkable"] else "사진으로 확인할 수 없음"
        return (f'<section class="card"><h2>{i["item_id"]} <small>바꾼 사실: {i["changed"]} · '
                f'{html.escape(i["kind"])}</small></h2><div class="row">{figure(i["photo"], "문항 사진")}'
                f'{figure(i["other_photo"], "다른 행사 사진")}</div>'
                f'<p>맞는 캡션: {html.escape(i["true_caption"])}<br>틀린 캡션: {html.escape(i["false_caption"])}</p>'
                f'<p class="note">{seen}: {html.escape(c.get("evidence", ""))}'
                f'{"<br>사진 속 글자 있음" if c.get("text_in_photo") else ""}'
                f'{"<br>일정이 알려진 정기 행사" if c.get("scheduled") else ""}'
                f'{"<br>메모: " + html.escape(c["note"]) if c.get("note") else ""}</p></section>')

    page = (
        '<!doctype html><html lang="ko"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>Commons 문항 확인</title><style>{PAGE_STYLE}</style></head><body><main>"
        f"<p>Commons 문항 {len(kept)}개입니다. 이 가운데 "
        f"{min(len(kept), _size('final'))}개를 씁니다. 네 가지를 봐 주세요. 맞는 캡션이 문항 사진에 "
        "맞는가, 틀린 캡션이 정말 틀렸는가(사건을 바꾼 문항은 바꾼 사건이 사진에 맞지 않아야 "
        "합니다), 두 사진의 주인공이 알아볼 수 있는 사람이 아닌가, 다른 행사 사진이 문항 사진과 "
        "다른 행사인가. 사진으로 확인할 수 있는지의 표시가 틀렸으면 그것도 알려 주세요. 사진을 "
        "누르면 모델이 볼 크기(긴 변 1000픽셀)로 열립니다. 뺄 문항은 번호(c001 등)만 알려 "
        "주세요.</p>"
        + "".join(card(i) for i in kept) + "</main></body></html>"
    )
    (out / "review.html").write_text(page, encoding="utf-8")
    print("wrote", out / "review.html", "| items", len(kept), "of", len(items))


def final(root, dropped=()):
    """items.json: the first 80 kept items in a seeded order, the changed facts in turn (spec section 4.2)."""
    import random
    from collections import Counter

    out = out_dir(root)
    items, checks = _checked(out)
    unknown = set(dropped) - set(items)
    if unknown:
        raise SystemExit(f"unknown item ids {sorted(unknown)}")
    kept = sorted((i for i in items.values() if checks[i["item_id"]]["keep"] and i["item_id"] not in dropped),
                  key=lambda i: i["item_id"])
    if SET != "commons":  # confirmation spec section 3: both photos taken before the day the config is fixed
        from datetime import date

        credits = json.loads((out / "credits.json").read_text(encoding="utf-8"))
        today = date.today().isoformat()
        late = [i["item_id"] for i in kept
                if any(credits[photo]["taken"] >= today for photo in (i["photo"], i["other_photo"]))]
        print("skip, photo taken today or later:", late)
        kept = [i for i in kept if i["item_id"] not in late]
    random.Random(SEED if SET == "commons" else CONFIRM_SEED).shuffle(kept)
    queues = {slot: [i for i in kept if i["changed"] == slot] for slot in SLOTS}
    chosen = []
    while len(chosen) < _size("final") and any(queues.values()):
        for slot in SLOTS:
            if queues[slot] and len(chosen) < _size("final"):
                chosen.append(queues[slot].pop(0))
    keys = ("item_id", "photo", "other_photo", "true_caption", "false_caption", "changed", "true_value",
            "false_value", "group", "kind", "sources")
    rows = [{k: i[k] for k in keys} | {"checkable": checks[i["item_id"]]["checkable"],
                                       "text_in_photo": checks[i["item_id"]]["text_in_photo"]}
            | ({"taken": i["taken"], "scheduled": checks[i["item_id"]].get("scheduled")} if SET != "commons" else {})
            for i in sorted(chosen, key=lambda i: i["item_id"])]
    (out / "items.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(rows), "items of", len(kept), "kept |", Counter(r["changed"] for r in rows).most_common(),
          "| checkable", Counter(r["checkable"] for r in rows).most_common())


def verite_sheets(root):
    """1000 px copies of the VERITE photos and 2 x 2 sheets for the text-in-photo labels (spec section 4.1)."""
    import csv

    from PIL import Image, ImageDraw

    sys.path.insert(0, str(Path(root) / "src"))
    from vtrust.caption_sample import prepare_photo, verite_items

    base = Path(root) / "data" / "verite" / "VERITE"
    photo_dir = Path(root) / "data" / "captions" / "photos"
    sheet_dir = Path(root) / "data" / "captions" / "verite_sheets"
    photo_dir.mkdir(parents=True, exist_ok=True)
    sheet_dir.mkdir(parents=True, exist_ok=True)
    with open(base / "VERITE.csv", encoding="utf-8") as f:
        items = verite_items(list(csv.DictReader(f)))
    photos = [(p, s) for item in items for p, s in item["sources"].items()]
    for photo, source in photos:
        if not (photo_dir / f"{photo}.jpg").exists():
            prepare_photo(base / source, photo_dir / f"{photo}.jpg")
    cell, index = 800, []
    for number in range(0, len(photos), 4):
        group = [p for p, _ in photos[number:number + 4]]
        sheet = Image.new("RGB", (2 * cell, 2 * cell), "white")
        draw = ImageDraw.Draw(sheet)
        for position, photo in enumerate(group):
            left, top = (position % 2) * cell, (position // 2) * cell
            with Image.open(photo_dir / f"{photo}.jpg") as image:
                image.thumbnail((cell - 8, cell - 30))
                sheet.paste(image, (left + 4, top + 26))
            draw.rectangle((left, top, left + 120, top + 22), fill="black")
            draw.text((left + 6, top + 5), f"{position + 1}: {photo}", fill="yellow")
        name = f"vs{number // 4:03d}"
        sheet.save(sheet_dir / f"{name}.jpg", quality=88)
        index.append({"sheet": name, "photos": group})
    (sheet_dir / "index.json").write_text(json.dumps(index, indent=1), encoding="utf-8")
    print(len(photos), "photos,", len(index), "sheets in", sheet_dir)


def main():
    global SET
    sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:]
    if "--set" in args:  # --set confirm writes to data/captions/commons_confirm/
        at = args.index("--set")
        SET = {"confirm": "commons_confirm"}[args[at + 1]]
        del args[at:at + 2]
    root, command = args[0], args[1]
    if command == "final":
        final(root, dropped=args[2:])
        return
    {"crawl": crawl, "files": files, "events": events, "chunks": chunks, "assemble": assemble, "large": large,
     "pass2": pass2, "repair": repair, "review": review, "verite-sheets": verite_sheets, "rescue": rescue,
     "extend": extend}[command](root)


if __name__ == "__main__":
    main()
