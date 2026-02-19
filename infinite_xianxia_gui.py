#!/usr/bin/env python3
"""
无穷道途 GUI 版（保持原玩法逻辑不变）

运行:
  python3 infinite_xianxia_gui.py
"""

from __future__ import annotations

import random
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


class GameUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("无穷道途 - 图形界面版")
        self.root.geometry("1240x860")
        self.root.minsize(1100, 760)
        self.root.configure(bg="#0e1220")

        self.rng = random.Random()
        self.player = make_player(self.rng)
        self.last_monster_title = "未遭遇怪物"
        self.last_monster_kind = "未知"
        self.last_lines: list[str] = []

        self._build_layout()
        self._draw_map()
        self._draw_monster()
        self.refresh_status()
        self.append_log("欢迎来到《无穷道途》图形版。核心玩法与文字版一致。")
        for line in help_lines():
            self.append_log(line)

    def _build_layout(self) -> None:
        main = tk.Frame(self.root, bg="#0e1220")
        main.pack(fill="both", expand=True, padx=14, pady=14)

        left = tk.Frame(main, bg="#121a2e", bd=0, highlightthickness=1, highlightbackground="#2a3456")
        center = tk.Frame(main, bg="#0e1220")
        right = tk.Frame(main, bg="#121a2e", bd=0, highlightthickness=1, highlightbackground="#2a3456")

        left.pack(side="left", fill="y", padx=(0, 10))
        center.pack(side="left", fill="both", expand=True)
        right.pack(side="left", fill="y", padx=(10, 0))

        self._build_left_panel(left)
        self._build_center_panel(center)
        self._build_right_panel(right)

    def _build_left_panel(self, parent: tk.Frame) -> None:
        tk.Label(
            parent,
            text="角色面板",
            font=("PingFang SC", 16, "bold"),
            fg="#eaf0ff",
            bg="#121a2e",
            pady=12,
        ).pack(fill="x")

        self.status_vars = []
        for _ in range(7):
            var = tk.StringVar(value="")
            self.status_vars.append(var)
            tk.Label(
                parent,
                textvariable=var,
                justify="left",
                anchor="w",
                wraplength=290,
                font=("PingFang SC", 11),
                fg="#c9d7ff",
                bg="#121a2e",
                padx=12,
                pady=8,
            ).pack(fill="x")

        tk.Label(
            parent,
            text="剧情速览",
            font=("PingFang SC", 12, "bold"),
            fg="#eaf0ff",
            bg="#121a2e",
            padx=12,
            pady=8,
            anchor="w",
        ).pack(fill="x")

        self.story_box = scrolledtext.ScrolledText(
            parent,
            width=36,
            height=14,
            wrap="word",
            bg="#0f1628",
            fg="#d4defc",
            insertbackground="#d4defc",
            relief="flat",
            font=("PingFang SC", 10),
        )
        self.story_box.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.story_box.configure(state="disabled")

    def _build_center_panel(self, parent: tk.Frame) -> None:
        top = tk.Frame(parent, bg="#0e1220")
        top.pack(fill="x")

        self.map_title_var = tk.StringVar(value="地图：-")
        tk.Label(
            top,
            textvariable=self.map_title_var,
            font=("PingFang SC", 14, "bold"),
            fg="#eaf0ff",
            bg="#0e1220",
            anchor="w",
        ).pack(fill="x", pady=(0, 8))

        self.map_canvas = tk.Canvas(
            parent,
            width=620,
            height=220,
            bg="#11172a",
            relief="flat",
            highlightthickness=1,
            highlightbackground="#2a3456",
        )
        self.map_canvas.pack(fill="x")

        log_title = tk.Label(
            parent,
            text="战斗与事件日志",
            font=("PingFang SC", 13, "bold"),
            fg="#eaf0ff",
            bg="#0e1220",
            anchor="w",
            pady=10,
        )
        log_title.pack(fill="x")

        self.log_box = scrolledtext.ScrolledText(
            parent,
            wrap="word",
            bg="#0f1628",
            fg="#d8e4ff",
            insertbackground="#d8e4ff",
            relief="flat",
            font=("PingFang SC", 10),
        )
        self.log_box.pack(fill="both", expand=True)
        self.log_box.configure(state="disabled")

    def _build_right_panel(self, parent: tk.Frame) -> None:
        tk.Label(
            parent,
            text="怪物图鉴",
            font=("PingFang SC", 16, "bold"),
            fg="#eaf0ff",
            bg="#121a2e",
            pady=12,
        ).pack(fill="x")

        self.monster_title_var = tk.StringVar(value="未遭遇怪物")
        tk.Label(
            parent,
            textvariable=self.monster_title_var,
            font=("PingFang SC", 12, "bold"),
            fg="#dce7ff",
            bg="#121a2e",
            pady=6,
        ).pack(fill="x")

        self.monster_canvas = tk.Canvas(
            parent,
            width=300,
            height=250,
            bg="#0f1628",
            relief="flat",
            highlightthickness=1,
            highlightbackground="#2a3456",
        )
        self.monster_canvas.pack(padx=12, pady=(0, 12))

        btn_wrap = tk.Frame(parent, bg="#121a2e")
        btn_wrap.pack(fill="x", padx=12, pady=(0, 12))

        buttons = [
            ("狩猎", self.on_hunt, "#316dff"),
            ("修炼", self.on_cultivate, "#2b8a3e"),
            ("寻宝", self.on_treasure, "#b6801c"),
            ("守关", self.on_challenge, "#8f3fb3"),
            ("突破", self.on_break, "#c7466a"),
            ("调息", self.on_calm, "#007d92"),
            ("任务", self.on_quest, "#465c8c"),
            ("剧情", self.on_lore, "#465c8c"),
            ("帮助", self.on_help, "#465c8c"),
            ("保存", self.on_save, "#465c8c"),
            ("读档", self.on_load, "#465c8c"),
            ("刷新状态", self.on_status, "#465c8c"),
        ]

        for i, (text, cmd, color) in enumerate(buttons):
            btn = tk.Button(
                btn_wrap,
                text=text,
                command=cmd,
                relief="flat",
                bg=color,
                fg="white",
                activebackground="#25304f",
                activeforeground="white",
                font=("PingFang SC", 10, "bold"),
                padx=8,
                pady=8,
                cursor="hand2",
            )
            btn.grid(row=i // 2, column=i % 2, sticky="ew", padx=4, pady=4)

        btn_wrap.grid_columnconfigure(0, weight=1)
        btn_wrap.grid_columnconfigure(1, weight=1)

    def append_log(self, line: str) -> None:
        self.log_box.configure(state="normal")
        self.log_box.insert("end", line + "\n")
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
        realm_idx = self.player.realm_idx
        cycle = self.player.cycle
        name = MAP_NAMES[min(realm_idx, len(MAP_NAMES) - 1)]
        self.map_title_var.set(f"地图：{name}  |  轮回 {cycle}")

        palettes = [
            ("#1f2a44", "#223d65", "#5fa3ff"),
            ("#1f3b2f", "#27633f", "#88d17a"),
            ("#2d3b1b", "#5f7124", "#cfd66f"),
            ("#3b2718", "#7a4f22", "#e39a4d"),
            ("#2f1f3f", "#5a2e7e", "#b884ff"),
            ("#2c2430", "#5b3f66", "#cf9ef7"),
            ("#2f1f24", "#7f2f46", "#f08ca3"),
            ("#1c2b33", "#2c5364", "#7ec8e3"),
            ("#1b2435", "#253a6b", "#9cb8ff"),
            ("#1b1b1b", "#4d4d4d", "#cfcfcf"),
        ]
        bg, mountain, accent = palettes[min(realm_idx, len(palettes) - 1)]

        self.map_canvas.create_rectangle(0, 0, 620, 220, fill=bg, width=0)
        self.map_canvas.create_rectangle(0, 165, 620, 220, fill=mountain, width=0)

        h1 = 70 + (realm_idx * 6) % 55
        h2 = 85 + (realm_idx * 8) % 60
        h3 = 60 + (realm_idx * 5) % 70
        self.map_canvas.create_polygon(20, 165, 140, h1, 240, 165, fill="#2d446f", outline="")
        self.map_canvas.create_polygon(180, 165, 320, h2, 460, 165, fill="#385884", outline="")
        self.map_canvas.create_polygon(370, 165, 510, h3, 610, 165, fill="#2f4f79", outline="")

        moon_x = 520 - (cycle % 6) * 50
        self.map_canvas.create_oval(moon_x, 30, moon_x + 36, 66, fill=accent, outline="")
        self.map_canvas.create_text(
            14,
            14,
            text=f"{name} · 境界{self.player.current_realm().name}",
            fill="#eaf0ff",
            font=("PingFang SC", 11, "bold"),
            anchor="nw",
        )

        for i in range(12):
            sx = 30 + i * 48
            sy = 180 + (i % 3) * 6
            self.map_canvas.create_rectangle(sx, sy, sx + 20, sy + 20, fill=accent, outline="")

    def _draw_monster(self) -> None:
        self.monster_canvas.delete("all")
        self.monster_canvas.create_rectangle(0, 0, 300, 250, fill="#101932", width=0)

        name = self.last_monster_title
        kind = self.last_monster_kind
        seed = sum(ord(ch) for ch in name)
        color_base = ["#6ec5ff", "#9be27a", "#ffb86c", "#d8a6ff", "#ff8fa3", "#79d3d0"][seed % 6]
        eye = "#f4f7ff"
        pupil = "#0f1322"

        self.monster_canvas.create_text(
            150,
            20,
            text=name,
            fill="#e8efff",
            font=("PingFang SC", 12, "bold"),
        )

        if "守关" in name:
            self.monster_canvas.create_polygon(90, 190, 150, 70, 210, 190, fill=color_base, outline="")
            self.monster_canvas.create_rectangle(130, 48, 170, 68, fill="#f2ca55", outline="")
            self.monster_canvas.create_oval(118, 115, 136, 133, fill=eye, outline="")
            self.monster_canvas.create_oval(164, 115, 182, 133, fill=eye, outline="")
            self.monster_canvas.create_oval(124, 121, 130, 127, fill=pupil, outline="")
            self.monster_canvas.create_oval(170, 121, 176, 127, fill=pupil, outline="")
        elif "狼" in kind:
            self.monster_canvas.create_oval(80, 90, 220, 200, fill=color_base, outline="")
            self.monster_canvas.create_polygon(105, 95, 130, 60, 145, 100, fill=color_base, outline="")
            self.monster_canvas.create_polygon(195, 95, 170, 60, 155, 100, fill=color_base, outline="")
            self.monster_canvas.create_oval(120, 125, 138, 143, fill=eye, outline="")
            self.monster_canvas.create_oval(162, 125, 180, 143, fill=eye, outline="")
            self.monster_canvas.create_oval(127, 132, 133, 138, fill=pupil, outline="")
            self.monster_canvas.create_oval(169, 132, 175, 138, fill=pupil, outline="")
        elif "鬼" in kind or "魇" in kind:
            self.monster_canvas.create_oval(95, 78, 205, 178, fill=color_base, outline="")
            for i in range(6):
                self.monster_canvas.create_polygon(
                    95 + i * 18,
                    168,
                    103 + i * 18,
                    198,
                    111 + i * 18,
                    168,
                    fill=color_base,
                    outline="",
                )
            self.monster_canvas.create_oval(120, 115, 138, 133, fill=eye, outline="")
            self.monster_canvas.create_oval(162, 115, 180, 133, fill=eye, outline="")
            self.monster_canvas.create_oval(127, 122, 133, 128, fill=pupil, outline="")
            self.monster_canvas.create_oval(169, 122, 175, 128, fill=pupil, outline="")
        elif "蛇" in kind:
            self.monster_canvas.create_arc(60, 110, 250, 220, start=10, extent=290, style="arc", width=16, outline=color_base)
            self.monster_canvas.create_oval(175, 80, 235, 140, fill=color_base, outline="")
            self.monster_canvas.create_oval(193, 102, 205, 114, fill=eye, outline="")
            self.monster_canvas.create_oval(215, 102, 227, 114, fill=eye, outline="")
            self.monster_canvas.create_line(224, 122, 246, 132, fill="#ff6f8f", width=3)
            self.monster_canvas.create_line(246, 132, 258, 122, fill="#ff6f8f", width=2)
            self.monster_canvas.create_line(246, 132, 258, 142, fill="#ff6f8f", width=2)
        else:
            self.monster_canvas.create_oval(90, 85, 210, 205, fill=color_base, outline="")
            self.monster_canvas.create_rectangle(108, 105, 192, 185, outline="#dce8ff", width=2)
            self.monster_canvas.create_oval(122, 122, 142, 142, fill=eye, outline="")
            self.monster_canvas.create_oval(158, 122, 178, 142, fill=eye, outline="")
            self.monster_canvas.create_oval(129, 129, 135, 135, fill=pupil, outline="")
            self.monster_canvas.create_oval(165, 129, 171, 135, fill=pupil, outline="")

        self.monster_canvas.create_text(
            150,
            232,
            text=f"类型：{kind}",
            fill="#b7c8f7",
            font=("PingFang SC", 10),
        )

    def _update_last_monster_from_lines(self, lines: list[str]) -> None:
        for line in lines:
            if line.startswith("[狩猎] "):
                payload = line.split("] ", 1)[1]
                head = payload.split("|", 1)[0].strip()
                parts = head.split()
                if len(parts) >= 2:
                    self.last_monster_title = " ".join(parts)
                    self.last_monster_kind = parts[-1]
            elif line.startswith("[守关] "):
                payload = line.split("] ", 1)[1]
                head = payload.split("|", 1)[0].strip()
                self.last_monster_title = head
                self.last_monster_kind = "守关者"
        self.monster_title_var.set(self.last_monster_title)

    def refresh_status(self) -> None:
        lines = status_lines(self.player)
        while len(lines) < len(self.status_vars):
            lines.append("")
        for var, text in zip(self.status_vars, lines):
            var.set(text)
        self._set_story_lines(lore_lines(self.player))
        self._draw_map()
        self._draw_monster()

    def _run_action(self, action_name: str) -> None:
        if action_name == "hunt":
            lines = action_hunt(self.player, self.rng)
        elif action_name == "cultivate":
            lines = action_cultivate(self.player, self.rng)
        elif action_name == "treasure":
            lines = action_treasure(self.player, self.rng)
        elif action_name == "challenge":
            lines = action_challenge(self.player, self.rng)
        elif action_name == "break":
            lines = action_breakthrough(self.player, self.rng)
        elif action_name == "calm":
            lines = action_calm(self.player)
        elif action_name == "quest":
            lines = quest_status_lines(self.player)
        elif action_name == "lore":
            lines = lore_lines(self.player)
        elif action_name == "status":
            lines = status_lines(self.player)
        elif action_name == "help":
            lines = help_lines()
        else:
            lines = ["未知动作"]

        self.last_lines = lines
        self._update_last_monster_from_lines(lines)
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

    def on_lore(self) -> None:
        self._run_action("lore")

    def on_help(self) -> None:
        self._run_action("help")

    def on_status(self) -> None:
        self._run_action("status")

    def on_save(self) -> None:
        msg = save_player(self.player)
        self.append_log(msg)
        self.refresh_status()

    def on_load(self) -> None:
        try:
            if not SAVE_PATH.exists():
                messagebox.showinfo("读档", f"未找到存档文件：{SAVE_PATH}")
                return
            self.player = load_player(SAVE_PATH)
            self.append_log(f"已读取存档：{SAVE_PATH}")
            self.refresh_status()
        except Exception as exc:
            messagebox.showerror("读档失败", str(exc))


def main() -> None:
    root = tk.Tk()
    GameUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()

