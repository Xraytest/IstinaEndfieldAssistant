import tkinter as tk
from typing import Callable, Optional

class AnimationManager:

    def __init__(self, widget: tk.Widget):
        self.widget = widget
        self._after_ids = []

    def fade_in(self, duration_ms: int=200, on_complete: Optional[Callable]=None):
        self._animate_alpha(0.0, 1.0, duration_ms, on_complete)

    def fade_out(self, duration_ms: int=200, on_complete: Optional[Callable]=None):
        self._animate_alpha(1.0, 0.0, duration_ms, on_complete)

    def _animate_alpha(self, start: float, end: float, duration_ms: int, on_complete: Optional[Callable]=None):
        steps = max(1, duration_ms // 16)
        step_delta = (end - start) / steps
        current = start

        def step(count=0):
            nonlocal current
            if count >= steps:
                if on_complete:
                    on_complete()
                return
            current += step_delta
            alpha = max(0.0, min(1.0, current))
            try:
                if hasattr(self.widget, 'configure'):
                    pass
            except:
                pass
            after_id = self.widget.after(16, lambda: step(count + 1))
            self._after_ids.append(after_id)
        step()

    def cancel_all(self):
        for after_id in self._after_ids:
            try:
                self.widget.after_cancel(after_id)
            except:
                pass
        self._after_ids.clear()

class HoverEffect:

    def __init__(self, widget: tk.Widget, normal_bg: str, hover_bg: str, normal_fg: str=None, hover_fg: str=None, duration_ms: int=150):
        self.widget = widget
        self.normal_bg = normal_bg
        self.hover_bg = hover_bg
        self.normal_fg = normal_fg
        self.hover_fg = hover_fg
        self.duration_ms = duration_ms
        self._hovered = False
        self._bind_events()

    def _bind_events(self):
        self.widget.bind('<Enter>', self._on_enter)
        self.widget.bind('<Leave>', self._on_leave)

    def _on_enter(self, event=None):
        if not self._hovered:
            self._hovered = True
            self._animate_to(self.hover_bg, self.hover_fg)

    def _on_leave(self, event=None):
        if self._hovered:
            self._hovered = False
            self._animate_to(self.normal_bg, self.normal_fg)

    def _animate_to(self, target_bg: str, target_fg: str=None):
        try:
            self.widget.configure(bg=target_bg)
            if target_fg and self.normal_fg:
                self.widget.configure(fg=target_fg)
        except:
            pass

class SmoothButton(tk.Button):

    def __init__(self, master=None, **kwargs):
        self.hover_bg = kwargs.pop('hover_bg', None)
        self.hover_fg = kwargs.pop('hover_fg', None)
        self.press_bg = kwargs.pop('press_bg', None)
        self.press_fg = kwargs.pop('press_fg', None)
        self.animation_duration = kwargs.pop('animation_duration', 100)
        self.normal_bg = kwargs.get('bg', 'SystemButtonFace')
        self.normal_fg = kwargs.get('fg', 'black')
        super().__init__(master, **kwargs)
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
        self.bind('<ButtonPress-1>', self._on_press)
        self.bind('<ButtonRelease-1>', self._on_release)
        self._hovered = False
        self._pressed = False

    def _on_enter(self, event=None):
        self._hovered = True
        if not self._pressed and self.hover_bg:
            self.configure(bg=self.hover_bg)
            if self.hover_fg:
                self.configure(fg=self.hover_fg)

    def _on_leave(self, event=None):
        self._hovered = False
        self._pressed = False
        self.configure(bg=self.normal_bg)
        self.configure(fg=self.normal_fg)

    def _on_press(self, event=None):
        self._pressed = True
        if self.press_bg:
            self.configure(bg=self.press_bg)
            if self.press_fg:
                self.configure(fg=self.press_fg)

    def _on_release(self, event=None):
        self._pressed = False
        if self._hovered and self.hover_bg:
            self.configure(bg=self.hover_bg)
            if self.hover_fg:
                self.configure(fg=self.hover_fg)
        else:
            self.configure(bg=self.normal_bg)
            self.configure(fg=self.normal_fg)

class DraggableItem:

    def __init__(self, widget: tk.Widget, index: int, on_drag_start: Callable=None, on_drag_move: Callable=None, on_drag_end: Callable=None):
        self.widget = widget
        self.index = index
        self.on_drag_start = on_drag_start
        self.on_drag_move = on_drag_move
        self.on_drag_end = on_drag_end
        self._dragging = False
        self._drag_start_y = 0
        self._drag_offset_y = 0
        self._bind_events()

    def _bind_events(self):
        self.widget.bind('<Button-1>', self._on_drag_start)
        self.widget.bind('<B1-Motion>', self._on_drag_move)
        self.widget.bind('<ButtonRelease-1>', self._on_drag_end)

    def _on_drag_start(self, event):
        self._dragging = True
        self._drag_start_y = event.y_root
        self._drag_offset_y = event.y
        self._apply_blur_effect(True)
        if self.on_drag_start:
            self.on_drag_start(self.index)

    def _on_drag_move(self, event):
        if not self._dragging:
            return
        if self.on_drag_move:
            self.on_drag_move(self.index, event.y_root - self._drag_start_y)

    def _on_drag_end(self, event):
        if not self._dragging:
            return
        self._dragging = False
        self._apply_blur_effect(False)
        if self.on_drag_end:
            self.on_drag_end(self.index)

    def _apply_blur_effect(self, blur: bool):
        try:
            if blur:
                self.widget.configure(bg='#E8E8E8')
                for child in self.widget.winfo_children():
                    try:
                        child.configure(fg='#999999')
                    except:
                        pass
            else:
                pass
        except:
            pass

def create_fade_animation(widget: tk.Widget, start_alpha: float, end_alpha: float, duration_ms: int=200):
    steps = max(1, duration_ms // 16)

    def step(current_step=0):
        if current_step >= steps:
            return
        progress = current_step / steps
        ease = _ease_in_out_cubic(progress)
        widget.after(16, lambda: step(current_step + 1))
    step()

def _ease_in_out_cubic(t: float) -> float:
    if t < 0.5:
        return 4 * t * t * t
    else:
        return 1 - pow(-2 * t + 2, 3) / 2

def _ease_out_cubic(t: float) -> float:
    return 1 - pow(1 - t, 3)

def _ease_in_cubic(t: float) -> float:
    return t * t * t