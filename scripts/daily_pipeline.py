#!/usr/bin/env python3
"""
IstinaEndfieldAssistant — 每日签到 & 任务分析流水线 v2

核心改进:
  1. 自适应页面检测 — 每个步骤先 VLM 分析当前画面，再决策下一步
  2. 模式感知 — 区分探索模式/基建模式，自动切换
  3. 导航决策树 — VLM 找不到目标时，智能尝试多种路径
  4. 完整事件覆盖 — 签到 + 每周任务 + 活动奖励
  5. 所有参数 PipelineConfig 集中可调

用法:
  python scripts/daily_pipeline.py
  python scripts/daily_pipeline.py --model vision
  python scripts/daily_pipeline.py --dry-run
"""

import subprocess, time, sys, io, os, base64, json, re, argparse
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum

from _path_setup import PROJECT_ROOT, SRC_DIR, MODULE_DIR, ensure_path
ensure_path()

PROJECT_ROOT = str(PROJECT_ROOT)
SRC_DIR = str(SRC_DIR)

os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 命令行参数
parser = argparse.ArgumentParser()
parser.add_argument("--device", help="设备地址, 如 localhost:16512")
parser.add_argument("--adb", help="ADB 路径")
args, _ = parser.parse_known_args()

# 从配置读取默认值
config = {}
try:
    with open(os.path.join(PROJECT_ROOT, "config", "client_config.json")) as f:
        config = json.load(f)
except Exception:
    pass
device_config = config.get("device", {})

adb_path = args.adb or device_config.get("adb_path", os.path.join(PROJECT_ROOT, "3rd-party", "adb", "adb.exe"))
device_addr = args.device or device_config.get("address", "localhost:16512")

ADB = [adb_path, "-s", device_addr]
SCREENSHOT_PATH = os.path.join(PROJECT_ROOT, "cache", "screenshot_current.png")
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "cache", "daily_analysis.json")


@dataclass
class PipelineConfig:
    model_tag: str = "exploration_deep"
    vlm_timeout: int = 180
    post_tap_delay: float = 8.0
    post_claim_delay: float = 5.0
    dry_run: bool = False
    max_retries: int = 2


class PageType(Enum):
    UNKNOWN = "unknown"
    EXPLORATION = "exploration"      # 野外探索主界面
    BASE = "base"                    # 基建/工业界面
    EVENT_CENTER = "event_center"    # 活动中心
    SIGN_IN = "sign_in"              # 签到页面
    WEEKLY_TASKS = "weekly_tasks"    # 每周事务
    DIALOG = "dialog"               # 弹窗/对话框
    LOADING = "loading"              # 加载中


# ── 工具函数 ──────────────────────────────────────────────────
def tap(x: int, y: int):
    subprocess.run(ADB + ["shell", "input", "tap", str(x), str(y)], capture_output=True)

def swipe(x1, y1, x2, y2, duration=200):
    subprocess.run(ADB + ["shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration)], capture_output=True)

def screenshot() -> Optional[bytes]:
    subprocess.run(ADB + ["shell", "screencap", "-p", "/sdcard/s.png"], capture_output=True)
    r = subprocess.run(ADB + ["pull", "/sdcard/s.png", SCREENSHOT_PATH], capture_output=True)
    if r.returncode != 0:
        return None
    with open(SCREENSHOT_PATH, "rb") as f:
        return f.read()

def vlm(cfg: PipelineConfig, instruction: str, sp: str = "") -> Optional[Dict]:
    raw = screenshot()
    if not raw:
        return None
    from core.communication.communicator import ClientCommunicator
    # 从配置读取密码和密钥，避免硬编码
    server_config = config.get("server", {})
    server_password = server_config.get("password", "default_password")
    api_key = config.get("api_key", "aa7d3551ab7fdb975c2eed5251df53ade38aa12cd6161475221d774f27026763")
    comm = ClientCommunicator(host="127.0.0.1", port=9999, password=server_password, timeout=cfg.vlm_timeout)
    r = comm.send_request("login", {"user_id": "explorer", "key": api_key})
    sid = (r or {}).get("session_id", "")
    comm.set_logged_in(True)
    b64 = base64.b64encode(raw).decode("utf-8")
    resp = comm.send_request("agent_chat", {
        "instruction": instruction, "screenshot": b64, "history": [],
        "session_id": sid, "user_id": "explorer",
        "model_tag": cfg.model_tag, "system_prompt": sp,
    })
    if not resp or resp.get("status") != "success":
        return None
    reply = resp.get("reply", "")
    m = re.search(r"\{[\s\S]*\}", reply)
    if m:
        try:
            return json.loads(m.group())
        except:
            pass
    return {"_raw": reply[:300]}

def find_btn(btns: List[Dict], keywords: List[str]) -> Optional[Tuple[int, int, str]]:
    for b in btns:
        lbl = str(b.get("label", ""))
        for kw in keywords:
            if kw in lbl:
                bb = b.get("bbox", [0, 0, 0, 0])
                if len(bb) >= 4 and bb[2] > bb[0]:
                    return ((bb[0] + bb[2]) // 2, (bb[1] + bb[3]) // 2, lbl)
    return None

def analyze(cfg: PipelineConfig, extra: str = "") -> Optional[Dict]:
    inst = "识别当前游戏画面。逐一列出每个按钮的标签和精确像素坐标，不要合并成组。"
    if extra:
        inst += "特别注意" + extra + "。"
    inst += '输出JSON：{"page_name":"","page_type":"","buttons":[{"label":"","bbox":[]}],"description":""}'
    return vlm(cfg, inst, "你是终末地UI分析器。每个按钮单独列出，输出JSON。")

def classify_page(r: Optional[Dict]) -> PageType:
    """根据 VLM 分析结果判断当前页面类型"""
    if not r:
        return PageType.UNKNOWN
    name = str(r.get("page_name", "")).lower()
    desc = str(r.get("description", "")).lower()
    btns = r.get("buttons", [])
    labels = " ".join([str(b.get("label", "")) for b in btns]).lower()

    # 基建界面特征：有"工业""制造""工具箱""装备"等
    if any(kw in labels for kw in ["工业", "制造", "工具箱", "装备"]):
        return PageType.BASE
    # 探索模式特征：有"电涌塔""激发""小地图""任务追踪"等
    if any(kw in labels for kw in ["电涌塔", "激发", "小地图", "探索"]):
        return PageType.EXPLORATION
    # 活动中心：有"活动中心"或左右分栏布局
    if any(kw in name for kw in ["活动", "event"]) or "活动中心" in desc:
        return PageType.EVENT_CENTER
    # 签到：有"签到""签""DAY"
    if any(kw in labels for kw in ["签到", "DAY", "签", "寻奇探幽"]):
        return PageType.SIGN_IN
    # 每周任务
    if any(kw in labels for kw in ["每周事务", "周常", "每周"]):
        return PageType.WEEKLY_TASKS
    return PageType.UNKNOWN


# ── 流水线 ────────────────────────────────────────────────────
class DailyPipeline:
    def __init__(self, cfg: PipelineConfig):
        self.cfg = cfg
        self.results = {
            "timestamp": time.time(),
            "model_tag": cfg.model_tag,
            "dry_run": cfg.dry_run,
            "pages_visited": [],
            "tasks": [],
            "claim_status": "unknown",
        }
        self._log_buf = []

    def log(self, msg: str, end="\n"):
        self._log_buf.append(msg)
        print(msg, end=end, flush=True)

    def save(self):
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

    def _go(self, x, y, label="", delay=None):
        if self.cfg.dry_run:
            self.log(f"  [DRY-RUN] tap ({x},{y}) {label}")
            return
        self.log(f"  tap ({x},{y}) {label}")
        tap(x, y)
        time.sleep(delay or self.cfg.post_tap_delay)

    # ── 核心步骤 ──
    def step_ensure_exploration(self) -> Optional[Dict]:
        """确保在探索模式（主界面），如果不在则切换"""
        self.log("\n[检测] 当前页面状态...")
        r = analyze(self.cfg)
        if not r:
            self.log("  VLM 分析失败")
            return None
        ptype = classify_page(r)
        self.log(f"  页面: {r.get('page_name','?')} → {ptype.value}")
        self.results["pages_visited"].append(r.get("page_name", "?"))

        if ptype == PageType.EXPLORATION:
            self.log("  ✅ 已在探索模式")
            return r
        elif ptype == PageType.BASE:
            self.log("  ⚡ 在基建模式，需切换")
            # 找探索模式按钮
            btns = r.get("buttons", [])
            exp = find_btn(btns, ["探索", "世界", "大地图"])
            if exp:
                self._go(exp[0], exp[1], f"[{exp[2]}]")
                r2 = analyze(self.cfg)
                if r2:
                    self.results["pages_visited"].append(r2.get("page_name", "?"))
                    self.log(f"  切换后: {r2.get('page_name','?')}")
                    return r2
            # 备用：尝试点击左上角探索模式切换
            self._go(86, 45, "探索模式切换(备用)")
            time.sleep(5)
            r2 = analyze(self.cfg)
            if r2:
                self.results["pages_visited"].append(r2.get("page_name", "?"))
                return r2
        return r

    def step_open_event(self, r: Optional[Dict]) -> Optional[Dict]:
        """打开活动中心"""
        self.log("\n[活动] 打开活动中心")
        btns = (r or {}).get("buttons", [])
        ev = find_btn(btns, ["活动", "EVENT", "事件", "event"])
        if ev:
            self._go(ev[0], ev[1], f"[{ev[2]}]")
        else:
            self.log("  VLM未找到活动按钮，使用经验坐标 (740, 50)")
            self._go(740, 50, "EVENT(备用)")

        # 等待并检查是否打开了活动中心
        time.sleep(self.cfg.post_tap_delay)
        r2 = analyze(self.cfg, "左侧活动列表")
        if r2:
            self.results["pages_visited"].append(r2.get("page_name", "?"))
            ptype = classify_page(r2)
            self.log(f"  跳转后: {r2.get('page_name','?')} → {ptype.value}")
            return r2
        return None

    def step_go_signin(self, r: Optional[Dict]) -> Optional[Dict]:
        """从活动中心进入签到页"""
        self.log("\n[签到] 寻找签到入口")
        btns = (r or {}).get("buttons", [])

        # 先找"寻奇探幽签到"列表项
        entry = find_btn(btns, ["寻奇探幽", "签到", "签", "奖励领取"])
        if entry:
            self._go(entry[0], entry[1], f"[{entry[2]}]")
        else:
            self.log("  未找到签到入口，尝试滚动左侧列表")
            # 可能列表需要滚动
            swipe(120, 400, 120, 200, 300)
            time.sleep(3)
            r2 = analyze(self.cfg, "左侧活动列表找到签到按钮")
            if r2:
                btns2 = r2.get("buttons", [])
                entry2 = find_btn(btns2, ["寻奇探幽", "签到", "签"])
                if entry2:
                    self._go(entry2[0], entry2[1], f"[{entry2[2]}]")
                else:
                    self.log("  滚动后仍未找到签到，尝试备用坐标 (112, 296)")
                    self._go(112, 296, "签到(备用)")
            else:
                self._go(112, 296, "签到(备用)")

        time.sleep(self.cfg.post_tap_delay)
        r2 = analyze(self.cfg, "寻找领取按钮")
        if r2:
            self.results["pages_visited"].append(r2.get("page_name", "?"))
            self.log(f"  签到页: {r2.get('page_name','?')}")
            return r2
        return None

    def step_claim(self, r: Optional[Dict]):
        """领取签到奖励"""
        self.log("\n[领取] 领取签到奖励")
        btns = (r or {}).get("buttons", [])

        # 优先找"一键领取"
        claim = find_btn(btns, ["一键领取", "一键", "全部领取"])
        if not claim:
            # 找单个"领取"按钮
            claim = find_btn(btns, ["领取", "签", "领奖"])
        if not claim:
            # 可能的坐标范围（来自页面知识）
            self.log("  使用备用领取坐标 (817, 852)")
            claim = (817, 852, "备用领取")

        if claim:
            self._go(claim[0], claim[1], f"[{claim[2]}]", delay=self.cfg.post_claim_delay)
            # 验证
            r2 = vlm(self.cfg, "刚才的领取操作成功了吗？JSON:{\"success\":false,\"message\":\"\"}", "")
            if r2:
                self.results["claim_status"] = "claimed" if r2.get("success") else "attempted"
                self.log(f"  结果: {json.dumps(r2, ensure_ascii=False)[:200]}")
        else:
            self.results["claim_status"] = "no_button"

    def step_weekly(self, r: Optional[Dict]):
        """分析每周事务"""
        self.log("\n[周常] 每周任务分析")
        btns = (r or {}).get("buttons", [])

        # 尝试切换到每周事务
        wk = find_btn(btns, ["每周事务", "每周", "周常", "事务"])
        if wk:
            self._go(wk[0], wk[1], f"[{wk[2]}]")
            time.sleep(self.cfg.post_tap_delay)

        # 分析任务
        r2 = vlm(self.cfg,
            "分析当前页面中的所有每周任务。每个任务列出名称、进度(如'3/10')和状态(in_progress/claimable/claimed)。"
            '输出JSON：{"tasks":[{"name":"","progress":"","status":""}]}',
            "你是终末地任务分析器。精确提取任务数据。")
        if r2:
            tasks = r2.get("tasks", [])
            if tasks:
                for t in tasks:
                    self.log(f"  [{t.get('status','?')}] {t.get('name','?')} - {t.get('progress','?')}")
                self.results["tasks"] = tasks
            else:
                self.log("  当前页面无可见每周任务")
        else:
            self.log("  分析失败")

    # ── 执行 ──
    def run(self):
        self.log(f"═══ 每日流水线 v3 (OCR优先) ═══")
        self.log(f"模型: {self.cfg.model_tag} | dry_run: {self.cfg.dry_run}")
        self.log(f"设备: localhost:16512")

        try:
            # ── 尝试使用优化引擎（OCR优先） ──
            try:
                from core.cloud.exploration_engine_optimized import OptimizedExplorationEngine
                engine = OptimizedExplorationEngine()
                engine.start_daily_flow()
                # 将执行日志同步到当前流水线
                for line in engine._execution_log:
                    self.log(line.lstrip("[").split("] ", 1)[-1] if "] " in line else line)
                self.results["claim_status"] = "completed"
                self.results["stats"] = engine._stats
                self.save()
                return
            except ImportError as e:
                self.log(f"优化引擎不可用 ({e})，回退 VLM 模式")
            except Exception as e:
                self.log(f"优化引擎异常 ({e})，回退 VLM 模式")

            # ── 回退：原 VLM 模式 ──
            # 1. 状态检测 + 确保在探索模式
            r = self.step_ensure_exploration()
            if not r:
                self.log("ERROR: 无法确定页面状态")
                self.save()
                return

            # 2. 任务分析（当前页面）
            self.log("\n[任务] 分析当前页面任务...")
            tasks = r.get("tasks", []) if r else []
            if tasks:
                for t in tasks:
                    self.log(f"  [{t.get('status','?')}] {t.get('name','?')}")

            # 3. 打开活动中心
            r = self.step_open_event(r)
            if not r:
                self.log("ERROR: 无法打开活动中心")
                self.save()
                return

            # 4. 进入签到
            r = self.step_go_signin(r)
            if r:
                # 5. 领取签到奖励
                self.step_claim(r)
            else:
                self.log("WARN: 签到页分析失败")

            # 6. 每周任务分析
            self.step_weekly(r)

            # 7. 返回世界地图再开任务面板
            self.log("\n[任务面板] 返回并打开任务面板...")
            for _ in range(3):
                tap(540, 540)  # 点击屏幕中央返回
                time.sleep(1)
            time.sleep(3)
            r2 = analyze(self.cfg)
            if r2:
                btns = r2.get("buttons", [])
                task_btn = find_btn(btns, ["任务", "日程", "quest"])
                if task_btn:
                    self._go(task_btn[0], task_btn[1], "[任务]")
                    r3 = analyze(self.cfg, "寻找领取/完成/提交按钮")
                    if r3:
                        btns3 = r3.get("buttons", [])
                        claim = find_btn(btns3, ["领取", "完成", "提交", "收取", "一键领取"])
                        if claim:
                            self._go(claim[0], claim[1], f"[领取:{claim[2]}]")
                            self.results["claim_status"] = "claimed"
                        # 检查每周
                        weekly = find_btn(btns3, ["每周事务", "周常"])
                        if weekly:
                            self._go(weekly[0], weekly[1], "[每周]")
                            time.sleep(5)
                            r4 = analyze(self.cfg, "找每周任务领取")
                            if r4:
                                wk_claim = find_btn(r4.get("buttons", []), ["领取", "完成"])
                                if wk_claim:
                                    self._go(wk_claim[0], wk_claim[1], f"[每周领取:{wk_claim[2]}]")

            self.log(f"\n═══ 完成 ═══")
            self.save()

        except KeyboardInterrupt:
            self.log("\n用户中断")
        except Exception as e:
            self.log(f"\n异常: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.save()
            self.log(f"结果保存: {OUTPUT_PATH}")


def main():
    parser = argparse.ArgumentParser(description="每日签到流水线 v2")
    parser.add_argument("--model", default="exploration_deep")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--delay", type=float, default=8.0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    cfg = PipelineConfig(
        model_tag=args.model,
        vlm_timeout=args.timeout,
        post_tap_delay=args.delay,
        dry_run=args.dry_run,
    )
    DailyPipeline(cfg).run()


if __name__ == "__main__":
    main()
