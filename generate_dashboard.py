# -*- coding: utf-8 -*-
import requests
import json
import os
from datetime import datetime, timezone

API_KEY  = os.environ.get("WEEEK_API_KEY", "")
BASE_URL = "https://api.weeek.net/public/v1"
BOARD_ID = 2074
COLS     = [6717, 6718, 6719, 6726, 10039]

COL_NAMES = {
    6717:  "Backlog",
    6718:  "В работе",
    6719:  "Сделали (SPRY)",
    6726:  "Не реализованные",
    10039: "Протокольные",
}

USERS = {
    "9baa77c9-1899-4f72-a7bc-47ca2ec08574": "Теньков Ю.В.",
    "9baa7653-116b-4ec4-b0b3-dfc723053745": "Михайловский В.С.",
    "9bc38a20-3cb7-4da9-8ee5-7cca50a2eb59": "Разборов И.В.",
    "9baa73fd-25e5-4f85-8255-4925809cd367": "Буков Д.С.",
    "a001c6b8-403e-499a-aa25-4c1cc2588304": "Черненко А.Г.",
    "9baa7697-375d-4f32-ab4a-b5674c5ea82d": "Овакимян В.В.",
    "9baa7618-eab6-4261-bd88-620bdf529f34": "Макаров Ю.В.",
    "9baa7626-54a3-4ef6-a1fb-a472eb9912c1": "Малышев С.Ю.",
    "9e139ce8-80e4-41b7-8737-8532b113fd3a": "Кузнецова Т.М.",
    "a0ff4ca2-c0ad-4608-8d00-3c1222b8e8c9": "Илюшкин А.Д.",
    "9baa766c-7acd-4454-8721-d311d1b63b88": "Мукимов А.Р.",
    "9baa7752-1a21-4cb2-b004-303b4273e643": "Сандаков Э.Г.",
    "9baa7386-6d00-4692-b62e-4cd568ad5dc6": "Чашников К.К.",
    "9f2ab407-79f0-4f54-a55c-3298f912666c": "Пекун П.С.",
    "a12abf42-e487-442e-b33d-9dd0c6e71be1": "Сакулин М.М.",
    "9baa7685-755e-458f-9f4a-4a2560ad28f9": "Никулин С.С.",
    "9baa7684-70b6-40d5-ac30-768a41bc92ab": "Никулин А.Г.",
    "9baa7566-212a-478f-9b4a-08bf43a3d21e": "Кирсанов А.С.",
    "9baa7816-b060-451c-87c0-903a6b4c2761": "Харнетов П.П.",
    "9d882219-0599-4e76-82d9-c33c5cf41eb2": "Битюков В.В.",
    "9baa74eb-76fa-45f8-bb6b-76a6aef50506": "Евдокимов Д.С.",
    "9baa74f1-ad5c-428a-ae72-103c8f088e9f": "Замураев И.В.",
    "9baa73ee-47e8-433b-94fc-1981a964dc98": "Дорджиев Д.Ю.",
    "9e2fc7a8-4192-4c23-914f-6751bd3f9224": "Школьников Г.Н.",
    "9c864865-5ab8-4b96-85be-71324582f313": "Иванов",
    "9ca3079d-dde1-4280-913d-c6209802ba5e": "Страшкова Н.В.",
    "9baa774f-992a-4dcf-8566-d3efcb7bd097": "Загривко Д.С.",
}

HEADERS = {
    "Authorization": "Bearer " + API_KEY,
    "Content-Type": "application/json",
}


def fetch_column(col_id):
    задач = []
    offset = 0
    while True:
        r = requests.get(
            BASE_URL + "/tm/задач",
            headers=HEADERS,
            params={"boardId": BOARD_ID, "boardColumnId": col_id, "limit": 50, "offset": offset},
            timeout=15,
        )
        if r.status_code != 200:
            break
        batch = r.json().get("задач", [])
        задач.extend(batch)
        if len(batch) < 50:
            break
        offset += 50
    return задач


# Кэш участников — обновляется из API при первом запросе
_members_cache = {}

def load_members():
    """Загружает список участников воркспейса из Weeek API"""
    global _members_cache
    if _members_cache:
        return
    try:
        r = requests.get(
            BASE_URL + "/ws/members",
            headers=HEADERS,
            timeout=10,
        )
        if r.status_code == 200:
            members = r.json().get("members", [])
            for m in members:
                uid = m.get("id", "")
                first = m.get("firstName", "")
                last  = m.get("lastName", "")
                name  = (last + " " + first[0] + ".").strip() if first else last
                if uid and name:
                    _members_cache[uid] = name
    except Exception:
        pass

def user_name(uid):
    """Возвращает имя пользователя: сначала из API, затем из статического словаря"""
    load_members()
    if uid in _members_cache:
        return _members_cache[uid]
    return USERS.get(uid, uid[:8] + "...")


def bar_rows_html(data, max_val, fill_color, text_color):
    rows = []
    for uid, cnt in data:
        w = round(cnt / max_val * 100)
        name = user_name(uid)
        rows.append(
            '<div style="display:flex;align-items:center;gap:8px;margin-bottom:7px;">'
            '<span style="width:160px;font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="' + name + '">' + name + '</span>'
            '<div style="flex:1;background:#f0f0ee;border-radius:3px;height:18px;">'
            '<div style="width:' + str(w) + '%;background:' + fill_color + ';border-radius:3px;height:100%;display:flex;align-items:center;padding-left:6px;min-width:22px;">'
            '<span style="font-size:11px;font-weight:600;color:' + text_color + ';">' + str(cnt) + '</span>'
            '</div></div></div>'
        )
    return "\n".join(rows)


def overdue_rows_html(overdue_sorted):
    rows = []
    for t in overdue_sorted:
        names = ", ".join(user_name(u) for u in t.get("assignees", [])) or "-"
        title_full = t.get("title", "")
        if "." in title_full[:6]:
            num = title_full.split(".")[0]
            title = title_full[len(num)+1:].strip()
        else:
            num = "-"
            title = title_full
        if len(title) > 90:
            title = title[:90] + "..."
        due = t.get("dueDate", "")
        rows.append(
            "<tr>"
            '<td style="padding:7px 8px;font-weight:600;color:#A32D2D;white-space:nowrap;">' + num + "</td>"
            '<td style="padding:7px 8px;font-size:13px;">' + title + "</td>"
            '<td style="padding:7px 8px;white-space:nowrap;color:#A32D2D;font-size:12px;">' + due + "</td>"
            '<td style="padding:7px 8px;font-size:12px;color:#444;">' + names + "</td>"
            "</tr>"
        )
    return "\n".join(rows)


def build_html(задач, generated_at):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    total   = len(задач)
    closed  = [t for t in задач if t.get("isCompleted")]
    opened  = [t for t in задач if not t.get("isCompleted")]
    overdue = [t for t in opened if t.get("dueDate") and t["dueDate"] < today]
    no_due  = [t for t in opened if not t.get("dueDate")]

    assignee_all     = {}
    assignee_overdue = {}
    for t in задач:
        is_over = not t.get("isCompleted") and t.get("dueDate") and t["dueDate"] < today
        for uid in t.get("assignees", []):
            assignee_all[uid]     = assignee_all.get(uid, 0) + 1
            if is_over:
                assignee_overdue[uid] = assignee_overdue.get(uid, 0) + 1

    top_all     = sorted(assignee_all.items(),     key=lambda x: -x[1])[:10]
    top_overdue = sorted(assignee_overdue.items(), key=lambda x: -x[1])[:8]
    max_all = top_all[0][1]     if top_all     else 1
    max_ovd = top_overdue[0][1] if top_overdue else 1

    col_total  = {c: 0 for c in COLS}
    col_open   = {c: 0 for c in COLS}
    col_closed = {c: 0 for c in COLS}
    for t in задач:
        c = t.get("boardColumnId")
        if c in col_total:
            col_total[c] += 1
            if t.get("isCompleted"):
                col_closed[c] += 1
            else:
                col_open[c] += 1

    col_labels = json.dumps([COL_NAMES[c] for c in COLS])
    col_data   = json.dumps([col_total[c]  for c in COLS])
    col_open_d = json.dumps([col_open[c]   for c in COLS])
    col_clos_d = json.dumps([col_closed[c] for c in COLS])

    pct_closed  = round(len(closed) / total * 100) if total else 0
    pct_open    = 100 - pct_closed
    pct_overdue = round(len(overdue) / len(opened) * 100) if opened else 0

    overdue_sorted = sorted(overdue, key=lambda t: t.get("dueDate", ""))

    bars_all     = bar_rows_html(top_all,     max_all, "#B5D4F4", "#0C447C")
    bars_overdue = bar_rows_html(top_overdue, max_ovd, "#F7C1C1", "#A32D2D") if top_overdue else "<p style='font-size:13px;color:#aaa;'>No overdue задач</p>"
    overdue_table = ""
    if overdue:
        overdue_table = (
            "<table>"
            "<thead><tr>"
            "<th>N</th><th>Task</th><th>Due</th><th>Responsible</th>"
            "</tr></thead>"
            "<tbody>" + overdue_rows_html(overdue_sorted) + "</tbody>"
            "</table>"
        )
    else:
        overdue_table = "<p style='font-size:13px;color:#aaa;'>No overdue задач</p>"

    html = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Plechi 2026 Dashboard</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f5f4f0;color:#1a1a18;line-height:1.5;}
.container{max-width:1100px;margin:0 auto;padding:24px 16px;}
.header{display:flex;align-items:center;justify-content:space-between;margin-bottom:24px;flex-wrap:wrap;gap:12px;}
.header-title{font-size:20px;font-weight:600;}
.header-sub{font-size:12px;color:#888;margin-top:3px;}
.header-link{font-size:13px;color:#185FA5;text-decoration:none;border:1px solid #B5D4F4;padding:6px 14px;border-radius:6px;}
.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px;}
.metric{background:#fff;border-radius:10px;padding:14px 16px;border:1px solid #e8e6e0;}
.metric-label{font-size:12px;color:#888;margin-bottom:4px;}
.metric-value{font-size:30px;font-weight:600;}
.metric-sub{font-size:11px;color:#aaa;margin-top:3px;}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px;}
.card{background:#fff;border-radius:10px;padding:16px 18px;border:1px solid #e8e6e0;margin-bottom:16px;}
.card-title{font-size:14px;font-weight:600;margin-bottom:14px;}
table{width:100%;border-collapse:collapse;}
th{font-size:11px;font-weight:600;color:#888;text-align:left;padding:6px 8px;border-bottom:2px solid #e8e6e0;text-transform:uppercase;letter-spacing:.04em;}
tr:hover td{background:#fafaf8;}
.dot{width:8px;height:8px;border-radius:50%;display:inline-block;margin-right:5px;vertical-align:middle;}
@media(max-width:640px){.metrics{grid-template-columns:1fr 1fr;}.grid2{grid-template-columns:1fr;}}
</style>
</head>
<body>
<div class="container">
<div class="header">
  <div>
    <div class="header-title">Plechi 2026 (SCRUM) Dashboard</div>
    <div class="header-sub">Обновлено: GENERATED_AT | Всего задач: TOTAL_COUNT</div>
  </div>
  <a class="header-link" href="https://app.weeek.net/ws/544168/project/204/board/2074" target="_blank">Открыть доску</a>
</div>
<div class="metrics">
  <div class="metric">
    <div class="metric-label"><span class="dot" style="background:#639922;"></span>Закрыто</div>
    <div class="metric-value" style="color:#3B6D11;">CLOSED_COUNT</div>
    <div class="metric-sub">PCT_CLOSED% всех задач</div>
  </div>
  <div class="metric">
    <div class="metric-label"><span class="dot" style="background:#378ADD;"></span>В работе / открыто</div>
    <div class="metric-value" style="color:#185FA5;">OPEN_COUNT</div>
    <div class="metric-sub">PCT_OPEN% всех задач</div>
  </div>
  <div class="metric">
    <div class="metric-label"><span class="dot" style="background:#E24B4A;"></span>Просрочено</div>
    <div class="metric-value" style="color:#A32D2D;">OVERDUE_COUNT</div>
    <div class="metric-sub">PCT_OVERDUE% открытых</div>
  </div>
  <div class="metric">
    <div class="metric-label"><span class="dot" style="background:#888;"></span>Без срока</div>
    <div class="metric-value" style="color:#5F5E5A;">NODUE_COUNT</div>
    <div class="metric-sub">нет дедлайна</div>
  </div>
</div>
<div class="grid2">
  <div class="card">
    <div class="card-title">Нагрузка по исполнителям</div>
    BARS_ALL
  </div>
  <div class="card">
    <div class="card-title"><span class="dot" style="background:#E24B4A;"></span>Просрочки по исполнителям</div>
    BARS_OVERDUE
  </div>
</div>
<div class="card">
  <div class="card-title"><span class="dot" style="background:#E24B4A;"></span>Просроченные задачи (OVERDUE_COUNT)</div>
  OVERDUE_TABLE
</div>
<div class="grid2">
  <div class="card">
    <div class="card-title">Задачи по колонкам</div>
    <div style="position:relative;height:200px;"><canvas id="colChart"></canvas></div>
  </div>
  <div class="card">
    <div class="card-title">Open / Закрыто by column</div>
    <div style="position:relative;height:200px;"><canvas id="statusChart"></canvas></div>
  </div>
</div>
</div>
<script>
var colLabels = COL_LABELS;
var tc = '#888780', gc = 'rgba(0,0,0,0.05)';
new Chart(document.getElementById('colChart'), {
  type:'doughnut',
  data:{labels:colLabels,datasets:[{data:COL_DATA,
    backgroundColor:['#B5D4F4','#9FE1CB','#C0DD97','#FAC775','#F5C4B3'],
    borderColor:['#378ADD','#1D9E75','#639922','#BA7517','#D85A30'],borderWidth:1.5}]},
  options:{responsive:true,maintainAspectRatio:false,
    plugins:{legend:{display:true,position:'right',labels:{color:tc,font:{size:11},boxWidth:10,padding:6}}}}
});
new Chart(document.getElementById('statusChart'), {
  type:'bar',
  data:{labels:colLabels,datasets:[
    {label:'Открыто',data:COL_OPEN,backgroundColor:'#85B7EB',borderRadius:3},
    {label:'Закрыто',data:COL_CLOSED,backgroundColor:'#97C459',borderRadius:3}
  ]},
  options:{responsive:true,maintainAspectRatio:false,
    plugins:{legend:{display:true,position:'top',labels:{color:tc,font:{size:11},boxWidth:10,padding:8}}},
    scales:{
      x:{stacked:true,ticks:{color:tc,font:{size:10},maxRotation:20},grid:{display:false}},
      y:{stacked:true,ticks:{color:tc,font:{size:11},stepSize:5},grid:{color:gc}}
    }
  }
});
</script>
</body>
</html>"""

    html = html.replace("GENERATED_AT", generated_at)
    html = html.replace("TOTAL_COUNT", str(total))
    html = html.replace("CLOSED_COUNT", str(len(closed)))
    html = html.replace("PCT_CLOSED", str(pct_closed))
    html = html.replace("OPEN_COUNT", str(len(opened)))
    html = html.replace("PCT_OPEN", str(pct_open))
    html = html.replace("OVERDUE_COUNT", str(len(overdue)))
    html = html.replace("PCT_OVERDUE", str(pct_overdue))
    html = html.replace("NODUE_COUNT", str(len(no_due)))
    html = html.replace("BARS_ALL", bars_all)
    html = html.replace("BARS_OVERDUE", bars_overdue)
    html = html.replace("OVERDUE_TABLE", overdue_table)
    html = html.replace("COL_LABELS", col_labels)
    html = html.replace("COL_DATA", col_data)
    html = html.replace("COL_OPEN", col_open_d)
    html = html.replace("COL_CLOSED", col_clos_d)

    return html


def main():
    print("Загружаю задачи из Weeek...")
    all_задач = []
    for col in COLS:
        batch = fetch_column(col)
        print("  Column " + COL_NAMES[col] + ": " + str(len(batch)) + " задач")
        all_задач.extend(batch)
    print("Всего: " + str(len(all_задач)) + " задач")

    generated_at = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")
    html = build_html(all_задач, generated_at)

    os.makedirs("output", exist_ok=True)
    with open("output/index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Дашборд сохранён в output/index.html")


if __name__ == "__main__":
    main()

