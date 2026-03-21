"""
动画效果模块 - 提供淡入淡出、悬停动画等视觉效果
"""
import tkinter as tk
from typing import Callable, Optional


class AnimationManager:
    """动画管理器 - 统一管理UI动画效果"""
    
    def __init__(self, widget: tk.Widget):
        self.widget = widget
        self._after_ids = []
        
    def fade_in(self, duration_ms: int = 200, on_complete: Optional[Callable] = None):
        """淡入动画"""
        self._animate_alpha(0.0, 1.0, duration_ms, on_complete)
        
    def fade_out(self, duration_ms: int = 200, on_complete: Optional[Callable] = None):
        """淡出动画"""
        self._animate_alpha(1.0, 0.0, duration_ms, on_complete)
        
    def _animate_alpha(self, start: float, end: float, duration_ms: int, on_complete: Optional[Callable] = None):
        """透明度动画核心"""
        steps = max(1, duration_ms // 16)  # 约60fps
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
            
            # 应用到widget
            try:
                if hasattr(self.widget, 'configure'):
                    # 对于支持alpha的控件
                    pass
            except:
                pass
            
            after_id = self.widget.after(16, lambda: step(count + 1))
            self._after_ids.append(after_id)
            
        step()
        
    def cancel_all(self):
        """取消所有动画"""
        for after_id in self._after_ids:
            try:
                self.widget.after_cancel(after_id)
            except:
                pass
        self._after_ids.clear()


class HoverEffect:
    """悬停效果管理器"""
    
    def __init__(self, widget: tk.Widget, 
                 normal_bg: str, hover_bg: str,
                 normal_fg: str = None, hover_fg: str = None,
                 duration_ms: int = 150):
        self.widget = widget
        self.normal_bg = normal_bg
        self.hover_bg = hover_bg
        self.normal_fg = normal_fg
        self.hover_fg = hover_fg
        self.duration_ms = duration_ms
        self._hovered = False
        
        self._bind_events()
        
    def _bind_events(self):
        """绑定悬停事件"""
        self.widget.bind('<Enter>', self._on_enter)
        self.widget.bind('<Leave>', self._on_leave)
        
    def _on_enter(self, event=None):
        """鼠标进入"""
        if not self._hovered:
            self._hovered = True
            self._animate_to(self.hover_bg, self.hover_fg)
            
    def _on_leave(self, event=None):
        """鼠标离开"""
        if self._hovered:
            self._hovered = False
            self._animate_to(self.normal_bg, self.normal_fg)
            
    def _animate_to(self, target_bg: str, target_fg: str = None):
        """动画过渡到目标颜色"""
        try:
            self.widget.configure(bg=target_bg)
            if target_fg and self.normal_fg:
                self.widget.configure(fg=target_fg)
        except:
            pass


class SmoothButton(tk.Button):
    """带平滑动画效果的按钮"""
    
    def __init__(self, master=None, **kwargs):
        # 提取动画相关参数
        self.hover_bg = kwargs.pop('hover_bg', None)
        self.hover_fg = kwargs.pop('hover_fg', None)
        self.press_bg = kwargs.pop('press_bg', None)
        self.press_fg = kwargs.pop('press_fg', None)
        self.animation_duration = kwargs.pop('animation_duration', 100)
        
        # 保存原始颜色
        self.normal_bg = kwargs.get('bg', 'SystemButtonFace')
        self.normal_fg = kwargs.get('fg', 'black')
        
        super().__init__(master, **kwargs)
        
        # 绑定事件
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
        self.bind('<ButtonPress-1>', self._on_press)
        self.bind('<ButtonRelease-1>', self._on_release)
        
        self._hovered = False
        self._pressed = False
        
    def _on_enter(self, event=None):
        """鼠标进入"""
        self._hovered = True
        if not self._pressed and self.hover_bg:
            self.configure(bg=self.hover_bg)
            if self.hover_fg:
                self.configure(fg=self.hover_fg)
                
    def _on_leave(self, event=None):
        """鼠标离开"""
        self._hovered = False
        self._pressed = False
        self.configure(bg=self.normal_bg)
        self.configure(fg=self.normal_fg)
        
    def _on_press(self, event=None):
        """鼠标按下"""
        self._pressed = True
        if self.press_bg:
            self.configure(bg=self.press_bg)
            if self.press_fg:
                self.configure(fg=self.press_fg)
                
    def _on_release(self, event=None):
        """鼠标释放"""
        self._pressed = False
        if self._hovered and self.hover_bg:
            self.configure(bg=self.hover_bg)
            if self.hover_fg:
                self.configure(fg=self.hover_fg)
        else:
            self.configure(bg=self.normal_bg)
            self.configure(fg=self.normal_fg)


class DraggableItem:
    """可拖拽项目基类"""
    
    def __init__(self, widget: tk.Widget, index: int, 
                 on_drag_start: Callable = None,
                 on_drag_move: Callable = None,
                 on_drag_end: Callable = None):
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
        """绑定拖拽事件"""
        self.widget.bind('<Button-1>', self._on_drag_start)
        self.widget.bind('<B1-Motion>', self._on_drag_move)
        self.widget.bind('<ButtonRelease-1>', self._on_drag_end)
        
    def _on_drag_start(self, event):
        """开始拖拽"""
        self._dragging = True
        self._drag_start_y = event.y_root
        self._drag_offset_y = event.y
        
        # 添加虚化效果
        self._apply_blur_effect(True)
        
        if self.on_drag_start:
            self.on_drag_start(self.index)
            
    def _on_drag_move(self, event):
        """拖拽中"""
        if not self._dragging:
            return
            
        if self.on_drag_move:
            self.on_drag_move(self.index, event.y_root - self._drag_start_y)
            
    def _on_drag_end(self, event):
        """结束拖拽"""
        if not self._dragging:
            return
            
        self._dragging = False
        
        # 移除虚化效果
        self._apply_blur_effect(False)
        
        if self.on_drag_end:
            self.on_drag_end(self.index)
            
    def _apply_blur_effect(self, blur: bool):
        """应用/移除虚化效果"""
        try:
            if blur:
                # 通过降低透明度/改变颜色模拟虚化
                self.widget.configure(bg='#E8E8E8')
                for child in self.widget.winfo_children():
                    try:
                        child.configure(fg='#999999')
                    except:
                        pass
            else:
                # 恢复正常
                pass
        except:
            pass


def create_fade_animation(widget: tk.Widget, start_alpha: float, end_alpha: float, 
                         duration_ms: int = 200):
    """创建淡入淡出动画"""
    steps = max(1, duration_ms // 16)
    
    def step(current_step=0):
        if current_step >= steps:
            return
        
        progress = current_step / steps
        # 使用缓动函数
        ease = _ease_in_out_cubic(progress)
        
        # 这里可以应用透明度变化
        # 注意：tkinter原生不支持alpha，需要通过其他方式实现
        
        widget.after(16, lambda: step(current_step + 1))
        
    step()


def _ease_in_out_cubic(t: float) -> float:
    """三次缓动函数"""
    if t < 0.5:
        return 4 * t * t * t
    else:
        return 1 - pow(-2 * t + 2, 3) / 2


def _ease_out_cubic(t: float) -> float:
    """三次缓出函数"""
    return 1 - pow(1 - t, 3)


def _ease_in_cubic(t: float) -> float:
    """三次缓入函数"""
    return t * t * t
