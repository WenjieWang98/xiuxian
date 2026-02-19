# 无穷道途（文字版大数修仙原型）

## 运行

```bash
python3 /Users/wangwenjie/Documents/code/open\ ai\ code\ playgroud/infinite_xianxia.py
```

图形界面版（保持原玩法逻辑）:

```bash
python3 /Users/wangwenjie/Documents/code/open\ ai\ code\ playgroud/infinite_xianxia_gui.py
```

自动模拟:

```bash
python3 /Users/wangwenjie/Documents/code/open\ ai\ code\ playgroud/infinite_xianxia.py --auto 120 --seed 42
```

读取存档:

```bash
python3 /Users/wangwenjie/Documents/code/open\ ai\ code\ playgroud/infinite_xianxia.py --load
```

## 命令

- `hunt / 狩猎`
- `cultivate / 修炼`
- `treasure / 寻宝`（消耗寻宝令，且有冷却）
- `challenge / 守关`（突破前置）
- `break / 突破`
- `calm / 调息`
- `quest / 任务`（查看宗门任务进度）
- `status / 状态`
- `lore / 剧情`
- `save / 保存`
- `load / 读档`

## 文件

- `/Users/wangwenjie/Documents/code/open ai code playgroud/infinite_xianxia.py`: 可运行游戏原型
- `/Users/wangwenjie/Documents/code/open ai code playgroud/infinite_xianxia_gui.py`: 图形界面版（含地图/怪物配图）
- `/Users/wangwenjie/Documents/code/open ai code playgroud/BALANCE.md`: 完整数值公式与平衡参数
