import requests
import os
import json

WEEEK_API_KEY = os.environ.get("WEEEK_API_KEY", "")
BOT_TOKEN     = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID       = os.environ.get("TELEGRAM_CHAT_ID", "")

BASE_URL = "https://api.weeek.net/public/v1"
BOARD_ID = 2074
COLS     = [6717, 6718, 6719, 6726, 10039]

COL_NAMES = {
    6717:  "Backlog",
    6718:  "V rabote",
    6719:  "Sdelali",
    6726:  "Ne realizovannye",
    10039: "Protokolnye",
}

USERS = {
    "9baa77c9-1899-4f72-a7bc-47ca2ec08574": "Tenkov Yu.V.",
    "9baa7653-116b-4ec4-b0b3-dfc723053745": "Mikhaylovskiy V.S.",
    "9bc38a20-3cb7-4da9-8ee5-7cca50a2eb59": "Razborov I.V.",
    "9baa73fd-25e5-4f85-8255-4925809cd367": "Bukov D.S.",
    "a001c6b8-403e-499a-aa25-4c1cc2588304": "Chernenko A.G.",
    "9baa7697-375d-4f32-ab4a-b5674c5ea82d": "Ovakimyan V.V.",
    "9baa7618-eab6-4261-bd88-620bdf529f34": "Makarov Yu.V.",
    "9baa7626-54a3-4ef6-a1fb-a472eb9912c1": "Malyshev S.Yu.",
    "9e139ce8-80e4-41b7-8737-8532b113fd3a": "Kuznetsova T.M.",
    "a0ff4ca2-c0ad-4608-8d00-3c1222b8e8c9": "Ilyushkin A.D.",
    "9baa766c-7acd-4454-8721-d311d1b63b88": "Mukimov A.R.",
    "9baa7752-1a21-4cb2-b004-303b4273e643": "Sandakov E.G.",
    "9baa7386-6d00-4692-b62e-4cd568ad5dc6": "Chashnikov K.K.",
    "9f2ab407-79f0-4f54-a55c-3298f912666c": "Pekun P.S.",
    "a12abf42-e487-442e-b33d-9dd0c6e71be1": "Sakulin M.M.",
    "9baa7685-755e-458f-9f4a-4a2560ad28f9": "Nikulin S.S.",
    "9baa7684-70b6-40d5-ac30-768a41bc92ab": "Nikulin A.G.",
    "9baa7566-212a-478f-9b4a-08bf43a3d21e": "Kirsanov A.S.",
    "9baa7816-b060-451c-87c0-903a6b4c2761": "Kharnetov P.P.",
    "9d882219-0599-4e76-82d9-c33c5cf41eb2": "Bityukov V.V.",
    "9baa74eb-76fa-45f8-bb6b-76a6aef50506": "Evdokimov D.S.",
    "9baa74f1-ad5c-428a-ae72-103c8f088e9f": "Zamuraev I.V.",
    "9baa73ee-47e8-433b-94fc-1981a964dc98": "Dordzhiev D.Yu.",
    "9e2fc7a8-4192-4c23-914f-6751bd3f9224": "Shkolnikov G.N.",
}

HEADERS = {
    "Authorization": "Bearer " + WEEEK_API_KEY,
    "Content-Type": "application/json",
}


def fetch_column(col_id):
    tasks = []
    offset = 0
    while True:
        r = requests.get(
            BASE_URL + "/tm/tasks",
            headers=HEADERS,
            params={"boardId": BOARD_ID, "boardColumnId": col_id, "limit": 50, "offset": offset},
            timeout=15,
        )
        if r.status_code != 200:
            break
        batch = r.json().get("tasks", [])
        tasks.extend(batch)
        if len(batch) < 50:
            break
        offset += 50
    return tasks


def user_name(uid):
    return USERS.get(uid, uid[:8] + "...")


def main():
    from datetime import datetime, timezone, date

    print("Fetching tasks for Telegram report...")
    all_tasks = []
    for col in COLS:
        batch = fetch_column(col)
        all_tasks.extend(batch)
    print("Total tasks: " + str(len(all_tasks)))

    today = date.today().isoformat()
    total   = len(all_tasks)
    closed  = sum(1 for t in all_tasks if t.get("isCompleted"))
    opened  = total - closed
    overdue = [t for t in all_tasks if not t.get("isCompleted") and t.get("dueDate") and t["dueDate"] < today]

    # Top assignees by total tasks
    assignee_all     = {}
    assignee_overdue = {}
    for t in all_tasks:
        is_over = not t.get("isCompleted") and t.get("dueDate") and t["dueDate"] < today
        for uid in t.get("assignees", []):
            assignee_all[uid]     = assignee_all.get(uid, 0) + 1
            if is_over:
                assignee_overdue[uid] = assignee_overdue.get(uid, 0) + 1

    top3_all     = sorted(assignee_all.items(),     key=lambda x: -x[1])[:3]
    top3_overdue = sorted(assignee_overdue.items(), key=lambda x: -x[1])[:3]

    pct_closed = round(closed / total * 100) if total else 0

    # Build message
    lines = []
    lines.append("Plechi 2026 (SCRUM) - Weekly Report")
    lines.append("")
    lines.append("Date: " + datetime.now(timezone.utc).strftime("%d.%m.%Y"))
    lines.append("")
    lines.append("SUMMARY")
    lines.append("Total tasks: " + str(total))
    lines.append("Closed: " + str(closed) + " (" + str(pct_closed) + "%)")
    lines.append("In progress: " + str(opened))
    lines.append("Overdue: " + str(len(overdue)))
    lines.append("")

    if top3_all:
        lines.append("TOP WORKLOAD")
        for uid, cnt in top3_all:
            lines.append("  " + user_name(uid) + ": " + str(cnt) + " tasks")
        lines.append("")

    if top3_overdue:
        lines.append("OVERDUE BY PERSON")
        for uid, cnt in top3_overdue:
            lines.append("  " + user_name(uid) + ": " + str(cnt) + " overdue")
        lines.append("")

    if overdue:
        lines.append("OVERDUE TASKS (top 5)")
        for t in sorted(overdue, key=lambda x: x.get("dueDate",""))[:5]:
            title = t.get("title", "")[:60]
            due   = t.get("dueDate", "")
            lines.append("  [" + due + "] " + title)
        lines.append("")

    lines.append("Dashboard: https://iurii312579-hue.github.io/weeek-dashboard/")
    lines.append("Board: https://app.weeek.net/ws/544168/project/204/board/2074")

    message = "\n".join(lines)
    print("Sending to Telegram...")
    print(message)

    r = requests.post(
        "https://api.telegram.org/bot" + BOT_TOKEN + "/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "text": message,
        },
        timeout=15,
    )
    print("Telegram response: " + str(r.status_code))
    if r.status_code == 200:
        print("Message sent successfully!")
    else:
        print("Error: " + r.text)


if __name__ == "__main__":
    main()

