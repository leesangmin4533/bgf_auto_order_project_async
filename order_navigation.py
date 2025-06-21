import time
import pyautogui

from utils import load_points

ORDER_POINTS_FILE = "full_order_points.json"


def load_order_points():
    """발주 메뉴 이동을 위한 좌표 정보 로드."""
    return load_points(ORDER_POINTS_FILE)


def perform_actions(points: dict) -> None:
    """저장된 단계에 따라 마우스 동작 수행."""
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


def main():
    try:
        points = load_order_points()
        perform_actions(points)
    except Exception as e:
        print(f"❌ 오류 발생: {e}")


if __name__ == "__main__":
    main()
