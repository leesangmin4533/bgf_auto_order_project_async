import json
import time
import pyautogui
import os

ORDER_POINTS_FILE = os.path.join(os.path.dirname(__file__), "full_order_points.json")


def load_order_points():
    with open(ORDER_POINTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def perform_actions(points):
    print("=== 발주 메뉴 자동 진입 시작 ===")
    for key, step in points.items():
        pos = step["position"]
        desc = step.get("description", key)
        print(f"🔴 이동 예정 → {desc}: {pos}")
        pyautogui.moveTo(pos[0], pos[1], duration=0.5)
        time.sleep(0.3)
        if step["action"] == "click":
            pyautogui.click()
            print(f"🖱️ 클릭 완료 → {desc}")
        elif step["action"] == "double_click":
            pyautogui.doubleClick()
            print(f"🖱️ 더블클릭 완료 → {desc}")
        time.sleep(0.5)


if __name__ == "__main__":
    try:
        points = load_order_points()
        perform_actions(points)
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
