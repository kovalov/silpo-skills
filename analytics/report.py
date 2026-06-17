#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Silpo purchase analytics over data/orders.json. Pure stdlib, no network.

Usage:
  report.py spend       [--orders=PATH] [--out=PATH]   # KPIs + HTML dashboard
  report.py restock     [--orders=PATH] [--ref=YYYY-MM-DD]
  report.py promo-match [--orders=PATH] [--snap=DIR]
  report.py --selftest
"""
import json, os, sys, glob, html, datetime as dt
from collections import defaultdict, Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from categorize import categorize, CAT_LABEL  # noqa: E402

DATA = os.path.join(HERE, "..", "data")
DEF_ORDERS = os.path.join(DATA, "orders.json")
DEF_SNAP = os.path.join(DATA, "snapshots")
DEF_OUT = os.path.join(DATA, "spend.html")
STAPLE_MIN = 3
WD_UA = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"]
MONTHS_UA = {1:"січ",2:"лют",3:"бер",4:"кві",5:"тра",6:"чер",7:"лип",8:"сер",
             9:"вер",10:"жов",11:"лис",12:"гру"}


def f(v):
    try: return float(v)
    except (TypeError, ValueError): return 0.0


def _norm_order(o):
    """One raw MCP order (offline/online) → canonical shape. Tolerates aliases."""
    created = o.get("createdAt") or o.get("date")
    if not created:
        return None
    prods = o.get("products") or o.get("items") or []
    return {
        "createdAt": created,
        "sumReg": f(o.get("sumReg") or o.get("total")),
        "sumDiscount": f(o.get("sumDiscount") or o.get("discount")),
        "bonus": f(o.get("accruedBalaBonusesSum") or o.get("bonusAccrued") or o.get("bonusEarned")),
        "products": [{
            "name": (p.get("name") or "").strip(),
            "qty": f(p.get("quantity") or p.get("qty")),
            "unit": p.get("unit") or "",
            "price": f(p.get("price")),
        } for p in prods if p.get("name")],
    }


def load_orders(src=None):
    """Load orders from raw MCP pages. Dedup by (createdAt, sumReg).
    src: a file, a dir of *.json, or None → glob data/raw/*.json (fallback
    data/orders.json). Each file may be a list or {orders|items:[...]}.
    """
    if src and os.path.isfile(src):
        files = [src]
    elif src and os.path.isdir(src):
        files = sorted(glob.glob(os.path.join(src, "*.json")))
    else:
        files = sorted(glob.glob(os.path.join(DATA, "raw", "*.json")))
        if not files and os.path.exists(DEF_ORDERS):
            files = [DEF_ORDERS]
    seen = {}
    for fp in files:
        try:
            raw = json.load(open(fp, encoding="utf-8"))
        except (ValueError, OSError):
            continue
        arr = raw if isinstance(raw, list) else (raw.get("orders") or raw.get("items") or [])
        for o in arr:
            n = _norm_order(o)
            if n:
                seen[(n["createdAt"], round(n["sumReg"], 2))] = n
    return sorted(seen.values(), key=lambda o: o["createdAt"])


def parse_dt(s):
    s = s.replace("Z", "")
    try:
        return dt.datetime.fromisoformat(s)
    except ValueError:
        return dt.datetime.fromisoformat(s[:10])


# ------------------------------------------------------------- aggregation
def build(orders):
    lines = []
    for o in orders:
        ts = parse_dt(o["createdAt"])
        for p in o["products"]:
            lines.append({
                "dt": ts, "wd": ts.weekday(), "hour": ts.hour,
                "month": (ts.year, ts.month), "name": p["name"],
                "qty": p["qty"], "price": p["price"],
                "total": round(p["price"] * p["qty"], 2),
                "cat": categorize(p["name"]),
            })
    return lines


def per_product(orders):
    p_orders = defaultdict(set); p_qty = defaultdict(float)
    p_spend = defaultdict(float); p_cat = {}
    p_dates = defaultdict(set)
    for i, o in enumerate(orders):
        d = parse_dt(o["createdAt"]).date()
        for p in o["products"]:
            nm = p["name"]
            p_orders[nm].add(i); p_dates[nm].add(d)
            p_qty[nm] += p["qty"]
            p_spend[nm] += round(p["price"] * p["qty"], 2)
            p_cat[nm] = categorize(nm)
    return p_orders, p_qty, p_spend, p_cat, p_dates


def forecast(orders, ref):
    p_orders, p_qty, p_spend, p_cat, p_dates = per_product(orders)
    freq = {nm: len(s) for nm, s in p_orders.items()}
    staples = [nm for nm, n in freq.items() if n >= STAPLE_MIN]
    rows = []
    for nm in staples:
        ds = sorted(p_dates[nm])
        gaps = [(ds[i+1]-ds[i]).days for i in range(len(ds)-1)]
        gaps = [g for g in gaps if g > 0]
        if not gaps:
            continue
        mean_gap = sum(gaps) / len(gaps)
        nxt = ds[-1] + dt.timedelta(days=round(mean_gap))
        due = (nxt - ref).days
        status = "overdue" if due < 0 else ("soon" if due <= 5 else "ok")
        rows.append({"name": nm, "cat": p_cat[nm], "freq": freq[nm],
                     "gap": round(mean_gap, 1), "last": ds[-1], "next": nxt,
                     "due": due, "status": status})
    rows.sort(key=lambda r: r["due"])  # overdue first
    return rows


# ------------------------------------------------------------- modes
def cmd_restock(orders, ref):
    rows = forecast(orders, ref)
    print(f"restock forecast as of {ref}  ({len(rows)} staples, ≥{STAPLE_MIN} orders)")
    for r in rows[:40]:
        due = (f"{abs(r['due'])}d ago" if r["due"] < 0
               else "today" if r["due"] == 0 else f"in {r['due']}d")
        tag = {"overdue":"OVERDUE","soon":"SOON","ok":"ok"}[r["status"]]
        print(f"  [{tag:7}] {r['name'][:48]:48}  ~{r['gap']:.0f}d  next {r['next']} ({due})")
    return rows


def _tokens(name):
    return [t for t in name.lower().split() if len(t) >= 4][:2]


def _load_promo_names(snapdir):
    path = os.path.join(snapdir, "promotions.json")
    if not os.path.exists(path):
        return []
    raw = json.load(open(path, encoding="utf-8"))
    pl = raw if isinstance(raw, list) else \
        raw.get("items") or raw.get("promotions") or raw.get("data") or []
    out = []
    for x in pl:
        nm = (x.get("name") or x.get("title") or x.get("productName") or "") if isinstance(x, dict) else str(x)
        if nm:
            out.append((nm, x if isinstance(x, dict) else {}))
    return out


def _name_matches(name, promo_names):
    toks = _tokens(name)
    if not toks:
        return None
    for pn, _ in promo_names:
        if any(t in pn.lower() for t in toks):
            return pn
    return None


def mean_qty(orders):
    q = defaultdict(list)
    for o in orders:
        for p in o["products"]:
            if p["qty"] > 0:
                q[p["name"]].append(p["qty"])
    return {nm: sum(v) / len(v) for nm, v in q.items()}


def cmd_promo_match(orders, snapdir, ref):
    rows = forecast(orders, ref)
    due = [r for r in rows if r["status"] in ("overdue", "soon")]
    promo_names = _load_promo_names(snapdir)
    if not promo_names:
        print("no data/snapshots/promotions.json — run `silpo promos` first")
        return []
    print(f"promo-match: {len(due)} items due/soon vs {len(promo_names)} active promos")
    hits = []
    for r in due:
        m = _name_matches(r["name"], promo_names)
        if m:
            hits.append((r, m))
            print(f"  ⭐ {r['name'][:40]:40} ({r['status']}) ↔ PROMO: {m[:50]}")
    if not hits:
        print("  (no overlap between due staples and current promos)")
    return hits


def cmd_restock_cart(orders, ref, snapdir, out, limit=15):
    """Overdue+soon staples → a cart spec (JSON [{name,qty}]), promo-matched first."""
    due = [r for r in forecast(orders, ref) if r["status"] in ("overdue", "soon")]
    promo_names = _load_promo_names(snapdir)
    for r in due:
        r["promo"] = bool(_name_matches(r["name"], promo_names))
    due.sort(key=lambda r: (not r["promo"], r["due"]))  # promo first, then most overdue
    mq = mean_qty(orders)
    picked = due[:limit]
    cart = [{"name": r["name"], "qty": max(1, round(mq.get(r["name"], 1)))} for r in picked]
    print(f"restock cart: {len(cart)} items (overdue+soon, promo-first)")
    for r, c in zip(picked, cart):
        print(f"  · {c['name'][:44]:44} x{c['qty']} [{r['status']}]{' PROMO' if r['promo'] else ''}")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(cart, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("wrote", out, "→ add with:  silpo cart add --from", out)
    return cart


def cmd_coupons(snapdir, orders, ref):
    """List coupons, soonest-expiring first; flag those expiring ≤7d."""
    path = os.path.join(snapdir, "coupons.json")
    if not os.path.exists(path):
        print("no data/snapshots/coupons.json — run `silpo promos` or `silpo snapshot` first")
        return []
    raw = json.load(open(path, encoding="utf-8"))
    cl = raw if isinstance(raw, list) else raw.get("items") or raw.get("coupons") or raw.get("data") or []
    parsed = []
    for c in cl:
        if not isinstance(c, dict):
            continue
        title = c.get("name") or c.get("title") or c.get("description") or "?"
        value = c.get("value") or c.get("discount") or c.get("amount") or ""
        exp = None
        for k in ("dateTo", "endDate", "expireDate", "validTo", "expirationDate", "dateEnd", "finishDate"):
            if c.get(k):
                try:
                    exp = dt.date.fromisoformat(str(c[k])[:10]); break
                except ValueError:
                    pass
        days = (exp - ref).days if exp else None
        parsed.append({"title": title, "value": value, "days": days})
    parsed.sort(key=lambda x: (x["days"] is None, x["days"] if x["days"] is not None else 9999))
    print(f"coupons: {len(parsed)} total")
    for c in parsed:
        when = "no expiry" if c["days"] is None else (
            f"EXPIRED {abs(c['days'])}d" if c["days"] < 0 else f"{c['days']}d left")
        flag = " ⏰" if (c["days"] is not None and 0 <= c["days"] <= 7) else ""
        print(f"  [{when:12}]{flag} {str(c['value'])[:8]:8} {str(c['title'])[:50]}")
    return parsed


def cmd_price_watch(orders, min_buys=3, top=25):
    """Own paid unit-price per product, first→last % change. NOTE: this is the
    price YOU paid (promo-affected), not pure shelf inflation; no unit
    normalization (shrinkflation not detected)."""
    hist = defaultdict(list)
    for o in orders:
        d = parse_dt(o["createdAt"]).date()
        for p in o["products"]:
            if p["price"] > 0 and p["qty"] > 0:
                hist[p["name"]].append((d, p["price"]))
    rows = []
    for nm, pts in hist.items():
        pts.sort()
        if len({d for d, _ in pts}) < min_buys:
            continue
        first, last = pts[0][1], pts[-1][1]
        if first <= 0:
            continue
        rows.append({"name": nm, "first": first, "last": last,
                     "chg": 100 * (last - first) / first, "n": len(pts)})
    rows.sort(key=lambda r: -abs(r["chg"]))
    print(f"price-watch: {len(rows)} products bought ≥{min_buys}× (own paid price, first→last)")
    for r in rows[:top]:
        arrow = "▲" if r["chg"] > 0 else ("▼" if r["chg"] < 0 else "•")
        print(f"  {arrow} {r['chg']:+5.0f}%  ₴{r['first']:.0f}→₴{r['last']:.0f}  {r['name'][:46]} (×{r['n']})")
    return rows


def cmd_budget_cart(orders, budget, out, ref):
    """Greedy basket of your staples filled to a ₴budget, priced from last paid
    price. ponytail: greedy-by-frequency, not optimal knapsack — fine for a cart."""
    p_orders, _, _, p_cat, _ = per_product(orders)
    freq = {nm: len(s) for nm, s in p_orders.items()}
    mq = mean_qty(orders)
    last_price = {}
    for o in orders:  # orders sorted ascending → last write = most recent price
        for p in o["products"]:
            if p["price"] > 0:
                last_price[p["name"]] = p["price"]
    cands = [nm for nm, n in freq.items()
             if n >= STAPLE_MIN and p_cat.get(nm) != "service"]
    cands.sort(key=lambda nm: -freq[nm])
    cart, spent = [], 0.0
    for nm in cands:
        qty = max(1, round(mq.get(nm, 1)))
        cost = last_price.get(nm, 0) * qty
        if cost <= 0 or spent + cost > budget:
            continue
        cart.append({"name": nm, "qty": qty, "est": round(cost, 2)})
        spent += cost
    print(f"budget-cart: ₴{budget:.0f} target → {len(cart)} items, est ₴{spent:.0f}")
    for c in cart:
        print(f"  · {c['name'][:44]:44} x{c['qty']}  ~₴{c['est']:.0f}")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump([{"name": c["name"], "qty": c["qty"]} for c in cart],
              open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("wrote", out, "→ add with:  silpo cart add --from", out)
    return cart


def cmd_taste(orders, snapdir, top=20):
    """New items (from silpo discover) in your favorite categories you haven't bought."""
    path = os.path.join(snapdir, "discover.json")
    if not os.path.exists(path):
        print("no data/snapshots/discover.json — run `silpo discover` first")
        return []
    disc = json.load(open(path, encoding="utf-8"))
    cands = (disc.get("similar", []) + disc.get("popular", [])) if isinstance(disc, dict) else disc
    bought = {p["name"].lower() for o in orders for p in o["products"]}
    catc = Counter(categorize(p["name"]) for o in orders for p in o["products"])
    fav_cats = {k for k, _ in catc.most_common(6)}
    recs, seen = [], set()
    for c in cands:
        nm = (c.get("name") or c.get("title") or "") if isinstance(c, dict) else str(c)
        low = nm.lower()
        if not nm or low in bought or low in seen or categorize(nm) not in fav_cats:
            continue
        seen.add(low); recs.append(nm)
    print(f"taste: {len(recs)} new items in your top categories you haven't bought")
    for nm in recs[:top]:
        print(f"  ✨ [{CAT_LABEL[categorize(nm)][0]}] {nm[:55]}")
    return recs


def cmd_last_order(orders, out):
    """Newest order's items → cart spec (for `reorder`)."""
    if not orders:
        print("no orders"); return []
    o = orders[-1]
    spec = [{"name": p["name"], "qty": max(1, round(p["qty"]))} for p in o["products"] if p["name"]]
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(spec, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"last order {o['createdAt'][:10]}: {len(spec)} items → {out}")
    return spec


def money(v):
    return f"{v:,.0f}".replace(",", " ")


def cmd_spend(orders, out):
    lines = build(orders)
    n_orders = len(orders)
    total = round(sum(o["sumReg"] for o in orders), 2)
    saved = round(sum(o["sumDiscount"] for o in orders), 2)
    bonus = round(sum(o["bonus"] for o in orders), 2)
    avg = round(total / n_orders, 2) if n_orders else 0
    cat_spend = defaultdict(float); cat_items = Counter()
    for ln in lines:
        cat_spend[ln["cat"]] += ln["total"]; cat_items[ln["cat"]] += 1
    cat_sorted = sorted(cat_spend.items(), key=lambda kv: -kv[1])
    _, _, p_spend, p_cat, _ = per_product(orders)
    top = sorted(p_spend.items(), key=lambda kv: -kv[1])[:20]
    wd_cnt = Counter(parse_dt(o["createdAt"]).weekday() for o in orders)
    hr_cnt = Counter(parse_dt(o["createdAt"]).hour for o in orders)
    month_spend = defaultdict(float)
    for o in orders:
        ts = parse_dt(o["createdAt"]); month_spend[(ts.year, ts.month)] += o["sumReg"]
    span = f'{orders[0]["createdAt"][:10]} → {orders[-1]["createdAt"][:10]}' if orders else "-"

    print(f"orders={n_orders} span={span} total=₴{money(total)} avg=₴{money(avg)} "
          f"saved=₴{money(saved)} bonus=₴{money(bonus)}")
    print("top categories:", ", ".join(f"{CAT_LABEL[k][0]} ₴{money(v)}" for k, v in cat_sorted[:5]))

    esc = lambda s: html.escape(str(s))
    cmax = cat_sorted[0][1] if cat_sorted else 1
    cat_rows = "\n".join(
        f'<div class=r><div class=l>{CAT_LABEL[k][1]} {esc(CAT_LABEL[k][0])}</div>'
        f'<div class=t><div class=f style="width:{max(2,round(100*v/cmax))}%"></div></div>'
        f'<div class=v>₴{money(v)} <span>{round(100*v/total) if total else 0}% · {cat_items[k]}поз</span></div></div>'
        for k, v in cat_sorted)
    tmax = top[0][1] if top else 1
    top_rows = "\n".join(
        f'<div class=r><div class="l wide" title="{esc(nm)}">{esc(nm)}</div>'
        f'<div class=t><div class=f style="width:{max(2,round(100*v/tmax))}%"></div></div>'
        f'<div class=v>₴{money(v)}</div></div>' for nm, v in top)
    wmax = max(wd_cnt.values()) if wd_cnt else 1
    wd_rows = "\n".join(
        f'<div class=r><div class="l sm">{WD_UA[i]}</div>'
        f'<div class=t><div class=f style="width:{round(100*wd_cnt[i]/wmax) if wd_cnt[i] else 0}%"></div></div>'
        f'<div class=v>{wd_cnt[i]}</div></div>' for i in range(7))
    months = sorted(month_spend)
    mmax = max(month_spend.values()) if month_spend else 1
    m_cols = "".join(
        f'<div class=mc><div class=mv>₴{money(month_spend[m])}</div>'
        f'<div class=mw><div class=mb style="height:{max(4,round(100*month_spend[m]/mmax))}%"></div></div>'
        f'<div class=mx>{MONTHS_UA[m[1]]}</div></div>' for m in months)

    page = f"""<!doctype html><meta charset=utf-8>
<title>Аналітика покупок Silpo</title>
<style>
body{{margin:0;background:#fbf1e6;color:#2a2017;font:15px/1.5 -apple-system,Segoe UI,Roboto,Arial}}
.wrap{{max-width:900px;margin:0 auto;padding:24px 20px 80px}}
h1{{font-size:22px}}h2{{font-size:16px;border-left:4px solid #ff7a1a;padding-left:10px;margin-top:30px}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px}}
.kpi{{background:#fff;border:1px solid #f0e0cf;border-radius:12px;padding:13px 15px}}
.kpi .n{{font-size:21px;font-weight:800;color:#e76a0d}}.kpi .k{{color:#8d7c6b;font-size:12px}}
.card{{background:#fff;border:1px solid #f0e0cf;border-radius:14px;padding:16px}}
.r{{display:flex;align-items:center;gap:10px;margin:6px 0}}
.l{{width:160px;flex:none;font-size:13px;color:#5e5346;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.l.wide{{width:240px}}.l.sm{{width:32px;font-weight:700}}
.t{{flex:1;background:#f3e7d9;border-radius:6px;height:15px;overflow:hidden}}
.f{{height:100%;background:linear-gradient(90deg,#ff9a45,#ef6f12);border-radius:6px;min-width:3px}}
.v{{width:130px;flex:none;text-align:right;font-size:13px}}.v span{{color:#8d7c6b;font-size:11px}}
.mrow{{display:flex;align-items:flex-end;gap:10px;height:180px}}
.mc{{flex:1;display:flex;flex-direction:column;align-items:center;height:100%}}
.mw{{flex:1;width:100%;display:flex;align-items:flex-end}}
.mb{{width:60%;margin:0 auto;background:linear-gradient(#ff9a45,#e76a0d);border-radius:5px 5px 0 0}}
.mv{{font-size:11px}}.mx{{font-size:12px;margin-top:5px}}
</style>
<div class=wrap>
<h1>🛒 Аналітика покупок Silpo</h1>
<p style="color:#8d7c6b">{span} · {n_orders} чеків · локально, нічого не передавалось назовні</p>
<div class=kpis>
<div class=kpi><div class=n>₴{money(total)}</div><div class=k>Всього</div></div>
<div class=kpi><div class=n>₴{money(avg)}</div><div class=k>Середній чек</div></div>
<div class=kpi><div class=n>{n_orders}</div><div class=k>Походів</div></div>
<div class=kpi><div class=n>₴{money(saved)}</div><div class=k>Зекономлено</div></div>
<div class=kpi><div class=n>₴{money(bonus)}</div><div class=k>Балобонусів</div></div>
</div>
<h2>📦 На що йдуть гроші</h2><div class=card>{cat_rows}</div>
<h2>🏆 Топ-20 товарів за витратами</h2><div class=card>{top_rows}</div>
<h2>📅 За днями тижня</h2><div class=card>{wd_rows}</div>
<h2>📈 По місяцях</h2><div class=card><div class=mrow>{m_cols}</div></div>
</div>"""
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(page)
    print("wrote", out)


# ------------------------------------------------------------- selftest
def selftest():
    assert categorize("Молоко Простоквашино 2.5%") == "dairy"
    assert categorize("Хліб Бородінський") == "bakery"
    assert categorize("Форель слабосолена") == "fish"
    assert categorize("Пакет Сільпо") == "household"
    assert categorize("Авокадо Хас") == "produce"
    assert categorize("Щось невідоме XYZ") == "other"
    # forecast: 3 purchases 10 days apart -> ~10d cycle, next = last+10
    base = dt.date(2026, 1, 1)
    orders = [{"createdAt": (base + dt.timedelta(days=10*i)).isoformat() + "T10:00:00",
               "sumReg": 100, "sumDiscount": 0, "bonus": 0,
               "products": [{"name": "Молоко X", "qty": 1, "unit": "", "price": 30}]}
              for i in range(3)]
    rows = forecast(orders, dt.date(2026, 1, 25))
    assert len(rows) == 1, rows
    r = rows[0]
    assert 9 <= r["gap"] <= 11, r
    assert r["next"] == dt.date(2026, 1, 31), r
    assert r["due"] == 6, r
    # price-watch: 100 → 120 over 3 dates = +20%
    pw = [{"createdAt": (base + dt.timedelta(days=10 * i)).isoformat() + "T10:00:00",
           "sumReg": 10, "sumDiscount": 0, "bonus": 0,
           "products": [{"name": "Кава Z", "qty": 1, "unit": "", "price": [100, 110, 120][i]}]}
          for i in range(3)]
    pwr = cmd_price_watch(pw, min_buys=3)
    assert pwr and abs(pwr[0]["chg"] - 20) < 0.5, pwr
    # restock-cart includes the due staple (ref past predicted next-buy → overdue)
    rc = cmd_restock_cart(orders, dt.date(2026, 2, 1), "/nonexistent", "/tmp/_rc.json", limit=5)
    assert any(c["name"] == "Молоко X" for c in rc), rc
    # budget-cart respects the cap (milk cost 30 ≤ 35)
    bc = cmd_budget_cart(orders, 35, "/tmp/_bc.json", dt.date(2026, 1, 25))
    assert any(c["name"] == "Молоко X" for c in bc) and sum(c["est"] for c in bc) <= 35, bc
    print("selftest OK")


def main():
    args = sys.argv[1:]
    if "--selftest" in args:
        return selftest()
    mode = args[0] if args else "spend"
    flags = {a[2:].split("=")[0]: (a.split("=", 1)[1] if "=" in a else True)
             for a in args if a.startswith("--")}
    orders = load_orders(flags.get("orders"))
    if not orders:
        print("no orders — run `silpo collect` first"); return
    ref = dt.date.fromisoformat(flags["ref"]) if flags.get("ref") else parse_dt(orders[-1]["createdAt"]).date()
    if mode == "spend":
        cmd_spend(orders, flags.get("out", DEF_OUT))
    elif mode == "restock":
        cmd_restock(orders, ref)
    elif mode == "promo-match":
        cmd_promo_match(orders, flags.get("snap", DEF_SNAP), ref)
    elif mode == "restock-cart":
        cmd_restock_cart(orders, ref, flags.get("snap", DEF_SNAP),
                         flags.get("out", os.path.join(DATA, "restock-cart.json")),
                         int(flags.get("limit", 15)))
    elif mode == "coupons":
        cmd_coupons(flags.get("snap", DEF_SNAP), orders, ref)
    elif mode == "price-watch":
        cmd_price_watch(orders, int(flags.get("min", 3)), int(flags.get("top", 25)))
    elif mode == "budget-cart":
        cmd_budget_cart(orders, float(flags.get("budget", 1000)),
                        flags.get("out", os.path.join(DATA, "budget-cart.json")), ref)
    elif mode == "taste":
        cmd_taste(orders, flags.get("snap", DEF_SNAP), int(flags.get("top", 20)))
    elif mode == "last-order":
        cmd_last_order(orders, flags.get("out", os.path.join(DATA, "reorder-cart.json")))
    else:
        print(f"unknown mode: {mode}"); sys.exit(1)


if __name__ == "__main__":
    main()
