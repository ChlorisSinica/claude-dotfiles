#!/usr/bin/env python3
"""Pattern 6: 2-line braille dots - model on line 1, metrics with remaining on line 2"""
import json, sys
from datetime import datetime, timezone

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

data = json.load(sys.stdin)

BRAILLE = ' ⣀⣄⣤⣦⣶⣷⣿'
R = '\033[0m'
DIM = '\033[2m'

def gradient(pct):
    if pct < 50:
        r = int(pct * 5.1)
        return f'\033[38;2;{r};200;80m'
    else:
        g = int(200 - (pct - 50) * 4)
        return f'\033[38;2;255;{max(g, 0)};60m'

def braille_bar(pct, width=8):
    pct = min(max(pct, 0), 100)
    level = pct / 100
    bar = ''
    for i in range(width):
        seg_start = i / width
        seg_end   = (i + 1) / width
        if level >= seg_end:
            bar += BRAILLE[7]
        elif level <= seg_start:
            bar += BRAILLE[0]
        else:
            frac = (level - seg_start) / (seg_end - seg_start)
            bar += BRAILLE[min(int(frac * 7), 7)]
    return bar

def fmt_tokens(tokens):
    if tokens >= 1_000_000:
        v = tokens / 1_000_000
        return f'{v:.1f}M' if v < 10 else f'{int(v)}M'
    if tokens >= 1_000:
        v = tokens / 1_000
        return f'{v:.1f}k' if v < 10 else f'{int(v)}k'
    return str(tokens)

def fmt_time(seconds):
    if seconds <= 0:
        return 'now'
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    if h >= 24:
        d = h // 24
        h2 = h % 24
        return f'{d}d{h2}h' if h2 else f'{d}d'
    if h > 0:
        return f'{h}h{m:02d}m' if m else f'{h}h'
    return f'{m}m'

def remaining_seconds(resets_at):
    if resets_at is None:
        return None
    try:
        if isinstance(resets_at, (int, float)):
            diff = resets_at - datetime.now(timezone.utc).timestamp()
        else:
            reset_dt = datetime.fromisoformat(str(resets_at).replace('Z', '+00:00'))
            diff = (reset_dt - datetime.now(timezone.utc)).total_seconds()
        return max(diff, 0)
    except Exception:
        return None

def fmt_ctx(pct, ctx_data):
    p   = round(pct)
    rem = 100 - p
    col = gradient(pct)
    # token count: used = pct/100 * window_size
    window_size = ctx_data.get('context_window_size')
    if window_size:
        used = int(pct / 100 * window_size)
        tok = f'{fmt_tokens(used)}/{fmt_tokens(window_size)}'
        return f'{DIM}ctx{R} {col}{braille_bar(pct)}{R} {p}% {DIM}({tok}){R}'
    return f'{DIM}ctx{R} {col}{braille_bar(pct)}{R} {p}%'

def fmt_rate(label, pct, rate_data):
    p   = round(pct)
    col = gradient(pct)
    secs = remaining_seconds(rate_data.get('resets_at'))
    rem = f' {DIM}({fmt_time(secs)}){R}' if secs is not None else ''
    return f'{DIM}{label}{R} {col}{braille_bar(pct)}{R} {p}%{rem}'

model = data.get('model', {}).get('display_name', 'Claude')
sep   = f' {DIM}│{R} '

line2_parts = []

ctx_data = data.get('context_window', {})
ctx = ctx_data.get('used_percentage')
if ctx is not None:
    line2_parts.append(fmt_ctx(ctx, ctx_data))

five_data = data.get('rate_limits', {}).get('five_hour', {})
five = five_data.get('used_percentage')
if five is not None:
    line2_parts.append(fmt_rate('5h', five, five_data))

week_data = data.get('rate_limits', {}).get('seven_day', {})
week = week_data.get('used_percentage')
if week is not None:
    line2_parts.append(fmt_rate('7d', week, week_data))

print(f'{model}\n{sep.join(line2_parts)}', end='')
