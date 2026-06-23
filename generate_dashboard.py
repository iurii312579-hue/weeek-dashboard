import os
import json
import requests
from datetime import datetime, timezone

API_KEY  = os.environ["WEEEK_API_KEY"]
BASE_URL = "https://api.weeek.net/public/v1"
HEADERS  = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

TIMEOUT  = 10
PER_PAGE = 50

WS_ID      = 544168
PROJECT_ID = 204
BOARD_ID   = 2074
BOARD_URL  = f"https://app.weeek.net/ws/{WS_ID}/project/{PROJECT_ID}/board/{BOARD_ID}"

COL_NAMES = {
    6717:  "Backlog",
    6718:  "В работе",
    6719:  "Сделали (SPRY)",
    6726:  "Не реализованные",
    10039: "Протокольные",
}
CLOSED_COL_IDS = {6719, 6726, 10039}


# ── Участники ─────────────────────────────────────────────────────────────────
def load_members():
    print("Загружаю участников...", flush=True)
    members = {}
    try:
        r = requests.get(f"{BASE_URL}/ws/members", headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        for m in data.get("members", []):
            uid        = m.get("id", "")
            last_name  = (m.get("lastName")   or "").strip()
            first_name = (m.get("firstName")  or "").strip()
            middle     = (m.get("middleName") or "").strip()   # ← правильное поле
            if not uid:
                continue
            if last_name and first_name:
                name = f"{last_name} {first_name[0]}."
                if middle:
                    name += f"{middle[0]}."
            elif last_name:
                name = last_name
            elif first_name:
                name = first_name
            else:
                # Fallback на email если нет имени
                email = (m.get("email") or "").split("@")[0]
                name  = email if email else uid[:8] + "..."
            members[uid] = name
        print(f"  Загружено участников: {len(members)}", flush=True)
    except Exception as e:
        print(f"  ОШИБКА загрузки участников: {e}", flush=True)
    return members


def user_name(uid, members):
    if not uid:
        return "—"
    return members.get(uid, uid[:8] + "...")


# ── Задачи ────────────────────────────────────────────────────────────────────
def load_tasks():
    tasks = []
    for col_id, col_name in COL_NAMES.items():
        print(f"  Колонка '{col_name}'...", flush=True)
        offset = 0
        while True:
            try:
                r = requests.get(
                    f"{BASE_URL}/tm/tasks",
                    headers=HEADERS,
                    params={
                        "boardId":       BOARD_ID,  # фильтр по нашей доске
                        "boardColumnId": col_id,
                        "perPage":       PER_PAGE,
                        "offset":        offset,
                    },
                    timeout=TIMEOUT,
                )
                r.raise_for_status()
                data  = r.json()
                batch = data.get("tasks", [])

                for t in batch:
                    t["_col_id"] = col_id
                tasks.extend(batch)
                print(f"    offset={offset}: {len(batch)} задач", flush=True)

                # Останавливаемся на пустой странице или неполной
                if len(batch) < PER_PAGE:
                    break
                offset += PER_PAGE

            except requests.exceptions.Timeout:
                print(f"    ОШИБКА: таймаут на offset={offset}", flush=True)
                break
            except Exception as e:
                print(f"    ОШИБКА: {e}", flush=True)
                break

    return tasks


# ── Парсинг дат ───────────────────────────────────────────────────────────────
def parse_date(date_str):
    if not date_str:
        return None
    try:
        if len(date_str) == 10:
            return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


# ── Аналитика ─────────────────────────────────────────────────────────────────
def analyse(tasks, members):
    now = datetime.now(timezone.utc)
    closed, open_, overdue, no_due = [], [], [], []
    workload = {}
    over_by  = {}

    for t in tasks:
        col       = t.get("_col_id")
        is_closed = col in CLOSED_COL_IDS
        due_dt    = parse_date(t.get("dueDate") or t.get("dueDateTime"))
        assignees = t.get("assignees") or []
        uid       = assignees[0] if assignees else None

        if uid:
            workload[uid] = workload.get(uid, 0) + 1

        if is_closed:
            closed.append(t)
        else:
            open_.append(t)
            if due_dt and due_dt < now:
                overdue.append(t)
                if uid:
                    over_by[uid] = over_by.get(uid, 0) + 1
            elif not due_dt:
                no_due.append(t)

    workload_sorted = sorted(workload.items(), key=lambda x: x[1], reverse=True)
    over_sorted     = sorted(over_by.items(),  key=lambda x: x[1], reverse=True)

    col_stats = {}
    for t in tasks:
        col = t.get("_col_id")
        if col not in col_stats:
            col_stats[col] = {"open": 0, "closed": 0}
        key = "closed" if t["_col_id"] in CLOSED_COL_IDS else "open"
        col_stats[col][key] += 1

    return {
        "total":     len(tasks),
        "closed":    closed,
        "open":      open_,
        "overdue":   overdue,
        "no_due":    no_due,
        "workload":  workload_sorted,
        "over_by":   over_sorted,
        "col_stats": col_stats,
    }


# ── HTML ──────────────────────────────────────────────────────────────────────
def build_html(stats, members):
    now_str   = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")
    total     = stats["total"]
    n_closed  = len(stats["closed"])
    n_open    = len(stats["open"])
    n_overdue = len(stats["overdue"])
    n_no_due  = len(stats["no_due"])

    pct_closed = round(n_closed / total * 100) if total else 0
    pct_open   = round(n_open   / total * 100) if total else 0
    pct_over   = round(n_overdue / n_open * 100) if n_open else 0

    max_wl  = stats["workload"][0][1] if stats["workload"] else 1
    wl_rows = ""
    for uid, cnt in stats["workload"]:
        pct = round(cnt / max_wl * 100)
        wl_rows += f"""
        <div class="bar-row">
          <span class="bar-name">{user_name(uid, members)}</span>
          <div class="bar-track"><div class="bar-fill" style="width:{pct}%">
            <span class="bar-val">{cnt}</span>
          </div></div>
        </div>"""

    max_ov  = stats["over_by"][0][1] if stats["over_by"] else 1
    ov_rows = ""
    for uid, cnt in stats["over_by"]:
        pct = round(cnt / max_ov * 100)
        ov_rows += f"""
        <div class="bar-row">
          <span class="bar-name">{user_name(uid, members)}</span>
          <div class="bar-track"><div class="bar-fill bar-fill-red" style="width:{pct}%">
            <span class="bar-val">{cnt}</span>
          </div></div>
        </div>"""
    if not ov_rows:
        ov_rows = '<p style="color:#888;font-size:13px;margin:8px 0;">Просроченных задач нет</p>'

    overdue_rows = ""
    for t in stats["overdue"]:
        num  = t.get("number", "")
        name = (t.get("title") or "")[:80] + ("…" if len(t.get("title","")) > 80 else "")
        due  = (t.get("dueDate") or t.get("dueDateTime") or "")[:10]
        assignees = t.get("assignees") or []
        resp = user_name(assignees[0], members) if assignees else "—"
        overdue_rows += f"""
        <tr>
          <td style="color:#C0392B;font-weight:600">{num}</td>
          <td>{name}</td>
          <td style="color:#C0392B;white-space:nowrap">{due}</td>
          <td style="white-space:nowrap">{resp}</td>
        </tr>"""

    col_labels    = json.dumps([COL_NAMES.get(c, str(c)) for c in COL_NAMES])
    col_open_js   = json.dumps([stats["col_stats"].get(c, {}).get("open",   0) for c in COL_NAMES])
    col_closed_js = json.dumps([stats["col_stats"].get(c, {}).get("closed", 0) for c in COL_NAMES])
    col_total_js  = json.dumps([stats["col_stats"].get(c, {}).get("open", 0) +
                                 stats["col_stats"].get(c, {}).get("closed", 0) for c in COL_NAMES])
    donut_colors  = json.dumps(["#5B8FF9","#5AD8A6","#F6BD16","#E8684A","#9B8AFA"])

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Плечи 2026 — Дашборд</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
        background:#F5F6FA;color:#1a1a2e;padding:24px 32px}}
  h1{{font-size:22px;font-weight:700;margin-bottom:2px}}
  .sub{{font-size:12px;color:#888;margin-bottom:20px}}
  .open-btn{{float:right;margin-top:-36px;padding:7px 16px;border:1px solid #ccc;
             border-radius:6px;font-size:13px;text-decoration:none;color:#333;background:#fff}}
  .open-btn:hover{{background:#f0f0f0}}
  .metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:20px}}
  .metric{{background:#fff;border-radius:10px;padding:16px 20px;box-shadow:0 1px 4px rgba(0,0,0,.07)}}
  .metric-label{{font-size:12px;color:#888;display:flex;align-items:center;gap:6px;margin-bottom:6px}}
  .dot{{width:8px;height:8px;border-radius:50%;display:inline-block}}
  .dot-green{{background:#27AE60}}.dot-blue{{background:#2980B9}}
  .dot-red{{background:#E74C3C}}.dot-gray{{background:#BDC3C7}}
  .metric-value{{font-size:36px;font-weight:700;line-height:1}}
  .metric-sub{{font-size:12px;color:#888;margin-top:4px}}
  .card{{background:#fff;border-radius:10px;padding:20px;box-shadow:0 1px 4px rgba(0,0,0,.07)}}
  .section-title{{font-size:14px;font-weight:600;margin-bottom:14px;display:flex;align-items:center;gap:6px}}
  .red-dot{{width:8px;height:8px;border-radius:50%;background:#E74C3C;display:inline-block}}
  .grid2{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px}}
  .bar-row{{display:flex;align-items:center;gap:10px;margin-bottom:8px}}
  .bar-name{{font-size:13px;min-width:160px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
  .bar-track{{flex:1;background:#F0F2F5;border-radius:4px;height:22px;overflow:hidden}}
  .bar-fill{{background:#93C4EE;height:100%;border-radius:4px;display:flex;align-items:center;min-width:28px}}
  .bar-fill-red{{background:#F5B8B8}}
  .bar-val{{font-size:12px;font-weight:600;padding-left:6px;color:#333}}
  table{{width:100%;border-collapse:collapse;font-size:13px}}
  th{{text-align:left;color:#888;font-size:11px;font-weight:500;text-transform:uppercase;
      padding:4px 8px;border-bottom:1px solid #eee}}
  td{{padding:8px;border-bottom:1px solid #f5f5f5}}
  tr:last-child td{{border-bottom:none}}
  .chart-wrap{{position:relative;height:200px}}
</style>
</head>
<body>
<h1>Плечи 2026 (SCRUM) — Дашборд</h1>
<p class="sub">Обновлено: {now_str} | Всего задач: {total}</p>
<a class="open-btn" href="{BOARD_URL}" target="_blank">Открыть доску</a>

<div class="metrics">
  <div class="metric">
    <div class="metric-label"><span class="dot dot-green"></span>Закрыто</div>
    <div class="metric-value">{n_closed}</div>
    <div class="metric-sub">{pct_closed}% всех задач</div>
  </div>
  <div class="metric">
    <div class="metric-label"><span class="dot dot-blue"></span>В работе</div>
    <div class="metric-value">{n_open}</div>
    <div class="metric-sub">{pct_open}% всех задач</div>
  </div>
  <div class="metric">
    <div class="metric-label"><span class="dot dot-red"></span>Просрочено</div>
    <div class="metric-value">{n_overdue}</div>
    <div class="metric-sub">{pct_over}% открытых</div>
  </div>
  <div class="metric">
    <div class="metric-label"><span class="dot dot-gray"></span>Без срока</div>
    <div class="metric-value">{n_no_due}</div>
    <div class="metric-sub">нет дедлайна</div>
  </div>
</div>

<div class="grid2">
  <div class="card">
    <div class="section-title">Нагрузка по исполнителям</div>
    {wl_rows}
  </div>
  <div class="card">
    <div class="section-title"><span class="red-dot"></span>&nbsp;Просрочки по исполнителям</div>
    {ov_rows}
  </div>
</div>

<div class="card" style="margin-bottom:16px">
  <div class="section-title"><span class="red-dot"></span>&nbsp;Просроченные задачи ({n_overdue})</div>
  <table>
    <thead><tr><th>N</th><th>Задача</th><th>Срок</th><th>Ответственный</th></tr></thead>
    <tbody>{overdue_rows if overdue_rows else '<tr><td colspan="4" style="color:#888">Просроченных задач нет</td></tr>'}</tbody>
  </table>
</div>

<div class="grid2">
  <div class="card">
    <div class="section-title">Задачи по колонкам</div>
    <div class="chart-wrap"><canvas id="donutChart"></canvas></div>
  </div>
  <div class="card">
    <div class="section-title">Открытые / закрытые по колонкам</div>
    <div class="chart-wrap"><canvas id="barChart"></canvas></div>
  </div>
</div>

<script>
const labels    = {col_labels};
const colOpen   = {col_open_js};
const colClosed = {col_closed_js};
const colTotal  = {col_total_js};
const colors    = {donut_colors};

new Chart(document.getElementById('donutChart'), {{
  type: 'doughnut',
  data: {{ labels, datasets: [{{ data: colTotal, backgroundColor: colors, borderWidth:2 }}] }},
  options: {{ cutout:'65%', plugins:{{ legend:{{ position:'right',labels:{{font:{{size:11}},boxWidth:12}} }} }} }}
}});
new Chart(document.getElementById('barChart'), {{
  type: 'bar',
  data: {{
    labels,
    datasets: [
      {{ label:'Открыто',  data: colOpen,   backgroundColor:'#93C4EE' }},
      {{ label:'Закрыто',  data: colClosed, backgroundColor:'#7BD4A0' }}
    ]
  }},
  options: {{
    responsive:true, maintainAspectRatio:false,
    plugins:{{ legend:{{ position:'top',labels:{{font:{{size:11}},boxWidth:12}} }} }},
    scales:{{ x:{{ ticks:{{font:{{size:10}} }} }}, y:{{ beginAtZero:true }} }}
  }}
}});
</script>
</body>
</html>"""


def main():
    print("=== Старт генерации дашборда ===", flush=True)
    members = load_members()

    print("Загружаю задачи...", flush=True)
    tasks = load_tasks()
    print(f"Итого задач: {len(tasks)}", flush=True)

    stats = analyse(tasks, members)
    html  = build_html(stats, members)

    os.makedirs("output", exist_ok=True)
    with open("output/index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("=== Дашборд сохранён ===", flush=True)


if __name__ == "__main__":
    main()

