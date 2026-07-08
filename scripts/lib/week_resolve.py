"""按系统日历解析「本周 / 上周 / 上上周」，再匹配 otl 日期区块。"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta

RELATIVE_WEEK_KEYWORDS: dict[str, int] = {
    "本周": 0,
    "这周": 0,
    "本星期": 0,
    "上周": 1,
    "上一周": 1,
    "前一周": 1,
    "上个星期": 1,
    "上上周": 2,
    "前两周": 2,
    "上上星期": 2,
}


def parse_relative_week_phrase(text: str) -> int | None:
    """从用户话术解析相对周次：0=本周，1=上周，2=上上周。"""
    if not text:
        return None
    t = text.strip()
    # 先匹配更长的词，避免「上上周」被「上周」截胡
    for phrase in sorted(RELATIVE_WEEK_KEYWORDS, key=len, reverse=True):
        if phrase in t:
            return RELATIVE_WEEK_KEYWORDS[phrase]
    return None


def calendar_week_bounds(today: date, weeks_ago: int = 0) -> tuple[date, date]:
    """以周一为一周起点。weeks_ago=0 本周，1 上周，2 上上周。"""
    monday_this = today - timedelta(days=today.weekday())
    monday = monday_this - timedelta(days=7 * weeks_ago)
    return monday, monday + timedelta(days=6)


def parse_dated_sections(
    sections: list[tuple[str, str]],
) -> list[tuple[date, str, str]]:
    dated: list[tuple[date, str, str]] = []
    for label, body in sections:
        m = re.search(r"(\d{4}-\d{2}-\d{2})", label)
        if m:
            dated.append((datetime.strptime(m.group(1), "%Y-%m-%d").date(), label, body))
    return dated


def pick_section_for_calendar_week(
    dated: list[tuple[date, str, str]],
    weeks_ago: int,
    today: date | None = None,
) -> tuple[str, str, date]:
    """在 otl 已解析的日期区块中，找落在系统日历目标周内的区块。"""
    today = today or date.today()
    week_start, week_end = calendar_week_bounds(today, weeks_ago)
    in_range = [t for t in dated if week_start <= t[0] <= week_end]
    if in_range:
        in_range.sort(key=lambda x: x[0], reverse=True)
        d, label, body = in_range[0]
        return label, body, d

    available = sorted({t[0] for t in dated}, reverse=True)
    label_map = {0: "本周", 1: "上周", 2: "上上周"}.get(weeks_ago, f"前{weeks_ago}周")
    avail_str = ", ".join(str(d) for d in available)
    raise SystemExit(
        f"otl 中无匹配系统日历{label_map}（{week_start} ~ {week_end}）的 # 日期区块；"
        f"可用日期: {avail_str}"
    )


def pick_latest_section_on_or_before(
    dated: list[tuple[date, str, str]],
    today: date | None = None,
) -> tuple[str, str, date]:
    """默认规则：取日期 ≤ 今天 的最新一期（未指定相对周次时用）。"""
    today = today or date.today()
    eligible = [t for t in dated if t[0] <= today]
    if eligible:
        eligible.sort(key=lambda x: x[0], reverse=True)
        d, label, body = eligible[0]
        return label, body, d
    dated.sort(key=lambda x: x[0], reverse=True)
    d, label, body = dated[0]
    return label, body, d


def build_week_aliases(week_iso: str) -> list[str]:
    """由 week (YYYY-MM-DD) 生成部门表头匹配别名。"""
    d = datetime.strptime(week_iso[:10], "%Y-%m-%d").date()
    period_start = d - timedelta(days=6)
    period = f"{period_start.month}.{period_start.day}-{d.month}.{d.day}"
    md = f"{d.month}月{d.day}日"
    short = f"{d.month}.{d.day}"
    return [short, md, period, f"周期：{period}"]
