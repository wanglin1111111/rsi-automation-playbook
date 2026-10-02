#!/usr/bin/env python3
"""validate.py — rsi-automation-playbook 自动化计划六维校验器

输入: 自动化计划 JSON（schema 见 tests/sample_good.json）
  {
    "worklog_minutes": 10,              # 开工前"什么问题/什么算解决"的时长（分钟）
    "tasks": [
      {
        "id": "TASK-1",
        "current_al": 3,                # 当前 AL 级 0-5
        "target_al": 4,                 # 目标 AL 级 0-5
        "verification": "execution",    # 验证层级: formal|execution|learned_judge|intrinsic
        "generator": "claude",          # 生成方
        "judge": "human",               # 评判方: 模型名 / human / tool
        "irreversible_actions": [],     # 涉及的不可逆动作枚举，须 ⊆ IRREVERSIBLE
        "monitoring": {                 # target_al >= 4 时必填
          "pre_block": true,            # 不可逆动作事前硬拦截
          "post_review_pct": 2,         # 可逆产物事后抽审比例(1-2 推荐, 0=无)
          "metrics": ["coverage", "review_latency", "escalation_rate"]
        }
      }
    ]
  }

六维校验（任一 FAIL → exit 1）：
  D1 分级合法: current_al/target_al ∈ [0,5]，且 target_al >= current_al（只上推不降级）
  D2 不承诺 AL5: target_al == 5 直接打回（全行业 AL5 为零，卡点在品味）
  D3 验证层级门槛: verification ∈ 枚举；target_al >= 4 且 verification ∈ {learned_judge, intrinsic}
     → FAIL（无机器客观验收不得 AL4+ 闭环）
  D4 拆开生成与评判: target_al >= 4 且 judge == generator（同名/共享权重）→ FAIL（自我确认循环）
  D5 双层监控: target_al >= 4 时 monitoring 必填且完整：
     有 irreversible_actions 时 pre_block 必须 true；post_review_pct ∈ (0,100]；
     metrics 三项齐全（coverage/review_latency/escalation_rate）
  D6 开工纪律: 顶层 worklog_minutes >= 10（品味+裁判不可省）

退出码：0=通过 / 1=有缺陷 / 2=文件/格式错误
"""
import json
import sys

VERIFICATION = {"formal", "execution", "learned_judge", "intrinsic"}
IRREVERSIBLE = {"delete_db", "exfiltrate", "payment", "production_deploy", "prod_config_change"}
REQUIRED_METRICS = {"coverage", "review_latency", "escalation_rate"}
OBJ = {"formal", "execution"}  # 机器客观验收层


def fail(checks, code, msg):
    checks.append(("FAIL", code, msg))


def ok(checks, code, msg):
    checks.append(("OK", code, msg))


def validate(plan):
    checks = []
    tasks = plan.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        fail(checks, "D0", "tasks 必须是非空数组")
        return checks

    # D6 开工纪律
    wl = plan.get("worklog_minutes")
    if not isinstance(wl, (int, float)) or wl < 10:
        fail(checks, "D6", f"worklog_minutes={wl!r}——开工前'什么问题/什么算解决'须 ≥10 分钟")
    else:
        ok(checks, "D6", f"开工纪律通过（{wl} 分钟）")

    for i, t in enumerate(tasks):
        where = f"tasks[{i}]({t.get('id', '?')})"
        cur = t.get("current_al")
        tgt = t.get("target_al")

        # D1 分级合法
        if not isinstance(cur, int) or cur < 0 or cur > 5:
            fail(checks, "D1", f"{where}: current_al 非法: {cur!r}")
            continue
        if not isinstance(tgt, int) or tgt < 0 or tgt > 5:
            fail(checks, "D1", f"{where}: target_al 非法: {tgt!r}")
            continue
        if tgt < cur:
            fail(checks, "D1", f"{where}: 目标级 {tgt} 低于当前级 {cur}——只上推不降级")
        else:
            ok(checks, "D1", f"{where}: AL{cur}→AL{tgt}")

        # D2 不承诺 AL5
        if tgt == 5:
            fail(checks, "D2", f"{where}: 目标 AL5（完全自主）——全行业为零，卡点在品味，不承诺不立项")
        else:
            ok(checks, "D2", f"{where}: 未承诺 AL5")

        # D3 验证层级门槛
        ver = t.get("verification")
        if ver not in VERIFICATION:
            fail(checks, "D3", f"{where}: verification 非法: {ver!r}（须为 formal/execution/learned_judge/intrinsic）")
        elif tgt >= 4 and ver in ("learned_judge", "intrinsic"):
            fail(checks, "D3", f"{where}: 验证层级={ver} 无机器客观验收——不得 AL4+ 闭环，留人在环上")
        else:
            ok(checks, "D3", f"{where}: 验证层级 {ver} 与目标 AL{tgt} 匹配")

        # D4 拆开生成与评判
        gen = t.get("generator")
        judge = t.get("judge")
        if not gen or not judge:
            fail(checks, "D4", f"{where}: generator/judge 缺失")
        elif tgt >= 4 and judge == gen:
            fail(checks, "D4", f"{where}: judge==generator（{gen}）——自我确认循环：换模型/外部ground truth/可检验断言")
        else:
            ok(checks, "D4", f"{where}: 生成与评判已拆分（{gen} vs {judge}）")

        # D5 双层监控
        acts = set(t.get("irreversible_actions") or [])
        unknown = acts - IRREVERSIBLE
        if unknown:
            fail(checks, "D5", f"{where}: 未知不可逆动作枚举: {sorted(unknown)}（须 ⊆ {sorted(IRREVERSIBLE)}）")
        if tgt >= 4:
            mon = t.get("monitoring") or {}
            if acts and mon.get("pre_block") is not True:
                fail(checks, "D5", f"{where}: 涉及不可逆动作 {sorted(acts)} 但 pre_block 未启用——无事前拦截不许规模化")
            else:
                ok(checks, "D5", f"{where}: 事前拦截通过（actions={sorted(acts) or '无'}）")
            pct = mon.get("post_review_pct")
            if not isinstance(pct, (int, float)) or pct <= 0 or pct > 100:
                fail(checks, "D5", f"{where}: post_review_pct 非法: {pct!r}（须 >0，推荐 1-2）")
            else:
                ok(checks, "D5", f"{where}: 事后抽审 {pct}%")
            metrics = set(mon.get("metrics") or [])
            missing = REQUIRED_METRICS - metrics
            if missing:
                fail(checks, "D5", f"{where}: 监控指标缺失: {sorted(missing)}（三指标：覆盖率/审查延迟/升级率）")
            else:
                ok(checks, "D5", f"{where}: 三指标齐全")
        else:
            ok(checks, "D5", f"{where}: 目标 AL{tgt} < 4，双层监控豁免")

    return checks


def main():
    if len(sys.argv) != 2:
        print("usage: python validate.py plan.json", file=sys.stderr)
        return 2
    try:
        with open(sys.argv[1], encoding="utf-8") as f:
            plan = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"ERROR: 无法读取/解析: {e}", file=sys.stderr)
        return 2
    if not isinstance(plan, dict):
        print("ERROR: 顶层必须是 JSON 对象", file=sys.stderr)
        return 2

    checks = validate(plan)
    fails = [c for c in checks if c[0] == "FAIL"]
    for status, code, msg in checks:
        if status == "FAIL":
            print(f"[{code}] FAIL {msg}")
    print(f"== {len(checks) - len(fails)} OK / {len(fails)} FAIL ==")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
