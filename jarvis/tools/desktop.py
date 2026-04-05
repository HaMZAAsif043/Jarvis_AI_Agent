import os
import time
from pathlib import Path
from typing import Optional


class Desktop:
    """PC control: mouse, keyboard, screenshots, window management."""

    def __init__(self):
        self._pyautogui = None
        self._pyautogui_imported = False

    def _get_pyautogui(self):
        if not self._pyautogui_imported:
            import pyautogui  # type: ignore
            pyautogui.FAILSAFE = True  # move mouse to corner to abort
            pyautogui.PAUSE = 0.1  # small delay between actions for stability
            self._pyautogui = pyautogui
            self._pyautogui_imported = True
        return self._pyautogui

    def mouse_click(self, x: int, y: int, clicks: int = 1, button: str = "left") -> dict:
        """Click at screen coordinates (x, y)."""
        try:
            pyautogui = self._get_pyautogui()
            pyautogui.click(x, y, clicks=clicks, button=button)
            return self._ok(f"Clicked at ({x}, {y})")
        except Exception as e:
            return self._err(str(e))

    def mouse_move(self, x: int, y: int) -> dict:
        """Move mouse to screen coordinates (x, y)."""
        try:
            pyautogui = self._get_pyautogui()
            pyautogui.moveTo(x, y, duration=0.3)
            return self._ok(f"Mouse moved to ({x}, {y})")
        except Exception as e:
            return self._err(str(e))

    def mouse_drag(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 1.0) -> dict:
        """Drag mouse from start to end coordinates (hold left button)."""
        try:
            pyautogui = self._get_pyautogui()
            pyautogui.mouseDown(start_x, start_y, button="left")
            pyautogui.moveTo(end_x, end_y, duration=duration)
            pyautogui.mouseUp(end_x, end_y, button="left")
            return self._ok(f"Dragged from ({start_x},{start_y}) to ({end_x},{end_y})")
        except Exception as e:
            return self._err(str(e))

    def drag_drop(self, file_icon_x: int, file_icon_y: int, target_x: int, target_y: int, duration: float = 1.5) -> dict:
        """Drag and drop: drag from source coordinates to target."""
        return self.mouse_drag(file_icon_x, file_icon_y, target_x, target_y, duration)

    def mouse_scroll(self, clicks: int = 10, direction: str = "down") -> dict:
        """Scroll the mouse wheel. Negative clicks = down, positive = up."""
        try:
            pyautogui = self._get_pyautogui()
            amount = -clicks if direction == "down" else clicks
            pyautogui.scroll(amount)
            return self._ok(f"Scrolled {clicks} {direction}")
        except Exception as e:
            return self._err(str(e))

    def right_click(self, x: int, y: int) -> dict:
        """Right-click at screen coordinates."""
        try:
            pyautogui = self._get_pyautogui()
            pyautogui.rightClick(x, y)
            return self._ok(f"Right-clicked at ({x}, {y})")
        except Exception as e:
            return self._err(str(e))

    def double_click(self, x: int, y: int) -> dict:
        """Double-click at screen coordinates."""
        try:
            pyautogui = self._get_pyautogui()
            pyautogui.doubleClick(x, y)
            return self._ok(f"Double-clicked at ({x}, {y})")
        except Exception as e:
            return self._err(str(e))

    def keyboard_type(self, text: str) -> dict:
        """Type text at current cursor position."""
        try:
            pyautogui = self._get_pyautogui()
            pyautogui.write(text, interval=0.05)
            return self._ok(f"Typed: {text}")
        except Exception as e:
            return self._err(str(e))

    def press_key(self, key: str) -> dict:
        """Press a single key (e.g., enter, space, escape, tab, backspace)."""
        try:
            pyautogui = self._get_pyautogui()
            pyautogui.press(key)
            return self._ok(f"Pressed key: {key}")
        except Exception as e:
            return self._err(str(e))

    def hotkey(self, keys: list[str]) -> dict:
        """Press a keyboard hotkey combination (e.g., ["ctrl", "t"])."""
        try:
            pyautogui = self._get_pyautogui()
            pyautogui.hotkey(*keys)
            return self._ok(f"Hotkey: {'+'.join(keys)}")
        except Exception as e:
            return self._err(str(e))

    def wait(self, seconds: float = 2.0) -> dict:
        """Pause execution for N seconds (useful between actions)."""
        try:
            time.sleep(seconds)
            return self._ok(f"Waited {seconds} seconds")
        except Exception as e:
            return self._err(str(e))

    def screenshot(self, output_path: str = "desktop_screenshot.png") -> dict:
        """Take a full desktop screenshot."""
        try:
            pyautogui = self._get_pyautogui()
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            pyautogui.screenshot(output_path)
            return self._ok(f"Screenshot saved to {output_path}")
        except Exception as e:
            return self._err(str(e))

    def get_screen_size(self) -> dict:
        """Get screen resolution."""
        try:
            pyautogui = self._get_pyautogui()
            w, h = pyautogui.size()
            return self._ok(output={"width": w, "height": h})
        except Exception as e:
            return self._err(str(e))

    def locate_on_screen(self, image_path: str, confidence: float = 0.8) -> dict:
        """Find an image/template on screen and return its center coordinates."""
        try:
            pyautogui = self._get_pyautogui()
            location = pyautogui.locateOnScreen(image_path, confidence=confidence)
            if location is None:
                return self._err(f"Image not found on screen: {image_path}")
            center = pyautogui.center(location)
            return self._ok(output={"x": center.x, "y": center.y, "box": location})
        except Exception as e:
            return self._err(str(e))

    def click_at_image(self, image_path: str) -> dict:
        """Find an image on screen and click its center."""
        try:
            pyautogui = self._get_pyautogui()
            location = pyautogui.locateOnScreen(image_path, confidence=0.8)
            if location is None:
                return self._err(f"Image not found on screen: {image_path}")
            center = pyautogui.center(location)
            pyautogui.click(center.x, center.y)
            return self._ok(f"Clicked image at ({center.x}, {center.y})")
        except Exception as e:
            return self._err(str(e))

    def get_cursor_position(self) -> dict:
        """Get current mouse cursor position."""
        try:
            pyautogui = self._get_pyautogui()
            x, y = pyautogui.position()
            return self._ok(output={"x": x, "y": y})
        except Exception as e:
            return self._err(str(e))

    def copy_to_clipboard(self, text: str = "") -> dict:
        """Copy text to system clipboard."""
        try:
            import pyperclip  # type: ignore
            pyperclip.copy(text)
            return self._ok(f"Copied text to clipboard ({len(text)} chars)")
        except Exception as e:
            return self._err(str(e))

    def paste_from_clipboard(self) -> dict:
        """Read text from system clipboard."""
        try:
            import pyperclip  # type: ignore
            text = pyperclip.paste()
            return self._ok(output={"text": text, "length": len(text)})
        except Exception as e:
            return self._err(str(e))

    def list_windows(self) -> dict:
        """List all open window titles."""
        try:
            import pygetwindow as gw  # type: ignore
            windows = [w.title for w in gw.getAllWindows() if w.title.strip()]
            return self._ok(output={"windows": windows, "count": len(windows)})
        except Exception as e:
            return self._err(str(e))

    def focus_window(self, title: str) -> dict:
        """Focus/activate a window by title."""
        try:
            import pygetwindow as gw  # type: ignore
            windows = gw.getWindowsWithTitle(title)
            if not windows:
                return self._err(f"No window matching '{title}' found")
            windows[0].activate()
            windows[0].maximize()
            return self._ok(output=f"Focused window: {windows[0].title}")
        except Exception as e:
            return self._err(str(e))

    def _ok(self, output=None, output_data: Optional[dict] = None) -> dict:
        if output_data is not None:
            return {"success": True, "output": output_data, "error": None}
        return {"success": True, "output": output, "error": None}

    def _err(self, message: str) -> dict:
        return {"success": False, "output": None, "error": message}
