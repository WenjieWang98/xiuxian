#!/usr/bin/env python3
"""
无穷道途（文字版原型）

运行:
  python3 infinite_xianxia.py
  python3 infinite_xianxia.py --auto 120 --seed 42
"""

from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple


SAVE_PATH = Path("infinite_xianxia_save.json")


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


@dataclass
class BigNum:
    """
    大数近似:
    layer=0: value=mag
    layer>0: value ~= 10^(10^(...^(mag)))，嵌套次数为 layer
    """

    layer: int = 0
    mag: float = 1.0

    @staticmethod
    def from_value(value: float) -> "BigNum":
        return BigNum(0, max(1e-12, float(value))).normalize()

    def normalize(self) -> "BigNum":
        if not math.isfinite(self.mag):
            self.layer += 1
            self.mag = 6.0
        if self.mag <= 1e-12:
            self.mag = 1e-12

        if self.layer == 0 and self.mag >= 1e12:
            self.mag = math.log10(self.mag)
            self.layer = 1

        while self.layer > 0 and self.mag >= 1e6:
            self.mag = math.log10(self.mag)
            self.layer += 1

        if self.layer == 1 and self.mag < 6.0:
            self.mag = 10 ** self.mag
            self.layer = 0
        return self

    def score(self) -> float:
        return self.layer * 2500.0 + self.mag

    def add(self, amount: float) -> "BigNum":
        if amount <= 0:
            return self
        if self.layer == 0:
            self.mag += amount
        elif self.layer == 1 and self.mag < 14:
            self.mag = math.log10((10 ** self.mag) + amount)
        return self.normalize()

    def mul(self, factor: float) -> "BigNum":
        factor = max(1e-12, factor)
        if self.layer == 0:
            self.mag *= factor
        elif self.layer == 1:
            self.mag += math.log10(factor)
        else:
            self.mag += math.log10(max(1.0, factor)) * 0.075
        return self.normalize()

    def pow(self, exponent: float) -> "BigNum":
        exponent = max(1e-6, exponent)
        if self.layer == 0:
            self.mag = self.mag**exponent
        elif self.layer == 1:
            self.mag *= exponent
        elif self.layer == 2:
            self.mag += math.log10(exponent) * 0.82
        else:
            self.mag += math.log10(exponent) * 0.32
        return self.normalize()

    def hyper(self, arrows: int, n: int) -> "BigNum":
        arrows = max(1, int(arrows))
        n = max(2, int(n))
        if arrows == 1:
            return self.pow(float(n))
        layer_gain = (arrows - 1) + max(0, n - 2)
        self.layer += layer_gain
        self.mag = math.log10(max(2.0, self.mag)) + 0.56 * math.log10(n + 1) + 0.32 * arrows
        return self.normalize()

    def fmt(self) -> str:
        if self.layer == 0:
            if self.mag < 1e4:
                return str(int(round(self.mag)))
            return f"{self.mag:.3e}"
        if self.layer == 1:
            return f"1e{self.mag:.2f}"
        if self.layer <= 7:
            return f"10^^{self.layer}({self.mag:.2f})"
        if self.layer <= 15:
            return f"高德纳[{self.layer - 1}]({self.mag:.2f})"
        return f"葛立恒门[L{self.layer - 15}]({self.mag:.2f})"

    def to_dict(self) -> Dict[str, float]:
        return {"layer": self.layer, "mag": self.mag}

    @staticmethod
    def from_dict(data: Dict[str, float]) -> "BigNum":
        return BigNum(int(data["layer"]), float(data["mag"])).normalize()


@dataclass(frozen=True)
class RealmConfig:
    idx: int
    name: str
    break_exp: int
    hunt_exp: int
    hunt_essence: float
    cultivate_exp: int
    cultivate_essence: float
    monster_steps: int
    unlock_stage: int
    amp_bonus: float
    treasure_bias: float


REALMS: List[RealmConfig] = [
    RealmConfig(0, "凡躯", 80, 14, 2.1, 9, 1.8, 2, 0, 0.04, 0.00),
    RealmConfig(1, "炼气", 160, 21, 3.2, 12, 2.5, 3, 1, 0.05, 0.08),
    RealmConfig(2, "筑基", 300, 31, 4.8, 16, 3.6, 4, 1, 0.07, 0.16),
    RealmConfig(3, "金丹", 520, 44, 6.9, 21, 4.9, 5, 2, 0.09, 0.25),
    RealmConfig(4, "元婴", 860, 60, 9.8, 28, 6.7, 6, 2, 0.12, 0.40),
    RealmConfig(5, "化神", 1350, 80, 13.8, 36, 9.0, 7, 3, 0.15, 0.58),
    RealmConfig(6, "炼虚", 2050, 105, 19.2, 46, 12.0, 8, 3, 0.19, 0.78),
    RealmConfig(7, "合体", 3000, 138, 26.5, 58, 15.9, 9, 4, 0.24, 0.98),
    RealmConfig(8, "大乘", 4300, 182, 36.0, 72, 20.8, 10, 4, 0.31, 1.20),
    RealmConfig(9, "无量", 6000, 240, 49.0, 88, 27.0, 11, 5, 0.40, 1.45),
]


STAGE_NAMES = [
    "加法增幅",
    "乘法增幅",
    "乘方增幅",
    "高德纳单箭头",
    "高德纳双箭头",
    "高德纳多箭头",
    "葛立恒之门",
]

REBIRTH_CAPS = [3, 6, 9]
REBIRTH_REWARD = {
    3: {"stage_gain": 1, "stage_floor": 2, "amp_mult": 1.16, "legacy": 1},
    6: {"stage_gain": 1, "stage_floor": 3, "amp_mult": 1.22, "legacy": 2},
    9: {"stage_gain": 1, "stage_floor": 5, "amp_mult": 1.30, "legacy": 3},
}


@dataclass
class Player:
    realm_idx: int
    exp: int
    cycle: int
    legacy: int
    amp_stage: int
    amp_value: float
    graham_seed: int
    attack: BigNum
    defense: BigNum
    health: BigNum
    wins: int = 0
    losses: int = 0
    story_flags: set[str] = field(default_factory=set)
    relics: Dict[str, int] = field(default_factory=dict)
    guardian_flags: set[int] = field(default_factory=set)
    guardian_failures: Dict[str, int] = field(default_factory=dict)
    demon_pressure: float = 0.0
    treasure_keys: int = 1
    key_fragments: float = 0.0
    treasure_cd: int = 0
    turn_count: int = 0
    quest_realm_idx: int = 0
    quest_hunt: int = 0
    quest_cultivate: int = 0
    quest_calm: int = 0
    quest_claimed: bool = False
    stamina: float = 72.0
    aura: float = 70.0
    fatigue: float = 0.0
    last_action: str = ""
    action_streak: int = 0
    bounty_kind: str = "狼"
    bounty_rank: str = "普通"
    bounty_need: int = 3
    bounty_done: int = 0
    bounty_tier: int = 1
    trial_realm_idx: int = 0
    trial_points: int = 0

    def current_realm(self) -> RealmConfig:
        return REALMS[self.realm_idx]

    def break_need(self) -> int:
        return self.current_realm().break_exp

    def stage_name(self) -> str:
        idx = min(self.amp_stage, len(STAGE_NAMES) - 1)
        return STAGE_NAMES[idx]

    def has_guardian_mark(self, target_realm_idx: int) -> bool:
        return target_realm_idx in self.guardian_flags

    def to_dict(self) -> Dict:
        return {
            "realm_idx": self.realm_idx,
            "exp": self.exp,
            "cycle": self.cycle,
            "legacy": self.legacy,
            "amp_stage": self.amp_stage,
            "amp_value": self.amp_value,
            "graham_seed": self.graham_seed,
            "attack": self.attack.to_dict(),
            "defense": self.defense.to_dict(),
            "health": self.health.to_dict(),
            "wins": self.wins,
            "losses": self.losses,
            "story_flags": list(self.story_flags),
            "relics": self.relics,
            "guardian_flags": list(self.guardian_flags),
            "guardian_failures": self.guardian_failures,
            "demon_pressure": self.demon_pressure,
            "treasure_keys": self.treasure_keys,
            "key_fragments": self.key_fragments,
            "treasure_cd": self.treasure_cd,
            "turn_count": self.turn_count,
            "quest_realm_idx": self.quest_realm_idx,
            "quest_hunt": self.quest_hunt,
            "quest_cultivate": self.quest_cultivate,
            "quest_calm": self.quest_calm,
            "quest_claimed": self.quest_claimed,
            "stamina": self.stamina,
            "aura": self.aura,
            "fatigue": self.fatigue,
            "last_action": self.last_action,
            "action_streak": self.action_streak,
            "bounty_kind": self.bounty_kind,
            "bounty_rank": self.bounty_rank,
            "bounty_need": self.bounty_need,
            "bounty_done": self.bounty_done,
            "bounty_tier": self.bounty_tier,
            "trial_realm_idx": self.trial_realm_idx,
            "trial_points": self.trial_points,
        }

    @staticmethod
    def from_dict(data: Dict) -> "Player":
        return Player(
            realm_idx=int(data["realm_idx"]),
            exp=int(data["exp"]),
            cycle=int(data["cycle"]),
            legacy=int(data["legacy"]),
            amp_stage=int(data["amp_stage"]),
            amp_value=float(data["amp_value"]),
            graham_seed=int(data.get("graham_seed", 0)),
            attack=BigNum.from_dict(data["attack"]),
            defense=BigNum.from_dict(data["defense"]),
            health=BigNum.from_dict(data["health"]),
            wins=int(data.get("wins", 0)),
            losses=int(data.get("losses", 0)),
            story_flags=set(data.get("story_flags", [])),
            relics=dict(data.get("relics", {})),
            guardian_flags=set(int(v) for v in data.get("guardian_flags", [])),
            guardian_failures={str(k): int(v) for k, v in dict(data.get("guardian_failures", {})).items()},
            demon_pressure=float(data.get("demon_pressure", 0.0)),
            treasure_keys=int(data.get("treasure_keys", 1)),
            key_fragments=float(data.get("key_fragments", 0.0)),
            treasure_cd=int(data.get("treasure_cd", 0)),
            turn_count=int(data.get("turn_count", 0)),
            quest_realm_idx=int(data.get("quest_realm_idx", data.get("realm_idx", 0))),
            quest_hunt=int(data.get("quest_hunt", 0)),
            quest_cultivate=int(data.get("quest_cultivate", 0)),
            quest_calm=int(data.get("quest_calm", 0)),
            quest_claimed=bool(data.get("quest_claimed", False)),
            stamina=float(data.get("stamina", 72.0)),
            aura=float(data.get("aura", 70.0)),
            fatigue=float(data.get("fatigue", 0.0)),
            last_action=str(data.get("last_action", "")),
            action_streak=int(data.get("action_streak", 0)),
            bounty_kind=str(data.get("bounty_kind", "狼")),
            bounty_rank=str(data.get("bounty_rank", "普通")),
            bounty_need=int(data.get("bounty_need", 3)),
            bounty_done=int(data.get("bounty_done", 0)),
            bounty_tier=int(data.get("bounty_tier", 1)),
            trial_realm_idx=int(data.get("trial_realm_idx", data.get("realm_idx", 0))),
            trial_points=int(data.get("trial_points", 0)),
        )


@dataclass
class Monster:
    name: str
    rank: str
    rank_mod: int
    stage: int
    attack: BigNum
    defense: BigNum
    health: BigNum
    exp_reward: int
    essence_reward: float
    shard_chance: float


MONSTER_PREFIX = ["灰", "骨", "月", "裂", "幽", "雷", "虚", "天", "噬", "寒"]
MONSTER_KIND = ["狼", "鬼", "傀", "蛇", "盗", "夜叉", "魇", "吞渊兽"]
BOUNTY_KINDS = ["狼", "鬼", "傀", "蛇", "盗", "夜叉", "魇", "吞渊兽"]
BOUNTY_RANKS = ["普通", "精英", "首领"]


def cycle_cap(cycle: int) -> int:
    if cycle < len(REBIRTH_CAPS):
        return REBIRTH_CAPS[cycle]
    return REBIRTH_CAPS[-1]


def clamp_resource(value: float) -> float:
    return clamp(value, 0.0, 100.0)


def roll_new_bounty(player: Player, rng: random.Random, keep_tier: bool = False) -> None:
    tier = player.bounty_tier if keep_tier else max(1, 1 + player.realm_idx // 2 + player.cycle)
    rank_roll = rng.random() + 0.08 * tier
    if rank_roll < 0.65:
        rank = "普通"
    elif rank_roll < 1.15:
        rank = "精英"
    else:
        rank = "首领"
    need = 2 + player.realm_idx // 2 + (1 if rank != "普通" else 0) + (1 if rank == "首领" else 0)

    player.bounty_tier = tier
    player.bounty_kind = rng.choice(BOUNTY_KINDS)
    player.bounty_rank = rank
    player.bounty_need = need
    player.bounty_done = 0


def action_rhythm(player: Player, action_name: str) -> Tuple[float, List[str]]:
    if player.last_action == action_name:
        player.action_streak += 1
    else:
        player.last_action = action_name
        player.action_streak = 1

    penalty = max(0.0, (player.action_streak - 2) * 0.16)
    penalty = clamp(penalty, 0.0, 0.58)
    lines: List[str] = []
    if penalty > 0:
        modify_pressure(player, 1.5 + 1.0 * penalty)
        lines.append(
            f"[节奏惩罚] 连续执行“{action_name}”{player.action_streak}次，收益倍率 {1.0 - penalty:.2f}。"
        )
    return 1.0 - penalty, lines


def spend_resources(player: Player, stamina: float = 0.0, aura: float = 0.0, fatigue_add: float = 0.0) -> Tuple[float, List[str]]:
    msgs: List[str] = []
    stamina = max(0.0, stamina)
    aura = max(0.0, aura)
    ratio_s = 1.0 if stamina <= 0 else min(1.0, player.stamina / stamina)
    ratio_a = 1.0 if aura <= 0 else min(1.0, player.aura / aura)
    efficiency = min(ratio_s, ratio_a)

    if stamina > 0:
        spent_s = min(player.stamina, stamina)
        player.stamina = clamp_resource(player.stamina - spent_s)
    if aura > 0:
        spent_a = min(player.aura, aura)
        player.aura = clamp_resource(player.aura - spent_a)

    if efficiency < 0.999:
        msgs.append(f"[资源不足] 体力/灵气不足，本次效率降为 {efficiency:.2f}。")
        modify_pressure(player, 2.0 + 6.0 * (1.0 - efficiency))

    fatigue_gain = fatigue_add * (1.0 + (1.0 - efficiency) * 0.9)
    player.fatigue = clamp_resource(player.fatigue + fatigue_gain)
    return efficiency, msgs


def recover_resources(player: Player, stamina: float = 0.0, aura: float = 0.0, fatigue_reduce: float = 0.0) -> None:
    player.stamina = clamp_resource(player.stamina + max(0.0, stamina))
    player.aura = clamp_resource(player.aura + max(0.0, aura))
    player.fatigue = clamp_resource(player.fatigue - max(0.0, fatigue_reduce))


def fatigue_growth_factor(player: Player) -> float:
    return clamp(1.0 - max(0.0, player.fatigue - 20.0) * 0.006, 0.45, 1.0)


def pressure_growth_factor(player: Player) -> float:
    p = player.demon_pressure
    base = clamp(1.0 - max(0.0, p - 35.0) * 0.008, 0.52, 1.0)
    return base * fatigue_growth_factor(player)


def pressure_enemy_buff(player: Player) -> float:
    p = player.demon_pressure
    fatigue_term = max(0.0, player.fatigue - 40.0) * 0.008
    return clamp(1.0 + max(0.0, p - 40.0) * 0.012 + fatigue_term, 1.0, 2.10)


def modify_pressure(player: Player, delta: float) -> None:
    player.demon_pressure = clamp(player.demon_pressure + delta, 0.0, 100.0)


def add_key_fragments(player: Player, amount: float) -> int:
    if amount <= 0:
        return 0
    player.key_fragments += amount
    gained = 0
    while player.key_fragments >= 1.0 and player.treasure_keys < 3:
        player.key_fragments -= 1.0
        player.treasure_keys += 1
        gained += 1
    if player.treasure_keys >= 3:
        player.key_fragments = min(player.key_fragments, 0.99)
    return gained


def advance_turn(player: Player, fragment_gain: float = 0.0) -> List[str]:
    player.turn_count += 1
    out: List[str] = []
    if player.treasure_cd > 0:
        player.treasure_cd -= 1
    gained = add_key_fragments(player, fragment_gain)
    if gained > 0:
        out.append(f"[系统] 你凝聚了 {gained} 枚寻宝令（当前 {player.treasure_keys}/3）。")
    return out


def quest_requirements(realm_idx: int) -> Dict[str, int]:
    return {
        "hunt": 3 + realm_idx,
        "cultivate": 2 + realm_idx // 2,
        "calm": 1 + realm_idx // 3,
    }


def trial_need(realm_idx: int) -> int:
    return 4 + realm_idx * 2


def reset_realm_trial(player: Player) -> None:
    player.trial_realm_idx = player.realm_idx
    player.trial_points = 0


def ensure_realm_trial(player: Player) -> None:
    if player.trial_realm_idx != player.realm_idx:
        reset_realm_trial(player)


def add_trial_points(player: Player, amount: int) -> int:
    ensure_realm_trial(player)
    cap = trial_need(player.realm_idx) + 6 + player.cycle * 2
    old = player.trial_points
    player.trial_points = int(clamp(player.trial_points + amount, 0, cap))
    return player.trial_points - old


def reset_realm_quest(player: Player) -> None:
    player.quest_realm_idx = player.realm_idx
    player.quest_hunt = 0
    player.quest_cultivate = 0
    player.quest_calm = 0
    player.quest_claimed = False


def ensure_realm_quest(player: Player) -> None:
    if player.quest_realm_idx != player.realm_idx:
        reset_realm_quest(player)


def quest_status_lines(player: Player) -> List[str]:
    ensure_realm_quest(player)
    ensure_realm_trial(player)
    req = quest_requirements(player.realm_idx)
    trial_req = trial_need(player.realm_idx)
    state = "已完成" if player.quest_claimed else "进行中"
    return [
        f"[宗门任务] 状态: {state} | 当前境界: {player.current_realm().name}",
        f"[宗门任务] 狩猎 {player.quest_hunt}/{req['hunt']} | 修炼 {player.quest_cultivate}/{req['cultivate']} | 调息 {player.quest_calm}/{req['calm']}",
        (
            f"[宗门任务] 当前悬赏：{player.bounty_rank}{player.bounty_kind} {player.bounty_done}/{player.bounty_need}"
            f" | 破境资粮 {player.trial_points}/{trial_req}"
        ),
    ]


def maybe_complete_quest(player: Player) -> List[str]:
    ensure_realm_quest(player)
    ensure_realm_trial(player)
    req = quest_requirements(player.realm_idx)
    if player.quest_claimed:
        return []
    if player.quest_hunt < req["hunt"] or player.quest_cultivate < req["cultivate"] or player.quest_calm < req["calm"]:
        return []

    player.quest_claimed = True
    realm = player.current_realm()
    reward_exp = int(realm.hunt_exp * 1.8 * (1.0 + 0.10 * player.cycle))
    reward_essence = realm.cultivate_essence * 1.35
    player.exp += reward_exp
    modify_pressure(player, -10.0)
    player.amp_value += 0.03 + 0.01 * realm.idx
    recover_resources(player, stamina=12.0, aura=14.0, fatigue_reduce=10.0)
    key_gain = add_key_fragments(player, 0.80 + 0.05 * realm.idx)
    trial_gain = add_trial_points(player, 2 + realm.idx // 2)
    lines = [
        f"[任务完成] 宗门任务达成，获得修为 +{reward_exp}。",
        "[任务完成] " + gain_stats(player, reward_essence, increase_amp=False),
        f"[任务完成] 增幅值额外 +{0.03 + 0.01 * realm.idx:.2f}，心魔压强 -10。",
    ]
    if trial_gain > 0:
        lines.append(f"[任务完成] 破境资粮 +{trial_gain}。")
    if key_gain > 0:
        lines.append(f"[任务完成] 额外凝聚寻宝令 {key_gain} 枚。")
    return lines


def apply_growth(stat: BigNum, gain: float, stage: int, amp_value: float) -> None:
    scaled = max(0.01, gain) * max(0.15, amp_value)
    stage = max(0, stage)
    if stage >= 2 and stat.layer == 0 and stat.mag < 1.2:
        stat.add(1.0 + 0.30 * scaled)
    if stage >= 3 and stat.layer == 0 and stat.mag < 2.0:
        stat.add(1.0)
    if stage == 0:
        stat.add(scaled)
    elif stage == 1:
        stat.mul(1.0 + 0.18 * scaled)
    elif stage == 2:
        stat.pow(1.0 + 0.064 * scaled * math.sqrt(max(0.5, amp_value)))
    elif stage == 3:
        n = 2 + int((scaled + 1.0) ** 0.42)
        stat.hyper(1, n)
    elif stage == 4:
        n = 2 + int(math.log10(1.0 + scaled) * 2.0)
        stat.hyper(2, n)
    else:
        arrows = 2 + (stage - 4)
        n = 2 + int(math.log10(1.0 + scaled) * (1.0 + 0.18 * arrows))
        stat.hyper(arrows, n)


def gain_stats(player: Player, essence: float, increase_amp: bool = True) -> str:
    growth_factor = pressure_growth_factor(player)
    final_essence = essence * growth_factor
    apply_growth(player.attack, final_essence * 1.00, player.amp_stage, player.amp_value)
    apply_growth(player.defense, final_essence * 0.90, player.amp_stage, player.amp_value)
    apply_growth(player.health, final_essence * 1.12, player.amp_stage, player.amp_value)
    amp_delta = 0.0
    if increase_amp:
        amp_delta = 0.0075 * math.sqrt(max(0.01, final_essence)) * (1.0 + player.realm_idx * 0.03)
        player.amp_value += amp_delta
    return (
        f"灵蕴 {final_essence:.2f}(原始{essence:.2f}) -> "
        f"攻 {player.attack.fmt()} 防 {player.defense.fmt()} 血 {player.health.fmt()} 增幅值+{amp_delta:.3f}"
    )


def make_player(rng: random.Random) -> Player:
    player = Player(
        realm_idx=0,
        exp=0,
        cycle=0,
        legacy=0,
        amp_stage=0,
        amp_value=1.0,
        graham_seed=0,
        attack=BigNum.from_value(rng.randint(1, 9)),
        defense=BigNum.from_value(rng.randint(1, 9)),
        health=BigNum.from_value(rng.randint(1, 9)),
    )
    reset_realm_quest(player)
    reset_realm_trial(player)
    roll_new_bounty(player, rng)
    return player


def generate_monster(player: Player, rng: random.Random, forced_rank_mod: int | None = None) -> Monster:
    realm = player.current_realm()
    roll = rng.random()
    if forced_rank_mod is not None:
        rank_mod = forced_rank_mod
    elif roll < 0.66:
        rank_mod = 0
    elif roll < 0.92:
        rank_mod = 1
    else:
        rank_mod = 2

    rank_name = ["普通", "精英", "首领"][rank_mod]
    name = f"{rng.choice(MONSTER_PREFIX)}{rng.choice(MONSTER_KIND)}"

    enemy_pressure = pressure_enemy_buff(player)
    atk = BigNum.from_value((2.9 + player.realm_idx * 1.3 + rank_mod * 1.8 + rng.uniform(0.0, 1.5)) * enemy_pressure)
    deff = BigNum.from_value((2.8 + player.realm_idx * 1.2 + rank_mod * 1.6 + rng.uniform(0.0, 1.5)) * enemy_pressure)
    hp = BigNum.from_value((6.0 + player.realm_idx * 2.0 + rank_mod * 2.2 + rng.uniform(0.0, 2.0)) * enemy_pressure)

    stage_base = max(0, realm.unlock_stage + player.cycle // 2)
    stage = min(player.amp_stage + 1, stage_base + rank_mod)
    steps = realm.monster_steps + player.cycle + rank_mod * 2 + rng.randint(1, 3)
    amp = (0.62 + 0.16 * player.realm_idx + 0.22 * player.cycle) * (1.0 + 0.22 * rank_mod) * enemy_pressure
    for _ in range(steps):
        pulse = rng.uniform(0.88, 1.32) * (1.0 + 0.08 * player.realm_idx)
        apply_growth(atk, pulse * 1.00, stage, amp * 0.96)
        apply_growth(deff, pulse * 0.95, stage, amp * 0.96)
        apply_growth(hp, pulse * 1.18, stage, amp * 0.96)

    exp_reward = int(realm.hunt_exp * (1.0 + 0.42 * rank_mod) * (1.0 + 0.15 * player.cycle))
    essence_reward = realm.hunt_essence * (1.0 + 0.45 * rank_mod) * (1.0 + 0.10 * player.cycle)
    shard_chance = clamp(0.02 + 0.03 * rank_mod + 0.008 * player.realm_idx, 0.02, 0.50)
    return Monster(name, rank_name, rank_mod, stage, atk, deff, hp, exp_reward, essence_reward, shard_chance)


def generate_guardian(player: Player, rng: random.Random, target_realm_idx: int) -> Monster:
    target = REALMS[target_realm_idx]
    name = f"{target.name}守关者"
    rank_name = "天关强敌"
    rank_mod = 3
    fail_layers = min(5, int(player.guardian_failures.get(str(target_realm_idx), 0)))
    suppress = 1.0 - 0.07 * fail_layers

    pressure = pressure_enemy_buff(player)
    atk = BigNum.from_value((5.0 + target.idx * 1.9 + player.cycle * 1.4) * pressure * suppress)
    deff = BigNum.from_value((5.2 + target.idx * 2.0 + player.cycle * 1.5) * pressure * suppress)
    hp = BigNum.from_value((9.0 + target.idx * 2.8 + player.cycle * 2.2) * pressure * suppress)

    stage = max(target.unlock_stage, min(player.amp_stage + 1, target.unlock_stage + 1 + player.cycle // 2))
    steps = max(4, target.monster_steps + 4 + player.cycle * 2 - fail_layers)
    amp = (0.82 + 0.17 * target.idx + 0.24 * player.cycle) * pressure * (1.0 - 0.05 * fail_layers)
    for i in range(steps):
        pulse = (1.06 + 0.02 * math.sin(i + target.idx)) * (1.0 + 0.085 * target.idx)
        apply_growth(atk, pulse * 1.02, stage, amp)
        apply_growth(deff, pulse * 1.00, stage, amp)
        apply_growth(hp, pulse * 1.26, stage, amp)

    exp_reward = int(target.hunt_exp * 2.2 * (1.0 + 0.20 * player.cycle))
    essence_reward = target.hunt_essence * 2.1 * (1.0 + 0.16 * player.cycle)
    shard_chance = 0.65
    return Monster(name, rank_name, rank_mod, stage, atk, deff, hp, exp_reward, essence_reward, shard_chance)


def calc_damage(att: BigNum, deff: BigNum, hp: BigNum, turn: int, rng: random.Random, ratio: float = 1.0) -> int:
    pressure = clamp(att.score() - deff.score(), -60.0, 60.0)
    swing = math.exp(pressure * 0.055)
    guard = 1.0 + max(0.0, hp.score() - att.score()) * 0.013
    variance = rng.uniform(0.90, 1.10)
    raw = (6.2 + turn * 0.68) * swing * variance / guard
    raw *= ratio
    return int(clamp(round(raw), 1, 64))


def battle(player: Player, monster: Monster, rng: random.Random) -> Tuple[bool, List[str]]:
    p_focus = 100
    m_focus = 100
    logs: List[str] = []

    p_mod = pressure_growth_factor(player)
    m_mod = pressure_enemy_buff(player)
    if player.demon_pressure >= 70:
        logs.append("[心魔] 你的识海躁动，出手时有概率走火。")

    for turn in range(1, 31):
        if player.demon_pressure >= 70 and rng.random() < 0.22:
            backlash = rng.randint(3, 8)
            p_focus -= backlash
            logs.append(f"回合{turn:02d} | 心魔反噬，你额外损失 {backlash} 点专注。")
            if p_focus <= 0:
                logs.append("你被心魔拖入幻境，战斗失败。")
                return False, logs

        p_hit = calc_damage(player.attack, monster.defense, monster.health, turn, rng, p_mod)
        m_focus -= p_hit
        logs.append(f"回合{turn:02d} | 你对{monster.name}造成 {p_hit:2d} 点专注伤害。")
        if m_focus <= 0:
            logs.append(f"{monster.name}被你击溃。")
            return True, logs

        m_hit = calc_damage(monster.attack, player.defense, player.health, turn, rng, m_mod)
        p_focus -= m_hit
        logs.append(f"回合{turn:02d} | {monster.name}对你造成 {m_hit:2d} 点专注伤害。")
        if p_focus <= 0:
            logs.append("经脉震裂，你暂时落败。")
            return False, logs

    return p_focus >= m_focus, logs + ["战斗超时，按剩余专注判定胜负。"]


def check_story(player: Player) -> List[str]:
    out: List[str] = []
    gates = [
        ("s1", player.realm_idx >= 2, "外门老执事告诉你：残卷属于失落的《无穷道典》。"),
        ("s2", player.amp_stage >= 2, "你悟到“增长方式”本身也能修炼。"),
        ("s3", player.cycle >= 1, "第一次归零后，你开始记得未来的碎片。"),
        ("s4", player.cycle >= 1 and player.realm_idx >= 4, "星海遗迹里，你看见怪物是失控大数的化身。"),
        ("s5", player.cycle >= 2, "你听见虚无祖名号：它能让一切数值归零。"),
        ("s6", player.graham_seed >= 1, "葛立恒之门开启，符号法则压过普通算术。"),
        ("s7", player.cycle >= 3 and player.amp_stage >= 6, "你可在骨血中刻下跨宇宙常量。"),
    ]
    for key, cond, text in gates:
        if cond and key not in player.story_flags:
            player.story_flags.add(key)
            out.append(f"[剧情] {text}")
    return out


def apply_rebirth(player: Player, cap: int, rng: random.Random) -> List[str]:
    reward = REBIRTH_REWARD[cap]
    messages = [f"[归零] 你触及本轮上限境界 {REALMS[cap].name}，天道重铸开始。"]

    player.cycle += 1
    player.legacy += reward["legacy"]
    player.amp_stage = max(player.amp_stage, reward["stage_floor"])
    player.amp_stage += reward["stage_gain"]
    player.amp_value *= reward["amp_mult"]

    if cap >= 9:
        player.graham_seed += 1
        player.amp_stage += player.graham_seed // 2
        messages.append(f"[归零] 葛立恒种子 +1 -> {player.graham_seed}")

    player.realm_idx = 0
    player.exp = 0
    player.guardian_flags.clear()
    player.guardian_failures.clear()
    player.demon_pressure = clamp(player.demon_pressure * 0.45, 0.0, 40.0)
    player.treasure_keys = 1
    player.key_fragments = 0.0
    player.treasure_cd = 0
    player.stamina = 76.0
    player.aura = 76.0
    player.fatigue = 8.0
    player.last_action = ""
    player.action_streak = 0

    player.attack = BigNum.from_value(rng.randint(1, 9))
    player.defense = BigNum.from_value(rng.randint(1, 9))
    player.health = BigNum.from_value(rng.randint(1, 9))

    pulses = max(1, player.legacy + player.cycle)
    for i in range(pulses):
        pulse = 0.55 + 0.08 * i + 0.30 * player.cycle
        apply_growth(player.attack, pulse * 1.0, player.amp_stage, player.amp_value * 0.67)
        apply_growth(player.defense, pulse * 0.9, player.amp_stage, player.amp_value * 0.67)
        apply_growth(player.health, pulse * 1.15, player.amp_stage, player.amp_value * 0.67)
    reset_realm_quest(player)
    reset_realm_trial(player)
    roll_new_bounty(player, rng)

    messages.append(
        f"[归零] 新起点: 攻 {player.attack.fmt()} 防 {player.defense.fmt()} 血 {player.health.fmt()} | "
        f"增幅阶 {player.amp_stage}({player.stage_name()}) 增幅值 {player.amp_value:.3f}"
    )
    return messages


def action_hunt(player: Player, rng: random.Random) -> List[str]:
    ensure_realm_quest(player)
    ensure_realm_trial(player)
    rhythm_factor, rhythm_lines = action_rhythm(player, "狩猎")
    stamina_cost = 13.0 + 1.6 * player.realm_idx
    aura_cost = 4.0 + 0.8 * player.realm_idx
    resource_factor, resource_lines = spend_resources(player, stamina=stamina_cost, aura=aura_cost, fatigue_add=6.0)
    action_factor = max(0.35, rhythm_factor * (0.65 + 0.35 * resource_factor))

    monster = generate_monster(player, rng)
    lines = [
        f"[狩猎] {monster.rank} {monster.name} | 怪物增幅阶 {monster.stage} | "
        f"攻 {monster.attack.fmt()} 防 {monster.defense.fmt()} 血 {monster.health.fmt()}"
    ]
    lines.extend(rhythm_lines)
    lines.extend(resource_lines)
    win, logs = battle(player, monster, rng)
    lines.extend(logs[:8])
    if len(logs) > 8:
        lines.append("...（战斗日志已折叠）")
        lines.append(logs[-1])

    if win:
        player.wins += 1
        player.quest_hunt += 1
        reward_exp = int(monster.exp_reward * action_factor)
        reward_essence = monster.essence_reward * action_factor
        player.exp += reward_exp
        lines.append(f"[胜利] 修为 +{reward_exp}（效率{action_factor:.2f}）")
        lines.append("[胜利] " + gain_stats(player, reward_essence))
        modify_pressure(player, 5.5 + 1.5 * monster.rank_mod)
        if rng.random() < monster.shard_chance:
            shard = 0.03 + 0.02 * min(monster.rank_mod, 2)
            player.amp_value += shard
            lines.append(f"[掉落] 道则碎晶：增幅值 +{shard:.2f}")
        trial_gain = 1 + monster.rank_mod
        if action_factor < 0.56:
            trial_gain = max(1, trial_gain - 1)
        gained = add_trial_points(player, trial_gain)
        if gained > 0:
            lines.append(f"[历练] 破境资粮 +{gained}（当前 {player.trial_points}/{trial_need(player.realm_idx)}）。")
        recover_resources(player, stamina=8.0 + 2.0 * monster.rank_mod, aura=4.0 + 1.2 * monster.rank_mod, fatigue_reduce=3.0)
        if player.bounty_rank == monster.rank and player.bounty_kind in monster.name:
            player.bounty_done += 1
            lines.append(
                f"[悬赏推进] 击败目标 {monster.rank}{player.bounty_kind}，进度 {player.bounty_done}/{player.bounty_need}。"
            )
            if player.bounty_done >= player.bounty_need:
                tier = player.bounty_tier
                bounty_exp = int(player.current_realm().hunt_exp * (1.6 + 0.30 * tier))
                bounty_ess = player.current_realm().hunt_essence * (1.35 + 0.22 * tier)
                player.exp += bounty_exp
                lines.append(f"[悬赏完成] 修为 +{bounty_exp}")
                lines.append("[悬赏完成] " + gain_stats(player, bounty_ess))
                amp_gain = 0.03 + 0.01 * tier
                player.amp_value += amp_gain
                key_gain = add_key_fragments(player, 0.45 + 0.05 * tier)
                lines.append(f"[悬赏完成] 增幅值 +{amp_gain:.2f}")
                bounty_trial = add_trial_points(player, 2 + tier // 2)
                if bounty_trial > 0:
                    lines.append(f"[悬赏完成] 破境资粮 +{bounty_trial}。")
                if key_gain > 0:
                    lines.append(f"[悬赏完成] 凝聚寻宝令 {key_gain} 枚。")
                roll_new_bounty(player, rng)
                lines.append(
                    f"[新悬赏] 击败 {player.bounty_need} 个「{player.bounty_rank}{player.bounty_kind}」。"
                )
        lines.extend(advance_turn(player, fragment_gain=0.20 + 0.04 * monster.rank_mod))
    else:
        player.losses += 1
        penalty = int(player.break_need() * (0.08 + 0.06 * (1.0 - action_factor)))
        player.exp = max(0, player.exp - penalty)
        consolation = max(0.45, monster.essence_reward * 0.24 * action_factor)
        lines.append(f"[落败] 修为 -{penalty}")
        lines.append("[落败] " + gain_stats(player, consolation, increase_amp=False))
        modify_pressure(player, 10.0 + 2.0 * monster.rank_mod)
        lost = add_trial_points(player, -1)
        if lost < 0:
            lines.append(f"[落败] 破境资粮 {lost}（当前 {player.trial_points}/{trial_need(player.realm_idx)}）。")
        recover_resources(player, stamina=3.0, aura=2.0, fatigue_reduce=1.0)
        lines.extend(advance_turn(player, fragment_gain=0.12))

    lines.extend(maybe_complete_quest(player))
    lines.extend(check_story(player))
    return lines


def action_cultivate(player: Player, rng: random.Random) -> List[str]:
    ensure_realm_quest(player)
    ensure_realm_trial(player)
    rhythm_factor, rhythm_lines = action_rhythm(player, "修炼")
    realm = player.current_realm()
    player.quest_cultivate += 1
    aura_cost = 20.0 + 2.2 * player.realm_idx
    stamina_cost = 5.0 + 0.8 * player.realm_idx
    resource_factor, resource_lines = spend_resources(player, stamina=stamina_cost, aura=aura_cost, fatigue_add=11.0)
    overheat = max(0, player.action_streak - 2)
    overheat_factor = clamp(1.0 - 0.22 * overheat, 0.08, 1.0)
    action_factor = max(0.06, rhythm_factor * resource_factor * fatigue_growth_factor(player) * overheat_factor)

    if resource_factor < 0.45:
        backlash = int(realm.cultivate_exp * (0.80 + 0.15 * player.realm_idx))
        player.exp = max(0, player.exp - backlash)
        modify_pressure(player, 10.0)
        lines = ["[闭关失败] 灵气与体力不足，修炼反噬。", f"[闭关失败] 修为 -{backlash}，心魔压强上升。"]
        lines.extend(rhythm_lines)
        lines.extend(resource_lines)
        lines.append("[闭关失败] 建议先调息或狩猎恢复资源。")
        add_trial_points(player, -1)
        recover_resources(player, stamina=2.5, aura=3.5, fatigue_reduce=0.0)
        lines.extend(advance_turn(player, fragment_gain=0.14 + 0.02 * player.realm_idx))
        lines.extend(check_story(player))
        return lines

    backlash_chance = clamp(
        0.04
        + 0.12 * max(0, player.action_streak - 2)
        + 0.005 * max(0.0, player.fatigue - 35.0)
        + 0.003 * max(0.0, player.demon_pressure - 30.0),
        0.04,
        0.78,
    )
    if rng.random() < backlash_chance:
        backlash = int(realm.cultivate_exp * (1.0 + 0.22 * player.realm_idx + 0.35 * overheat))
        player.exp = max(0, player.exp - backlash)
        modify_pressure(player, 8.0 + 2.0 * overheat)
        lines = ["[走火] 你强行冲关导致灵气逆冲。", f"[走火] 修为 -{backlash}，风险率 {backlash_chance:.0%}。"]
        lines.extend(rhythm_lines)
        lines.extend(resource_lines)
        add_trial_points(player, -1)
        if overheat >= 2 and rng.random() < 0.55:
            intruder = generate_monster(player, rng, forced_rank_mod=1 if overheat == 2 else 2)
            lines.append(f"[异象] 闭关波动引来 {intruder.rank}{intruder.name}。")
            win, logs = battle(player, intruder, rng)
            lines.extend(logs[:6])
            if win:
                counter_exp = int(intruder.exp_reward * 0.55)
                player.exp += counter_exp
                lines.append(f"[反杀] 你借劫淬体，修为回补 +{counter_exp}。")
                gain = add_trial_points(player, 1 + intruder.rank_mod)
                if gain > 0:
                    lines.append(f"[反杀] 破境资粮 +{gain}。")
            else:
                loss = int(player.break_need() * 0.06)
                player.exp = max(0, player.exp - loss)
                lines.append(f"[异象败退] 再损修为 -{loss}。")
                modify_pressure(player, 6.0)
        recover_resources(player, stamina=2.5, aura=4.0, fatigue_reduce=0.0)
        lines.extend(advance_turn(player, fragment_gain=0.16 + 0.02 * player.realm_idx))
        lines.extend(check_story(player))
        return lines

    exp_gain = int(
        realm.cultivate_exp * (1.0 + 0.11 * player.cycle) * rng.uniform(0.88, 1.10) * action_factor
    )
    essence = realm.cultivate_essence * (1.0 + 0.08 * player.realm_idx) * rng.uniform(0.90, 1.06) * action_factor
    player.exp += exp_gain
    lines = [f"[修炼] 修为 +{exp_gain}（效率{action_factor:.2f}）", "[修炼] " + gain_stats(player, essence)]
    lines.extend(rhythm_lines)
    lines.extend(resource_lines)
    if overheat > 0:
        lines.append(f"[火候过热] 连续闭关导致效率额外衰减至 {overheat_factor:.2f}。")

    if rng.random() < 0.14:
        insight = (0.04 + 0.015 * player.realm_idx) * (0.75 + 0.25 * action_factor)
        player.amp_value += insight
        lines.append(f"[顿悟] 增幅值 +{insight:.2f}")

    modify_pressure(player, -8.0)
    recover_resources(player, stamina=4.0, aura=0.0, fatigue_reduce=0.0)
    lines.extend(advance_turn(player, fragment_gain=0.30 + 0.03 * player.realm_idx))
    lines.extend(maybe_complete_quest(player))
    lines.extend(check_story(player))
    return lines


def action_calm(player: Player) -> List[str]:
    ensure_realm_quest(player)
    rhythm_factor, rhythm_lines = action_rhythm(player, "调息")
    lines = ["[调息] 你收束神识，压制心魔。"]
    lines.extend(rhythm_lines)
    player.quest_calm += 1
    modify_pressure(player, -18.0)
    gain = 0.7 + 0.2 * player.cycle
    lines.append(f"[调息] 寻宝令碎片 +{gain:.2f}")
    recover_resources(player, stamina=24.0 + 3.0 * player.cycle, aura=28.0 + 2.5 * player.cycle, fatigue_reduce=26.0)
    if rhythm_factor < 0.90:
        lines.append("[调息] 连续调息效果衰减，建议穿插狩猎或修炼。")
    lines.extend(advance_turn(player, fragment_gain=gain))
    lines.extend(maybe_complete_quest(player))
    return lines


def apply_relic(player: Player, relic: str, rng: random.Random) -> str:
    player.relics[relic] = player.relics.get(relic, 0) + 1
    if relic == "剑骨":
        apply_growth(player.attack, 6.8 + 1.3 * player.realm_idx, player.amp_stage, player.amp_value)
        return "剑骨共鸣：攻击路径重塑。"
    if relic == "玄龟甲":
        apply_growth(player.defense, 6.6 + 1.2 * player.realm_idx, player.amp_stage, player.amp_value)
        return "玄龟甲固化：防御稳定。"
    if relic == "龙髓":
        apply_growth(player.health, 8.5 + 1.5 * player.realm_idx, player.amp_stage, player.amp_value)
        return "龙髓涌动：生命拓展。"
    if relic == "道矩":
        delta = 0.13 + 0.03 * player.cycle
        player.amp_value += delta
        return f"道矩重排：增幅值 +{delta:.2f}。"
    if relic == "箭经":
        if rng.random() < 0.35:
            player.amp_stage += 1
            return "箭经破译：增幅阶 +1。"
        player.amp_value += 0.16
        return "箭经未全解：增幅值 +0.16。"
    if relic == "葛立恒残片":
        player.graham_seed += 1
        player.amp_stage += 1
        player.amp_value += 0.26
        return "残片共鸣：增幅阶 +1，增幅值 +0.26，葛立恒种子 +1。"
    return "未知遗宝，没有效果。"


def action_treasure(player: Player, rng: random.Random) -> List[str]:
    ensure_realm_quest(player)
    ensure_realm_trial(player)
    rhythm_factor, rhythm_lines = action_rhythm(player, "寻宝")
    lines: List[str] = []
    if player.treasure_cd > 0:
        lines.append(f"[寻宝] 你上次探索惊动了天机，需冷却 {player.treasure_cd} 回合。")
        return lines
    if player.treasure_keys <= 0:
        lines.append("[寻宝] 没有寻宝令。请通过修炼、狩猎或调息积攒。")
        return lines
    resource_factor, resource_lines = spend_resources(
        player,
        stamina=9.0 + 1.0 * player.realm_idx,
        aura=16.0 + 1.8 * player.realm_idx,
        fatigue_add=8.0,
    )
    action_factor = max(0.35, rhythm_factor * (0.7 + 0.3 * resource_factor))

    player.treasure_keys -= 1
    player.treasure_cd = 2

    realm = player.current_realm()
    quality = rng.random() + realm.treasure_bias - 0.10 * pressure_enemy_buff(player)
    lines.append(f"[寻宝] 你消耗1枚寻宝令，探索质量={quality:.2f}")
    lines.extend(rhythm_lines)
    lines.extend(resource_lines)

    if quality < 0.80:
        exp_gain = int(realm.hunt_exp * 0.45 * (1.0 + max(0.0, quality)) * action_factor)
        essence = realm.hunt_essence * 0.55 * (1.0 + 0.5 * max(0.0, quality)) * action_factor
        player.exp += exp_gain
        lines.append(f"[寻宝] 仅找到残破补给：修为 +{exp_gain}")
        lines.append("[寻宝] " + gain_stats(player, essence))
        gain = add_trial_points(player, 1)
        if gain > 0:
            lines.append(f"[寻宝] 破境资粮 +{gain}。")
    elif quality < 1.25:
        relic = rng.choice(["剑骨", "玄龟甲", "龙髓", "道矩"])
        lines.append(f"[寻宝] 获得遗宝：{relic}")
        lines.append("[遗宝] " + apply_relic(player, relic, rng))
        gain = add_trial_points(player, 1)
        if gain > 0:
            lines.append(f"[寻宝] 破境资粮 +{gain}。")
    elif quality < 1.55:
        lines.append("[寻宝] 阵法塌陷，天关守卫降临。")
        monster = generate_monster(player, rng, forced_rank_mod=2)
        win, logs = battle(player, monster, rng)
        lines.extend(logs[:6])
        if win:
            reward_exp = int(monster.exp_reward * 1.25 * action_factor)
            player.exp += reward_exp
            lines.append(f"[寻宝胜] 修为 +{reward_exp}")
            lines.append("[寻宝胜] " + gain_stats(player, monster.essence_reward * 1.35 * action_factor))
            relic = rng.choice(["箭经", "道矩"])
            lines.append("[遗宝] " + apply_relic(player, relic, rng))
            gain = add_trial_points(player, 3)
            if gain > 0:
                lines.append(f"[寻宝胜] 破境资粮 +{gain}。")
            modify_pressure(player, 11.0)
        else:
            player.exp = max(0, player.exp - int(player.break_need() * 0.14))
            lines.append("[寻宝败] 负伤撤离，修为受损。")
            lost = add_trial_points(player, -1)
            if lost < 0:
                lines.append(f"[寻宝败] 破境资粮 {lost}。")
            modify_pressure(player, 14.0)
    else:
        relic = rng.choice(["箭经", "葛立恒残片"])
        lines.append(f"[寻宝] 你打开了神话宝库：{relic}")
        lines.append("[遗宝] " + apply_relic(player, relic, rng))
        essence = realm.hunt_essence * 1.55 * action_factor
        lines.append("[寻宝] " + gain_stats(player, essence))
        gain = add_trial_points(player, 2)
        if gain > 0:
            lines.append(f"[寻宝] 破境资粮 +{gain}。")
        modify_pressure(player, 13.5)

    recover_resources(player, stamina=2.0, aura=2.0, fatigue_reduce=2.0)
    lines.extend(advance_turn(player, fragment_gain=0.06))
    lines.extend(check_story(player))
    return lines


def action_challenge(player: Player, rng: random.Random) -> List[str]:
    ensure_realm_quest(player)
    ensure_realm_trial(player)
    rhythm_factor, rhythm_lines = action_rhythm(player, "守关")
    lines: List[str] = []
    if player.realm_idx >= len(REALMS) - 1:
        lines.append("[守关] 你已到达当前已设计的最高境界，无需挑战。")
        return lines

    target_realm = player.realm_idx + 1
    if not player.quest_claimed:
        lines.append("[守关] 你尚未完成本境宗门任务，无法挑战天关。")
        lines.extend(quest_status_lines(player))
        return lines

    trial_req = trial_need(player.realm_idx)
    challenge_req = max(2, int(math.ceil(trial_req * 0.55)))
    if player.trial_points < challenge_req:
        lines.append(
            f"[守关] 破境资粮不足：需至少 {challenge_req}，当前 {player.trial_points}。"
        )
        lines.append("[守关] 请通过狩猎、悬赏或寻宝积累资粮。")
        return lines

    if player.has_guardian_mark(target_realm):
        lines.append(f"[守关] 你已击败过 {REALMS[target_realm].name} 守关者。")
        return lines

    resource_factor, resource_lines = spend_resources(
        player,
        stamina=18.0 + 1.8 * player.realm_idx,
        aura=14.0 + 1.5 * player.realm_idx,
        fatigue_add=10.0,
    )
    action_factor = max(0.40, rhythm_factor * (0.7 + 0.3 * resource_factor))
    fail_layers = min(5, int(player.guardian_failures.get(str(target_realm), 0)))
    guardian = generate_guardian(player, rng, target_realm)
    lines.append(
        f"[守关] {guardian.rank} {guardian.name} | 增幅阶 {guardian.stage} | 压制层 {fail_layers}/5 | "
        f"攻 {guardian.attack.fmt()} 防 {guardian.defense.fmt()} 血 {guardian.health.fmt()}"
    )
    lines.extend(rhythm_lines)
    lines.extend(resource_lines)
    win, logs = battle(player, guardian, rng)
    lines.extend(logs[:9])
    if len(logs) > 9:
        lines.append("...（战斗日志已折叠）")
        lines.append(logs[-1])

    if win:
        player.guardian_flags.add(target_realm)
        player.guardian_failures.pop(str(target_realm), None)
        reward_exp = int(guardian.exp_reward * 0.75 * action_factor)
        player.exp += reward_exp
        lines.append(f"[守关胜] 获得破境印记：{REALMS[target_realm].name}")
        lines.append(f"[守关胜] 修为 +{reward_exp}")
        lines.append("[守关胜] " + gain_stats(player, guardian.essence_reward * 0.95 * action_factor, increase_amp=False))
        if rng.random() < guardian.shard_chance:
            player.amp_value += 0.08
            lines.append("[守关胜] 额外道则回响：增幅值 +0.08")
        gain = add_trial_points(player, 2 + target_realm // 2)
        if gain > 0:
            lines.append(f"[守关胜] 破境资粮 +{gain}（当前 {player.trial_points}/{trial_need(player.realm_idx)}）。")
        modify_pressure(player, 9.0)
        recover_resources(player, stamina=8.0, aura=6.0, fatigue_reduce=4.0)
        lines.extend(advance_turn(player, fragment_gain=0.22))
    else:
        new_layers = min(5, fail_layers + 1)
        player.guardian_failures[str(target_realm)] = new_layers
        penalty = int(player.break_need() * (0.10 + 0.05 * (1.0 - action_factor)))
        refund = int(player.break_need() * 0.05)
        player.exp = max(0, player.exp - penalty)
        player.exp += refund
        lines.append(f"[守关败] 印记未成，修为 -{penalty}，参悟回流 +{refund}。")
        lines.append(f"[守关败] 你解析了天关破绽，压制层提升到 {new_layers}/5。")
        lines.append("[守关败] " + gain_stats(player, guardian.essence_reward * 0.25 * action_factor, increase_amp=False))
        lost = add_trial_points(player, -1)
        if lost < 0:
            lines.append(f"[守关败] 破境资粮 {lost}。")
        modify_pressure(player, 16.0)
        recover_resources(player, stamina=3.0, aura=3.0, fatigue_reduce=1.5)
        lines.extend(advance_turn(player, fragment_gain=0.10))

    lines.extend(check_story(player))
    return lines


def action_breakthrough(player: Player, rng: random.Random) -> List[str]:
    ensure_realm_trial(player)
    rhythm_factor, rhythm_lines = action_rhythm(player, "突破")
    lines: List[str] = []
    if player.realm_idx >= len(REALMS) - 1:
        lines.append("[突破] 你已在无量境，暂无更高境界可突破。")
        return lines

    target_realm = player.realm_idx + 1
    if not player.has_guardian_mark(target_realm):
        lines.append(f"[突破] 缺少破境印记：需先击败 {REALMS[target_realm].name}守关者（命令：challenge/守关）。")
        return lines

    if player.exp < player.break_need():
        lines.append(f"[突破] 修为不足：需要 {player.break_need()}，当前 {player.exp}。")
        return lines

    need_trial = trial_need(player.realm_idx)
    if player.trial_points < need_trial:
        lines.append(f"[突破] 破境资粮不足：需要 {need_trial}，当前 {player.trial_points}。")
        lines.append("[突破] 请通过狩猎、悬赏、守关或寻宝积累资粮。")
        return lines

    resource_factor, resource_lines = spend_resources(
        player,
        stamina=14.0 + 1.5 * player.realm_idx,
        aura=22.0 + 2.0 * player.realm_idx,
        fatigue_add=9.0,
    )
    action_factor = max(0.50, rhythm_factor * (0.70 + 0.30 * resource_factor))

    surplus_trial = max(0, player.trial_points - need_trial)
    player.exp -= player.break_need()
    player.realm_idx = target_realm
    reset_realm_quest(player)
    reset_realm_trial(player)
    roll_new_bounty(player, rng)
    realm = player.current_realm()

    player.amp_stage = max(player.amp_stage, realm.unlock_stage)
    player.amp_value += realm.amp_bonus
    if surplus_trial > 0:
        carry_amp = min(0.12, 0.015 * surplus_trial)
        player.amp_value += carry_amp
        lines.append(f"[突破] 富余资粮转化为道韵，增幅值额外 +{carry_amp:.2f}。")
    modify_pressure(player, 6.0)

    lines.append(
        f"[突破] 你踏入 {realm.name}。增幅阶={player.amp_stage}({player.stage_name()}) 增幅值={player.amp_value:.3f}"
    )
    lines.extend(rhythm_lines)
    lines.extend(resource_lines)
    lines.append("[突破] " + gain_stats(player, realm.cultivate_essence * 1.10 * action_factor, increase_amp=False))
    recover_resources(player, stamina=12.0, aura=10.0, fatigue_reduce=8.0)
    lines.append(f"[新悬赏] 击败 {player.bounty_need} 个「{player.bounty_rank}{player.bounty_kind}」。")

    cap = cycle_cap(player.cycle)
    if player.realm_idx >= cap:
        lines.extend(apply_rebirth(player, cap, rng))

    lines.extend(advance_turn(player, fragment_gain=0.08))
    lines.extend(check_story(player))
    return lines


def status_lines(player: Player) -> List[str]:
    ensure_realm_quest(player)
    ensure_realm_trial(player)
    realm = player.current_realm()
    cap = cycle_cap(player.cycle)
    relic_text = "，".join(f"{k}x{v}" for k, v in sorted(player.relics.items())) or "无"
    req = quest_requirements(player.realm_idx)
    trial_req = trial_need(player.realm_idx)
    quest_state = "已完成" if player.quest_claimed else "进行中"

    target_realm = min(player.realm_idx + 1, len(REALMS) - 1)
    gate_text = "已完成" if player.has_guardian_mark(target_realm) else "未完成"
    suppress = min(5, int(player.guardian_failures.get(str(target_realm), 0)))

    return [
        f"境界: {realm.name}({player.realm_idx}) | 轮回 {player.cycle} | 本轮上限 {REALMS[cap].name}",
        (
            f"修为: {player.exp}/{player.break_need()} | 破境资粮: {player.trial_points}/{trial_req} | "
            f"下阶守关: {REALMS[target_realm].name}({gate_text}, 压制层{suppress}/5)"
        ),
        (
            f"宗门任务[{quest_state}]: 狩猎 {player.quest_hunt}/{req['hunt']} 修炼 {player.quest_cultivate}/{req['cultivate']} "
            f"调息 {player.quest_calm}/{req['calm']}"
        ),
        f"攻: {player.attack.fmt()} | 防: {player.defense.fmt()} | 血: {player.health.fmt()}",
        f"增幅: 阶 {player.amp_stage}[{player.stage_name()}] 值 {player.amp_value:.3f} | 葛立恒种子 {player.graham_seed}",
        (
            f"资源: 体力 {player.stamina:.1f}/100 灵气 {player.aura:.1f}/100 疲劳 {player.fatigue:.1f}/100 "
            f"| 心魔 {player.demon_pressure:.1f}/100"
        ),
        (
            f"悬赏: {player.bounty_rank}{player.bounty_kind} {player.bounty_done}/{player.bounty_need} "
            f"| 寻宝令 {player.treasure_keys}/3 (+{player.key_fragments:.2f}) 冷却 {player.treasure_cd} "
            f"| 胜败 {player.wins}/{player.losses} | 遗宝: {relic_text}"
        ),
    ]


def help_lines() -> List[str]:
    return [
        "命令列表:",
        "  hunt / 狩猎        - 打一场怪",
        "  cultivate / 修炼    - 稳定获取修为与灵蕴",
        "  treasure / 寻宝     - 消耗寻宝令探索遗迹（有冷却）",
        "  challenge / 守关    - 挑战下一境守关强敌，获取破境印记",
        "  break / 突破        - 消耗修为并突破（需守关印记+破境资粮）",
        "  calm / 调息         - 降低心魔并积攒寻宝令碎片",
        "  quest / 任务        - 查看当前境界宗门任务进度",
        "  bounty / 悬赏       - 查看当前悬赏与奖励建议",
        "  status / 状态       - 查看当前面板",
        "  lore / 剧情         - 查看已解锁剧情",
        "  save / 保存         - 保存进度",
        "  load / 读档         - 读取进度",
        "  help / 帮助         - 显示命令",
        "  quit / 退出         - 退出游戏",
    ]


def lore_lines(player: Player) -> List[str]:
    if not player.story_flags:
        return ["你还没有解锁剧情片段。"]
    return [f"已解锁剧情标记: {', '.join(sorted(player.story_flags))}"]


def bounty_lines(player: Player) -> List[str]:
    ensure_realm_trial(player)
    return [
        f"[悬赏] 当前目标：击败 {player.bounty_need} 个「{player.bounty_rank}{player.bounty_kind}」。",
        f"[悬赏] 当前进度：{player.bounty_done}/{player.bounty_need}（难度层级 {player.bounty_tier}）",
        (
            f"[悬赏] 当前破境资粮：{player.trial_points}/{trial_need(player.realm_idx)}，"
            "完成悬赏可额外补资粮并加速破境。"
        ),
    ]


def save_player(player: Player, path: Path = SAVE_PATH) -> str:
    path.write_text(json.dumps(player.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    return f"已保存到 {path}"


def load_player(path: Path = SAVE_PATH) -> Player:
    data = json.loads(path.read_text(encoding="utf-8"))
    return Player.from_dict(data)


def pick_auto_action(player: Player, rng: random.Random) -> str:
    ensure_realm_quest(player)
    ensure_realm_trial(player)
    req = quest_requirements(player.realm_idx)
    t_need = trial_need(player.realm_idx)
    challenge_need = max(2, int(math.ceil(t_need * 0.55)))

    if player.fatigue >= 72 or player.aura <= 14 or player.stamina <= 14:
        return "calm"

    if not player.quest_claimed:
        if player.quest_calm < req["calm"] and player.demon_pressure > 35:
            return "calm"
        if player.quest_cultivate < req["cultivate"] and player.aura > 24 and rng.random() < 0.50:
            return "cultivate"
        if player.quest_hunt < req["hunt"] and rng.random() < 0.70:
            return "hunt"
        if player.quest_calm < req["calm"]:
            return "calm"

    if (
        player.realm_idx < len(REALMS) - 1
        and player.quest_claimed
        and not player.has_guardian_mark(player.realm_idx + 1)
        and player.trial_points >= challenge_need
        and rng.random() < 0.35
    ):
        return "challenge"

    if (
        player.exp >= player.break_need()
        and player.realm_idx < len(REALMS) - 1
        and player.has_guardian_mark(player.realm_idx + 1)
        and player.trial_points >= t_need
    ):
        return "break"

    if player.demon_pressure >= 74:
        return "calm"

    if player.treasure_keys > 0 and player.treasure_cd == 0 and rng.random() < 0.15:
        return "treasure"

    if player.quest_claimed and player.trial_points < t_need:
        if player.bounty_done < player.bounty_need and player.stamina > 20:
            return "hunt"
        if player.treasure_keys > 0 and player.treasure_cd == 0 and rng.random() < 0.35:
            return "treasure"
        return "hunt"

    if player.bounty_done < player.bounty_need and player.stamina > 20 and rng.random() < 0.60:
        return "hunt"

    roll = rng.random()
    if roll < 0.58:
        return "hunt"
    if roll < 0.72:
        return "cultivate"
    if roll < 0.90:
        return "calm"
    return "treasure" if player.treasure_keys > 0 and player.treasure_cd == 0 else "calm"


def run_auto(player: Player, rng: random.Random, turns: int) -> None:
    print(f"自动模拟 {turns} 回合")
    for i in range(1, turns + 1):
        action = pick_auto_action(player, rng)
        if action == "hunt":
            lines = action_hunt(player, rng)
        elif action == "cultivate":
            lines = action_cultivate(player, rng)
        elif action == "treasure":
            lines = action_treasure(player, rng)
        elif action == "challenge":
            lines = action_challenge(player, rng)
        elif action == "break":
            lines = action_breakthrough(player, rng)
        else:
            lines = action_calm(player)

        if i % 10 == 0 or action in {"break", "challenge"}:
            print(f"--- 回合 {i} [{action}] ---")
            for line in lines[:5]:
                print(line)
            print(status_lines(player)[0])
    print("自动模拟结束。")
    for line in status_lines(player):
        print(line)


def run_interactive(player: Player, rng: random.Random) -> None:
    print("无穷道途：大数修仙（文字原型）")
    print("你是外门弃徒，拾得《无穷道典》残卷。")
    print("目标：在归零轮回中抬升增幅阶，最终对抗虚无。")
    for line in help_lines():
        print(line)
    print()
    for line in status_lines(player):
        print(line)

    while True:
        cmd = input("\n>> ").strip().lower()
        if cmd in {"hunt", "h", "狩猎"}:
            lines = action_hunt(player, rng)
        elif cmd in {"cultivate", "c", "修炼"}:
            lines = action_cultivate(player, rng)
        elif cmd in {"treasure", "t", "寻宝"}:
            lines = action_treasure(player, rng)
        elif cmd in {"challenge", "守关", "g"}:
            lines = action_challenge(player, rng)
        elif cmd in {"break", "b", "突破"}:
            lines = action_breakthrough(player, rng)
        elif cmd in {"calm", "调息", "m"}:
            lines = action_calm(player)
        elif cmd in {"quest", "任务"}:
            lines = quest_status_lines(player)
        elif cmd in {"bounty", "悬赏"}:
            lines = bounty_lines(player)
        elif cmd in {"status", "s", "状态"}:
            lines = status_lines(player)
        elif cmd in {"lore", "l", "剧情"}:
            lines = lore_lines(player)
        elif cmd in {"help", "帮助"}:
            lines = help_lines()
        elif cmd in {"save", "保存"}:
            lines = [save_player(player)]
        elif cmd in {"load", "读档"}:
            if SAVE_PATH.exists():
                loaded = load_player(SAVE_PATH)
                player.realm_idx = loaded.realm_idx
                player.exp = loaded.exp
                player.cycle = loaded.cycle
                player.legacy = loaded.legacy
                player.amp_stage = loaded.amp_stage
                player.amp_value = loaded.amp_value
                player.graham_seed = loaded.graham_seed
                player.attack = loaded.attack
                player.defense = loaded.defense
                player.health = loaded.health
                player.wins = loaded.wins
                player.losses = loaded.losses
                player.story_flags = loaded.story_flags
                player.relics = loaded.relics
                player.guardian_flags = loaded.guardian_flags
                player.guardian_failures = loaded.guardian_failures
                player.demon_pressure = loaded.demon_pressure
                player.treasure_keys = loaded.treasure_keys
                player.key_fragments = loaded.key_fragments
                player.treasure_cd = loaded.treasure_cd
                player.turn_count = loaded.turn_count
                player.quest_realm_idx = loaded.quest_realm_idx
                player.quest_hunt = loaded.quest_hunt
                player.quest_cultivate = loaded.quest_cultivate
                player.quest_calm = loaded.quest_calm
                player.quest_claimed = loaded.quest_claimed
                player.stamina = loaded.stamina
                player.aura = loaded.aura
                player.fatigue = loaded.fatigue
                player.last_action = loaded.last_action
                player.action_streak = loaded.action_streak
                player.bounty_kind = loaded.bounty_kind
                player.bounty_rank = loaded.bounty_rank
                player.bounty_need = loaded.bounty_need
                player.bounty_done = loaded.bounty_done
                player.bounty_tier = loaded.bounty_tier
                player.trial_realm_idx = loaded.trial_realm_idx
                player.trial_points = loaded.trial_points
                lines = [f"已读取 {SAVE_PATH}"] + status_lines(player)
            else:
                lines = [f"未找到存档：{SAVE_PATH}"]
        elif cmd in {"quit", "q", "exit", "退出"}:
            print("道友后会有期。")
            return
        else:
            lines = ["未知命令，输入 help/帮助 查看可用命令。"]

        for line in lines:
            print(line)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="无穷道途文字原型")
    parser.add_argument("--seed", type=int, default=None, help="随机种子")
    parser.add_argument("--auto", type=int, default=0, help="自动模拟回合数")
    parser.add_argument("--load", action="store_true", help="启动时读取存档")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rng = random.Random(args.seed)
    if args.load and SAVE_PATH.exists():
        player = load_player(SAVE_PATH)
    else:
        player = make_player(rng)

    if args.auto > 0:
        run_auto(player, rng, args.auto)
    else:
        run_interactive(player, rng)


if __name__ == "__main__":
    main()
