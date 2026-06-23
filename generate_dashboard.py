import os
import json
import requests
from datetime import datetime, timezone

API_KEY  = os.environ["WEEEK_API_KEY"]
BASE_URL = "https://api.weeek.net/public/v1"
HEADERS  = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

TIMEOUT    = 10
PER_PAGE   = 50

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


# ── ДИАГНОСТИКА ───────────────────────────────────────────────────────────────
def diagnose():
    print("\n========== ДИАГНОСТИКА ==========", flush=True)

    # 1. Участники
    print("\n--- /ws/members ---", flush=True)
    r = requests.get(f"{BASE_URL}/ws/members", headers=HEADERS, timeout=TIMEOUT)
    print(f"Status: {r.status_code}", flush=True)
    data = r.json()
    print(f"Ключи: {list(data.keys())}", flush=True)
    members_raw = data.get("members") or data.get("data") or []
    print(f"Кол-во участников: {len(members_raw)}", flush=True)
    if members_raw:
        print(f"Пример участника (ключи): {list(members_raw[0].keys())}", flush=True)
        print(f"Пример участника (данные): {members_raw[0]}", flush=True)

    # 2. Задачи без фильтра boardId — смотрим сколько их
    print("\n--- /tm/tasks без фильтров (первые 5) ---", flush=True)
    r2 = requests.get(f"{BASE_URL}/tm/tasks",
                      headers=HEADERS,
                      params={"perPage": 5, "offset": 0},
                      timeout=TIMEOUT)
    d2 = r2.json()
    print(f"Ключи ответа: {list(d2.keys())}", flush=True)
    print(f"hasMore: {d2.get('hasMore')}", flush=True)
    tasks_sample = d2.get("tasks", [])
    if tasks_sample:
        print(f"Ключи задачи: {list(tasks_sample[0].keys())}", flush=True)
        t = tasks_sample[0]
        print(f"boardId в задаче: {t.get('boardId')}, boardColumnId: {t.get('boardColumnId')}, projectId: {t.get('projectId')}", flush=True)

    # 3. Задачи с фильтром boardId
    print(f"\n--- /tm/tasks с boardId={BOARD_ID} (первые 5) ---", flush=True)
    r3 = requests.get(f"{BASE_URL}/tm/tasks",
                      headers=HEADERS,
                      params={"boardId": BOARD_ID, "perPage": 5, "offset": 0},
                      timeout=TIMEOUT)
    d3 = r3.json()
    tasks3 = d3.get("tasks", [])
    print(f"Задач получено: {len(tasks3)}, hasMore: {d3.get('hasMore')}", flush=True)
    if tasks3:
        t = tasks3[0]
        print(f"boardId в задаче: {t.get('boardId')}, boardColumnId: {t.get('boardColumnId')}", flush=True)

    # 4. Задачи с boardColumnId одной колонки
    print(f"\n--- /tm/tasks с boardColumnId=6719 (первые 5) ---", flush=True)
    r4 = requests.get(f"{BASE_URL}/tm/tasks",
                      headers=HEADERS,
                      params={"boardColumnId": 6719, "perPage": 5, "offset": 0},
                      timeout=TIMEOUT)
    d4 = r4.json()
    tasks4 = d4.get("tasks", [])
    print(f"Задач получено: {len(tasks4)}, hasMore: {d4.get('hasMore')}", flush=True)
    if tasks4:
        t = tasks4[0]
        print(f"boardId в задаче: {t.get('boardId')}, projectId: {t.get('projectId')}", flush=True)

    # 5. Задачи с boardId + boardColumnId вместе
    print(f"\n--- /tm/tasks с boardId={BOARD_ID} + boardColumnId=6719 ---", flush=True)
    r5 = requests.get(f"{BASE_URL}/tm/tasks",
                      headers=HEADERS,
                      params={"boardId": BOARD_ID, "boardColumnId": 6719, "perPage": 5, "offset": 0},
                      timeout=TIMEOUT)
    d5 = r5.json()
    tasks5 = d5.get("tasks", [])
    print(f"Задач получено: {len(tasks5)}, hasMore: {d5.get('hasMore')}", flush=True)

    print("\n========== КОНЕЦ ДИАГНОСТИКИ ==========\n", flush=True)


def main():
    print("=== РЕЖИМ ДИАГНОСТИКИ ===", flush=True)
    diagnose()
    print("Диагностика завершена. Дашборд не генерируется.", flush=True)


if __name__ == "__main__":
    main()

