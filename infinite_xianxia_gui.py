#!/usr/bin/env python3
"""
无穷道途 GUI 版（保持原玩法逻辑不变）

运行:
  python3 infinite_xianxia_gui.py
"""

from __future__ import annotations

import random
import re
import tkinter as tk
from tkinter import messagebox, scrolledtext

from infinite_xianxia import (
    SAVE_PATH,
    REALMS,
    action_breakthrough,
    action_calm,
    action_challenge,
    action_cultivate,
    action_hunt,
    action_treasure,
    bounty_lines,
    help_lines,
    load_player,
    lore_lines,
    make_player,
    quest_status_lines,
    save_player,
    status_lines,
)

MAP_NAMES = [
    "外门山道",
    "灵溪平原",
    "青木洞天",
    "金丹古殿",
    "元婴星港",
    "化神云城",
    "炼虚裂谷",
    "合体天阙",
    "大乘神庭",
    "无量界海",
]

THEME = {
    "bg": "#0c1120",
    "panel": "#131c33",
    "panel_alt": "#18223d",
    "line": "#2d3d64",
    "text": "#eff4ff",
    "muted": "#b5c4e8",
    "dark_text": "#0b1430",
    "btn_bg": "#f7f9ff",
    "btn_bg_pressed": "#ffffff",
    "btn_disabled": "#eceff7",
    "blue": "#2f82ff",
    "green": "#1ea76f",
    "gold": "#d29a26",
    "purple": "#824ee8",
    "red": "#df4e68",
    "cyan": "#1f98ae",
}


class GameUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("无穷道途 - 图形交互版")
        self.root.geometry("1400x920")
        self.root.minsize(1200, 780)
        self.root.configure(bg=THEME["bg"])

        self.rng = random.Random()
        self.player = make_player(self.rng)

        self.last_monster_title = "未遭遇怪物"
        self.last_monster_kind = "未知"
        self.last_monster_rank = "-"
        self.last_monster_stats = "-"

        self.status_vars: list[tk.StringVar] = []
        self.kv_vars: dict[str, tk.StringVar] = {}

        self.major_buttons: dict[str, tk.Button] = {}
        self.major_button_labels: dict[str, str] = {}
        self.major_button_accents: dict[str, str] = {}

        self._build_layout()
        self._bind_shortcuts()
        self._setup_log_tags()

        self.refresh_status()
        self.append_log("[系统] 图形界面已启动。玩法逻辑与命令行版一致。")
        self.append_log("[系统] 高对比模式：按钮白底深字，禁用态仍清晰可读。")
        for line in help_lines():
            self.append_log(f"[帮助] {line}")

    def _card(self, parent: tk.Widget, title: str, fixed_height: int | None = None) -> tk.Frame:
        frame = tk.Frame(parent, bg=THEME["panel"], highlightthickness=1, highlightbackground=THEME["line"])
        if fixed_height:
            frame.configure(height=fixed_height)
            frame.pack_propagate(False)
        tk.Label(
            frame,
            text=title,
            bg=THEME["panel"],
            fg=THEME["text"],
            font=("PingFang SC", 12, "bold"),
            anchor="w",
            padx=10,
            pady=7,
        ).pack(fill="x")
        return frame

    def _build_layout(self) -> None:
        main = tk.Frame(self.root, bg=THEME["bg"])
        main.pack(fill="both", expand=True, padx=14, pady=14)

        self._build_header(main)

        body = tk.Frame(main, bg=THEME["bg"])
        body.pack(fill="both", expand=True, pady=(10, 0))

        left = tk.Frame(body, bg=THEME["bg"], width=320)
        center = tk.Frame(body, bg=THEME["bg"])
        right = tk.Frame(body, bg=THEME["bg"], width=370)

        left.pack(side="left", fill="y", padx=(0, 10))
        center.pack(side="left", fill="both", expand=True)
        right.pack(side="left", fill="y", padx=(10, 0))

        left.pack_propagate(False)
        right.pack_propagate(False)

        self._build_left_panel(left)
        self._build_center_panel(center)
        self._build_right_panel(right)

    def _build_header(self, parent: tk.Frame) -> None:
        box = tk.Frame(parent, bg=THEME["panel_alt"], highlightthickness=1, highlightbackground=THEME["line"])
        box.pack(fill="x")

        row = tk.Frame(box, bg=THEME["panel_alt"])
        row.pack(fill="x", padx=12, pady=(10, 6))

        tk.Label(
            row,
            text="无穷道途",
            bg=THEME["panel_alt"],
            fg=THEME["text"],
            font=("PingFang SC", 22, "bold"),
        ).pack(side="left")

        tk.Label(
            row,
            text="清晰交互版",
            bg=THEME["panel_alt"],
            fg=THEME["muted"],
            font=("PingFang SC", 11),
            padx=10,
        ).pack(side="left")

        chips = tk.Frame(box, bg=THEME["panel_alt"])
        chips.pack(fill="x", padx=8, pady=(0, 10))

        defs = [
            ("realm", "境界", THEME["blue"]),
            ("exp", "修为", THEME["green"]),
            ("amp", "增幅", THEME["purple"]),
            ("pressure", "心魔", THEME["red"]),
            ("keys", "寻宝令", THEME["gold"]),
            ("wl", "胜败", THEME["cyan"]),
        ]

        for i, (key, title, color) in enumerate(defs):
            card = tk.Frame(chips, bg="#1a2444", highlightthickness=1, highlightbackground=color)
            card.grid(row=0, column=i, sticky="nsew", padx=4)
            chips.grid_columnconfigure(i, weight=1)
            tk.Label(card, text=title, bg="#1a2444", fg=THEME["muted"], font=("PingFang SC", 9)).pack(pady=(4, 0))
            var = tk.StringVar(value="-")
            self.kv_vars[key] = var
            tk.Label(card, textvariable=var, bg="#1a2444", fg=THEME["text"], font=("PingFang SC", 11, "bold")).pack(pady=(0, 6))

    def _build_left_panel(self, parent: tk.Frame) -> None:
        action_card = self._card(parent, "操作区")
        action_card.pack(fill="x")

        wrap = tk.Frame(action_card, bg=THEME["panel"])
        wrap.pack(fill="x", padx=10, pady=(2, 8))

        major = [
            ("狩猎 (1)", self.on_hunt, THEME["blue"], "hunt"),
            ("修炼 (2)", self.on_cultivate, THEME["green"], "cultivate"),
            ("寻宝 (3)", self.on_treasure, THEME["gold"], "treasure"),
            ("守关 (4)", self.on_challenge, THEME["purple"], "challenge"),
            ("突破 (5)", self.on_break, THEME["red"], "break"),
            ("调息 (6)", self.on_calm, THEME["cyan"], "calm"),
        ]

        for i, (text, cmd, accent, key) in enumerate(major):
            btn = tk.Button(
                wrap,
                text=text,
                command=cmd,
                relief="flat",
                bd=0,
                bg=THEME["btn_bg"],
                fg=THEME["dark_text"],
                activebackground=THEME["btn_bg_pressed"],
                activeforeground=THEME["dark_text"],
                font=("PingFang SC", 12, "bold"),
                padx=10,
                pady=10,
                cursor="hand2",
                highlightthickness=3,
                highlightbackground=accent,
                highlightcolor=accent,
            )
            btn.grid(row=i, column=0, sticky="ew", pady=4)
            self.major_buttons[key] = btn
            self.major_button_labels[key] = text
            self.major_button_accents[key] = accent

        wrap.grid_columnconfigure(0, weight=1)

        util = tk.Frame(action_card, bg=THEME["panel"])
        util.pack(fill="x", padx=10, pady=(4, 10))

        for i, (text, cmd) in enumerate([
            ("任务 (Q)", self.on_quest),
            ("悬赏 (B)", self.on_bounty),
            ("剧情 (L)", self.on_lore),
            ("状态 (F5)", self.on_status),
            ("帮助 (H)", self.on_help),
            ("保存 (S)", self.on_save),
            ("读档 (R)", self.on_load),
        ]):
            btn = tk.Button(
                util,
                text=text,
                command=cmd,
                relief="flat",
                bd=0,
                bg="#ffffff",
                fg="#111d3b",
                activebackground="#f5f8ff",
                activeforeground="#111d3b",
                font=("PingFang SC", 11, "bold"),
                padx=8,
                pady=8,
                cursor="hand2",
            )
            btn.grid(row=i // 2, column=i % 2, sticky="ew", padx=3, pady=3)

        util.grid_columnconfigure(0, weight=1)
        util.grid_columnconfigure(1, weight=1)

        guide = self._card(parent, "操作建议", fixed_height=220)
        guide.pack(fill="x", pady=(10, 0))
        self.guide_var = tk.StringVar(value="-")
        tk.Label(
            guide,
            textvariable=self.guide_var,
            justify="left",
            anchor="nw",
            wraplength=290,
            bg=THEME["panel"],
            fg="#d9e5ff",
            font=("PingFang SC", 10),
            padx=10,
            pady=10,
        ).pack(fill="both", expand=True)

    def _build_center_panel(self, parent: tk.Frame) -> None:
        map_card = self._card(parent, "地图与战场")
        map_card.pack(fill="x")

        self.map_title_var = tk.StringVar(value="地图：-")
        tk.Label(
            map_card,
            textvariable=self.map_title_var,
            bg=THEME["panel"],
            fg=THEME["muted"],
            font=("PingFang SC", 10),
            anchor="w",
            padx=10,
            pady=0,
        ).pack(fill="x", pady=(0, 6))

        self.map_canvas = tk.Canvas(
            map_card,
            width=780,
            height=260,
            bg="#0f162d",
            relief="flat",
            highlightthickness=1,
            highlightbackground=THEME["line"],
        )
        self.map_canvas.pack(fill="x", padx=10, pady=(0, 10))
        self.map_canvas.bind("<Configure>", lambda _evt: self._draw_map())

        log_card = self._card(parent, "战斗与事件日志")
        log_card.pack(fill="both", expand=True, pady=(10, 0))

        self.log_box = scrolledtext.ScrolledText(
            log_card,
            wrap="word",
            bg="#0d1529",
            fg="#dce7ff",
            insertbackground="#dce7ff",
            relief="flat",
            font=("Menlo", 11),
        )
        self.log_box.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.log_box.configure(state="disabled")

    def _build_right_panel(self, parent: tk.Frame) -> None:
        monster_card = self._card(parent, "怪物识别")
        monster_card.pack(fill="x")

        self.monster_title_var = tk.StringVar(value="未遭遇怪物")
        tk.Label(
            monster_card,
            textvariable=self.monster_title_var,
            bg=THEME["panel"],
            fg=THEME["text"],
            font=("PingFang SC", 12, "bold"),
            pady=2,
        ).pack(fill="x")

        self.monster_stats_var = tk.StringVar(value="阶位: - | 属性: -")
        tk.Label(
            monster_card,
            textvariable=self.monster_stats_var,
            bg=THEME["panel"],
            fg=THEME["muted"],
            font=("PingFang SC", 10),
            pady=0,
        ).pack(fill="x", pady=(0, 6))

        self.monster_canvas = tk.Canvas(
            monster_card,
            width=340,
            height=290,
            bg="#101932",
            relief="flat",
            highlightthickness=1,
            highlightbackground=THEME["line"],
        )
        self.monster_canvas.pack(fill="x", padx=10, pady=(0, 10))
        self.monster_canvas.bind("<Configure>", lambda _evt: self._draw_monster())

        status_card = self._card(parent, "状态详情")
        status_card.pack(fill="both", expand=True, pady=(10, 0))

        detail = tk.Frame(status_card, bg=THEME["panel"])
        detail.pack(fill="both", expand=True, padx=8, pady=(0, 6))
        for _ in range(7):
            var = tk.StringVar(value="")
            self.status_vars.append(var)
            tk.Label(
                detail,
                textvariable=var,
                justify="left",
                anchor="w",
                wraplength=330,
                bg="#1a2440",
                fg="#dce7ff",
                font=("PingFang SC", 10),
                padx=8,
                pady=7,
            ).pack(fill="x", pady=3)

        story_card = self._card(parent, "剧情速览")
        story_card.pack(fill="both", expand=True, pady=(10, 0))

        self.story_box = scrolledtext.ScrolledText(
            story_card,
            wrap="word",
            bg="#0f1628",
            fg="#cfe0ff",
            insertbackground="#cfe0ff",
            relief="flat",
            font=("PingFang SC", 10),
            height=8,
        )
        self.story_box.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.story_box.configure(state="disabled")

    def _bind_shortcuts(self) -> None:
        bind_map = {
            "1": self.on_hunt,
            "2": self.on_cultivate,
            "3": self.on_treasure,
            "4": self.on_challenge,
            "5": self.on_break,
            "6": self.on_calm,
            "q": self.on_quest,
            "Q": self.on_quest,
            "b": self.on_bounty,
            "B": self.on_bounty,
            "l": self.on_lore,
            "L": self.on_lore,
            "h": self.on_help,
            "H": self.on_help,
            "s": self.on_save,
            "S": self.on_save,
            "r": self.on_load,
            "R": self.on_load,
        }
        for key, handler in bind_map.items():
            self.root.bind(key, lambda _evt, h=handler: h())
        self.root.bind("<F5>", lambda _evt: self.on_status())

    def _setup_log_tags(self) -> None:
        self.log_box.tag_config("sys", foreground="#88d9ff")
        self.log_box.tag_config("win", foreground="#7fe6a9")
        self.log_box.tag_config("loss", foreground="#ff9ba7")
        self.log_box.tag_config("quest", foreground="#f5d580")
        self.log_box.tag_config("story", foreground="#cfb3ff")
        self.log_box.tag_config("normal", foreground="#dce7ff")

    def append_log(self, line: str) -> None:
        tag = "normal"
        if line.startswith("[系统"):
            tag = "sys"
        elif line.startswith("[胜") or line.startswith("[守关胜") or line.startswith("[任务完成"):
            tag = "win"
        elif line.startswith("[落败") or line.startswith("[守关败"):
            tag = "loss"
        elif line.startswith("[剧情"):
            tag = "story"
        elif line.startswith("[宗门任务"):
            tag = "quest"

        self.log_box.configure(state="normal")
        self.log_box.insert("end", line + "\n", tag)
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _set_story_lines(self, lines: list[str]) -> None:
        self.story_box.configure(state="normal")
        self.story_box.delete("1.0", "end")
        for line in lines:
            self.story_box.insert("end", line + "\n")
        self.story_box.configure(state="disabled")

    def _draw_map(self) -> None:
        self.map_canvas.delete("all")

        w = max(self.map_canvas.winfo_width(), int(self.map_canvas.cget("width")))
        h = max(self.map_canvas.winfo_height(), int(self.map_canvas.cget("height")))

        idx = self.player.realm_idx
        cycle = self.player.cycle
        name = MAP_NAMES[min(idx, len(MAP_NAMES) - 1)]
        self.map_title_var.set(f"地图：{name} | 当前境界：{self.player.current_realm().name} | 轮回：{cycle}")

        palettes = [
            ("#1b2846", "#2d4c80", "#6cb2ff"),
            ("#173727", "#2c6a48", "#8edb8f"),
            ("#2e3118", "#69712b", "#d9de83"),
            ("#3b2618", "#7a4b2c", "#ebb07a"),
            ("#2a2242", "#5a3b8e", "#bf98ff"),
            ("#2b1f31", "#66427a", "#deaff7"),
            ("#2b1f25", "#7f3550", "#ffa2ba"),
            ("#17313a", "#2d5d70", "#92d8ef"),
            ("#182741", "#29477f", "#a7c1ff"),
            ("#1f1f1f", "#555555", "#d8d8d8"),
        ]
        sky, ground, accent = palettes[min(idx, len(palettes) - 1)]

        self.map_canvas.create_rectangle(0, 0, w, h, fill=sky, width=0)
        self.map_canvas.create_rectangle(0, h - 68, w, h, fill=ground, width=0)

        steps = min(10, len(REALMS))
        x_gap = (w - 100) / max(1, steps - 1)
        y = h - 42
        for i in range(steps):
            x = 50 + i * x_gap
            if i < steps - 1:
                x2 = 50 + (i + 1) * x_gap
                self.map_canvas.create_line(x, y, x2, y, fill="#91a5d4", width=2)
            node_color = accent if i <= idx else "#4c5878"
            self.map_canvas.create_oval(x - 8, y - 8, x + 8, y + 8, fill=node_color, outline="")
            if i <= idx:
                self.map_canvas.create_text(x, y + 16, text=REALMS[i].name, fill="#edf3ff", font=("PingFang SC", 9))

        moon_x = w - 110 - (cycle % 5) * 40
        self.map_canvas.create_oval(moon_x, 24, moon_x + 40, 64, fill=accent, outline="")
        self.map_canvas.create_text(14, 14, text=f"场景：{name}", fill="#edf3ff", font=("PingFang SC", 12, "bold"), anchor="nw")

    def _draw_monster(self) -> None:
        self.monster_canvas.delete("all")

        w = max(self.monster_canvas.winfo_width(), int(self.monster_canvas.cget("width")))
        h = max(self.monster_canvas.winfo_height(), int(self.monster_canvas.cget("height")))
        cx = w / 2

        self.monster_canvas.create_rectangle(0, 0, w, h, fill="#101932", width=0)

        name = self.last_monster_title
        kind = self.last_monster_kind
        seed = sum(ord(ch) for ch in name)
        color = ["#6ec5ff", "#9be27a", "#ffb86c", "#d8a6ff", "#ff8fa3", "#79d3d0"][seed % 6]
        eye = "#f4f7ff"
        pupil = "#0f1322"

        self.monster_canvas.create_text(cx, 24, text=name, fill="#e8efff", font=("PingFang SC", 12, "bold"))

        if "守关" in name:
            self.monster_canvas.create_polygon(cx - 70, h - 72, cx, 86, cx + 70, h - 72, fill=color, outline="", tags=("monster_body",))
            self.monster_canvas.create_rectangle(cx - 22, 64, cx + 22, 84, fill="#f2ca55", outline="", tags=("monster_body",))
            self.monster_canvas.create_oval(cx - 34, 134, cx - 14, 154, fill=eye, outline="", tags=("monster_body",))
            self.monster_canvas.create_oval(cx + 14, 134, cx + 34, 154, fill=eye, outline="", tags=("monster_body",))
            self.monster_canvas.create_oval(cx - 27, 141, cx - 21, 147, fill=pupil, outline="", tags=("monster_body",))
            self.monster_canvas.create_oval(cx + 21, 141, cx + 27, 147, fill=pupil, outline="", tags=("monster_body",))
        elif "狼" in kind:
            self.monster_canvas.create_oval(cx - 80, 110, cx + 80, 225, fill=color, outline="", tags=("monster_body",))
            self.monster_canvas.create_polygon(cx - 55, 115, cx - 27, 74, cx - 13, 118, fill=color, outline="", tags=("monster_body",))
            self.monster_canvas.create_polygon(cx + 55, 115, cx + 27, 74, cx + 13, 118, fill=color, outline="", tags=("monster_body",))
            self.monster_canvas.create_oval(cx - 37, 148, cx - 19, 166, fill=eye, outline="", tags=("monster_body",))
            self.monster_canvas.create_oval(cx + 19, 148, cx + 37, 166, fill=eye, outline="", tags=("monster_body",))
            self.monster_canvas.create_oval(cx - 31, 154, cx - 25, 160, fill=pupil, outline="", tags=("monster_body",))
            self.monster_canvas.create_oval(cx + 25, 154, cx + 31, 160, fill=pupil, outline="", tags=("monster_body",))
        elif "鬼" in kind or "魇" in kind:
            self.monster_canvas.create_oval(cx - 65, 95, cx + 65, 200, fill=color, outline="", tags=("monster_body",))
            for i in range(7):
                x0 = cx - 65 + i * 18
                self.monster_canvas.create_polygon(x0, 190, x0 + 8, 224, x0 + 16, 190, fill=color, outline="", tags=("monster_body",))
            self.monster_canvas.create_oval(cx - 37, 140, cx - 17, 160, fill=eye, outline="", tags=("monster_body",))
            self.monster_canvas.create_oval(cx + 17, 140, cx + 37, 160, fill=eye, outline="", tags=("monster_body",))
            self.monster_canvas.create_oval(cx - 30, 147, cx - 24, 153, fill=pupil, outline="", tags=("monster_body",))
            self.monster_canvas.create_oval(cx + 24, 147, cx + 30, 153, fill=pupil, outline="", tags=("monster_body",))
        elif "蛇" in kind:
            self.monster_canvas.create_arc(cx - 100, 130, cx + 100, 245, start=10, extent=295, style="arc", width=18, outline=color, tags=("monster_body",))
            self.monster_canvas.create_oval(cx + 18, 90, cx + 82, 155, fill=color, outline="", tags=("monster_body",))
            self.monster_canvas.create_oval(cx + 37, 114, cx + 49, 126, fill=eye, outline="", tags=("monster_body",))
            self.monster_canvas.create_oval(cx + 61, 114, cx + 73, 126, fill=eye, outline="", tags=("monster_body",))
            self.monster_canvas.create_line(cx + 72, 135, cx + 96, 147, fill="#ff6f8f", width=3, tags=("monster_body",))
            self.monster_canvas.create_line(cx + 96, 147, cx + 109, 136, fill="#ff6f8f", width=2, tags=("monster_body",))
            self.monster_canvas.create_line(cx + 96, 147, cx + 109, 158, fill="#ff6f8f", width=2, tags=("monster_body",))
        else:
            self.monster_canvas.create_oval(cx - 73, 105, cx + 73, 225, fill=color, outline="", tags=("monster_body",))
            self.monster_canvas.create_rectangle(cx - 49, 128, cx + 49, 208, outline="#dce8ff", width=2, tags=("monster_body",))
            self.monster_canvas.create_oval(cx - 31, 146, cx - 9, 168, fill=eye, outline="", tags=("monster_body",))
            self.monster_canvas.create_oval(cx + 9, 146, cx + 31, 168, fill=eye, outline="", tags=("monster_body",))
            self.monster_canvas.create_oval(cx - 23, 154, cx - 17, 160, fill=pupil, outline="", tags=("monster_body",))
            self.monster_canvas.create_oval(cx + 17, 154, cx + 23, 160, fill=pupil, outline="", tags=("monster_body",))

        # 按包围盒强制把怪物图形居中到识别区域（不受怪物形状偏置影响）
        bbox = self.monster_canvas.bbox("monster_body")
        if bbox:
            cur_x = (bbox[0] + bbox[2]) / 2
            cur_y = (bbox[1] + bbox[3]) / 2
            target_x = w / 2
            target_y = (76 + (h - 58)) / 2
            self.monster_canvas.move("monster_body", target_x - cur_x, target_y - cur_y)

        danger = 0.35
        if "守关" in name:
            danger = 0.92
        elif "首领" in self.last_monster_rank:
            danger = 0.75
        elif "精英" in self.last_monster_rank:
            danger = 0.55

        bar_w = min(280, w - 40)
        x0 = (w - bar_w) / 2
        x1 = x0 + bar_w
        y0, y1 = h - 42, h - 24
        self.monster_canvas.create_rectangle(x0, y0, x1, y1, fill="#25324f", outline="")
        self.monster_canvas.create_rectangle(x0, y0, x0 + bar_w * danger, y1, fill="#e16f87", outline="")
        self.monster_canvas.create_text(w / 2, (y0 + y1) / 2, text="威胁等级", fill="#f0f5ff", font=("PingFang SC", 9))

    def _update_last_monster_from_lines(self, lines: list[str]) -> None:
        for line in lines:
            if line.startswith("[狩猎] "):
                m = re.search(r"^\[狩猎\]\s+([^|]+)\|", line)
                if m:
                    head = m.group(1).strip()
                    self.last_monster_title = head
                    parts = head.split()
                    self.last_monster_rank = parts[0] if parts else "-"
                    self.last_monster_kind = parts[-1] if parts else "未知"
                m2 = re.search(r"攻\s+([^\s]+)\s+防\s+([^\s]+)\s+血\s+([^\s]+)", line)
                if m2:
                    self.last_monster_stats = f"攻 {m2.group(1)} / 防 {m2.group(2)} / 血 {m2.group(3)}"
            elif line.startswith("[守关] "):
                m = re.search(r"^\[守关\]\s+([^|]+)\|", line)
                if m:
                    self.last_monster_title = m.group(1).strip()
                    self.last_monster_rank = "守关"
                    self.last_monster_kind = "守关者"
                m2 = re.search(r"攻\s+([^\s]+)\s+防\s+([^\s]+)\s+血\s+([^\s]+)", line)
                if m2:
                    self.last_monster_stats = f"攻 {m2.group(1)} / 防 {m2.group(2)} / 血 {m2.group(3)}"

        self.monster_title_var.set(self.last_monster_title)
        self.monster_stats_var.set(f"阶位: {self.last_monster_rank} | 属性: {self.last_monster_stats}")

    def _parse_runtime_flags(self) -> dict[str, int]:
        lines = status_lines(self.player)
        out = {
            "exp_now": 0,
            "exp_need": 0,
            "guard_ok": 0,
            "keys": 0,
            "cooldown": 0,
            "trial_now": 0,
            "trial_need": 0,
        }
        full = " | ".join(lines)

        m = re.search(r"修为:\s*(\d+)/(\d+)", full)
        if m:
            out["exp_now"] = int(m.group(1))
            out["exp_need"] = int(m.group(2))

        guard_line = next((line for line in lines if "下阶守关:" in line), "")
        if "已完成" in guard_line:
            out["guard_ok"] = 1

        m = re.search(r"寻宝令[:\s]+(\d+)/3", full)
        if m:
            out["keys"] = int(m.group(1))
        m2 = re.search(r"(?:寻宝冷却|冷却)[:\s]+(\d+)", full)
        if m2:
            out["cooldown"] = int(m2.group(1))
        m3 = re.search(r"破境资粮[:\s]+(\d+)/(\d+)", full)
        if m3:
            out["trial_now"] = int(m3.group(1))
            out["trial_need"] = int(m3.group(2))

        q_lines = quest_status_lines(self.player)
        out["quest_done"] = 1 if q_lines and "已完成" in q_lines[0] else 0
        return out

    def _update_top_metrics(self) -> None:
        lines = status_lines(self.player)
        q_lines = quest_status_lines(self.player)
        full = " | ".join(lines)

        self.kv_vars["realm"].set(self.player.current_realm().name)

        exp_text = "-"
        m = re.search(r"修为:\s*(\d+)/(\d+)", full)
        if m:
            exp_text = f"{m.group(1)}/{m.group(2)}"
        self.kv_vars["exp"].set(exp_text)

        amp_text = "-"
        m = re.search(r"阶\s*(\d+).*值\s*([0-9.]+)", full)
        if m:
            amp_text = f"阶{m.group(1)} / {m.group(2)}"
        self.kv_vars["amp"].set(amp_text)

        pressure_text = "-"
        m = re.search(r"(?:心魔压强|心魔)[:\s]+([0-9.]+)/100", full)
        if m:
            pressure_text = m.group(1)
        self.kv_vars["pressure"].set(pressure_text)

        key_text = "-"
        m = re.search(r"寻宝令[:\s]+(\d+/3)", full)
        if m:
            key_text = m.group(1)
        self.kv_vars["keys"].set(key_text)

        wl_text = "-"
        m = re.search(r"胜败[:\s]+(\d+/\d+)", full)
        if m:
            wl_text = m.group(1)
        self.kv_vars["wl"].set(wl_text)

        if q_lines:
            guide = q_lines[0]
            if len(q_lines) > 1:
                guide += "\n" + q_lines[1]
            self.guide_var.set(guide)

    def _set_major_button_state(self, key: str, enabled: bool) -> None:
        btn = self.major_buttons.get(key)
        if btn is None:
            return
        accent = self.major_button_accents.get(key, THEME["line"])
        text = self.major_button_labels.get(key, key)
        if enabled:
            btn.configure(
                text=text,
                bg=THEME["btn_bg"],
                fg=THEME["dark_text"],
                activebackground=THEME["btn_bg_pressed"],
                activeforeground=THEME["dark_text"],
                highlightbackground=accent,
                highlightcolor=accent,
                cursor="hand2",
            )
        else:
            btn.configure(
                text=f"{text} · 条件不足",
                bg=THEME["btn_disabled"],
                fg="#1a284a",
                activebackground=THEME["btn_disabled"],
                activeforeground="#1a284a",
                highlightbackground="#8d99b6",
                highlightcolor="#8d99b6",
                cursor="arrow",
            )

    def _update_button_states(self) -> None:
        flags = self._parse_runtime_flags()
        challenge_need = max(2, int(flags["trial_need"] * 0.55 + 0.999))
        can_break = (
            flags["guard_ok"]
            and flags["exp_now"] >= flags["exp_need"]
            and flags["trial_now"] >= flags["trial_need"]
        )
        can_challenge = flags["quest_done"] and not flags["guard_ok"] and flags["trial_now"] >= challenge_need
        can_treasure = flags["keys"] > 0 and flags["cooldown"] == 0

        self._set_major_button_state("break", bool(can_break))
        self._set_major_button_state("challenge", bool(can_challenge))
        self._set_major_button_state("treasure", bool(can_treasure))

    def refresh_status(self) -> None:
        lines = status_lines(self.player)
        while len(lines) < len(self.status_vars):
            lines.append("")
        for var, text in zip(self.status_vars, lines):
            var.set(text)

        self._set_story_lines(lore_lines(self.player))
        self._update_top_metrics()
        self._update_button_states()
        self._draw_map()
        self._draw_monster()

    def _run_action(self, action: str) -> None:
        if action == "hunt":
            lines = action_hunt(self.player, self.rng)
        elif action == "cultivate":
            lines = action_cultivate(self.player, self.rng)
        elif action == "treasure":
            lines = action_treasure(self.player, self.rng)
        elif action == "challenge":
            lines = action_challenge(self.player, self.rng)
        elif action == "break":
            lines = action_breakthrough(self.player, self.rng)
        elif action == "calm":
            lines = action_calm(self.player)
        elif action == "quest":
            lines = quest_status_lines(self.player)
        elif action == "bounty":
            lines = bounty_lines(self.player)
        elif action == "lore":
            lines = lore_lines(self.player)
        elif action == "status":
            lines = status_lines(self.player)
        elif action == "help":
            lines = help_lines()
        else:
            lines = ["未知动作"]

        self._update_last_monster_from_lines(lines)
        self.append_log(f"[系统] === 执行动作: {action} ===")
        for line in lines:
            self.append_log(line)
        self.refresh_status()

    def on_hunt(self) -> None:
        self._run_action("hunt")

    def on_cultivate(self) -> None:
        self._run_action("cultivate")

    def on_treasure(self) -> None:
        self._run_action("treasure")

    def on_challenge(self) -> None:
        self._run_action("challenge")

    def on_break(self) -> None:
        self._run_action("break")

    def on_calm(self) -> None:
        self._run_action("calm")

    def on_quest(self) -> None:
        self._run_action("quest")

    def on_bounty(self) -> None:
        self._run_action("bounty")

    def on_lore(self) -> None:
        self._run_action("lore")

    def on_help(self) -> None:
        self._run_action("help")

    def on_status(self) -> None:
        self._run_action("status")

    def on_save(self) -> None:
        try:
            msg = save_player(self.player)
            self.append_log(f"[系统] {msg}")
            self.refresh_status()
        except Exception as exc:
            messagebox.showerror("保存失败", str(exc))

    def on_load(self) -> None:
        try:
            if not SAVE_PATH.exists():
                messagebox.showinfo("读档", f"未找到存档文件：{SAVE_PATH}")
                return
            self.player = load_player(SAVE_PATH)
            self.append_log(f"[系统] 已读取存档：{SAVE_PATH}")
            self.refresh_status()
        except Exception as exc:
            messagebox.showerror("读档失败", str(exc))


def main() -> None:
    root = tk.Tk()
    GameUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
