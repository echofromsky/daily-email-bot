#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日自动邮件机器人
功能：抓取当天天气 + 每日一句，自动发一封 HTML 邮件到你的邮箱。
只用 Python 自带库，无需 pip install。
用法：python main.py（正常发信） / python main.py --dry-run（仅预览）
"""

import datetime
import json
import os
import random
import smtplib
import ssl
import sys
import urllib.parse
import urllib.request
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formataddr

# ========== 1. 配置（GitHub 上通过 Secrets 注入，本地可改默认值） ==========

MAIL_USER = os.environ.get("MAIL_USER", "")           # 发件邮箱，如 123456@qq.com
MAIL_PASS = os.environ.get("MAIL_PASS", "")           # 16位授权码（不是QQ密码！）
MAIL_TO = os.environ.get("MAIL_TO", "") or MAIL_USER  # 收件邮箱，默认发给自己

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.qq.com")  # 163邮箱改 smtp.163.com
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))

CITY_NAME = os.environ.get("CITY_NAME", "上海")
CITY_LAT = float(os.environ.get("CITY_LAT", "31.23"))
CITY_LON = float(os.environ.get("CITY_LON", "121.47"))

CITY_COORDS = {
    "北京": (39.90, 116.40), "上海": (31.23, 121.47), "广州": (23.13, 113.26),
    "深圳": (22.54, 114.06), "杭州": (30.27, 120.15), "南京": (32.06, 118.80),
    "成都": (30.57, 104.07), "武汉": (30.59, 114.31), "西安": (34.34, 108.94),
    "长沙": (28.23, 112.94), "重庆": (29.56, 106.55), "郑州": (34.75, 113.63),
    "哈尔滨": (45.80, 126.53), "沈阳": (41.80, 123.43), "济南": (36.65, 117.12),
    "合肥": (31.82, 117.23), "福州": (26.07, 119.30), "南昌": (28.68, 115.86),
    "天津": (39.13, 117.20), "昆明": (25.04, 102.71), "南宁": (22.82, 108.32),
}

WEATHER_MAP = {
    0: ("晴", "☀️"), 1: ("大致晴朗", "🌤️"), 2: ("局部多云", "⛅"), 3: ("阴", "☁️"),
    45: ("雾", "🌫️"), 48: ("冻雾", "🌫️"), 51: ("小毛毛雨", "🌦️"), 53: ("毛毛雨", "🌦️"),
    55: ("大毛毛雨", "🌧️"), 56: ("冻毛毛雨", "🌧️"), 57: ("强冻毛毛雨", "🌧️"),
    61: ("小雨", "🌦️"), 63: ("中雨", "🌧️"), 65: ("大雨", "🌧️"),
    66: ("冻雨", "🌧️"), 67: ("强冻雨", "🌧️"), 71: ("小雪", "🌨️"),
    73: ("中雪", "🌨️"), 75: ("大雪", "❄️"), 77: ("米雪", "🌨️"),
    80: ("阵雨", "🌦️"), 81: ("强阵雨", "🌧️"), 82: ("暴雨", "⛈️"),
    85: ("阵雪", "🌨️"), 86: ("强阵雪", "❄️"), 95: ("雷阵雨", "⛈️"),
    96: ("雷阵雨伴冰雹", "⛈️"), 99: ("强雷暴", "⛈️"),
}

QUOTES = [
    "种一棵树最好的时间是十年前，其次是现在。",
    "不要等待机会，而要创造机会。",
    "把纸上价值，应该看他贡献什么，而不是取得什么。",
    "保持热爱，奔赴山海。",
    "你所经历的每一次挫折，都会在你人生的某个时刻派上用场。",
    "行动是治愈恐惧的良药。",
    "千里之行，始于足下。",
    "越努力，越幸运。",
    "慢一点没关系，只要不停下来。",
    "所有的努力都不会白费，它们只是在等一个合适的时机。",
    "与其抱怨黑暗，不如提灯前行。",
    "认真的人，运气都不会太差。",
    "不要假装努力，结果不会陪你演戏。",
    "生活的理想，就是为了理想的生活。",
    "星光不问赶路人，时光不负有心人。",
    "做好今天的事，就是对明天最好的准备。",
]

TIPS = [
    "💡 记得喝水，今天已经过去一半了。",
    "💡 久坐一小时，起身活动五分钟。",
    "💡 今日三件事：做完一件划掉一件。",
    "💡 晚上记得早点睡，别熬到凌晨。",
    "💡 出门前看看窗外，别被雨淋。",
    "💡 给家人发条消息吧，他们会开心。",
]


def get_weather():
    """从 Open-Meteo 免费接口获取天气（无需注册、无需 API Key）"""
    lat, lon = CITY_COORDS.get(CITY_NAME, (CITY_LAT, CITY_LON))
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,weather_code,relative_humidity_2m,wind_speed_10m",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "timezone": "Asia/Shanghai",
        "forecast_days": 2,
    }
    url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "daily-email-bot/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    cur = data["current"]
    daily = data["daily"]
    desc, icon = WEATHER_MAP.get(cur["weather_code"], ("未知天气", "🌡️"))

    return {
        "city": CITY_NAME,
        "temp": round(cur["temperature_2m"], 1),
        "desc": desc,
        "icon": icon,
        "humidity": cur["relative_humidity_2m"],
        "wind": round(cur["wind_speed_10m"], 1),
        "tmax": round(daily["temperature_2m_max"][0], 1),
        "tmin": round(daily["temperature_2m_min"][0], 1),
        "rain": daily["precipitation_probability_max"][0],
        "tomorrow": WEATHER_MAP.get(daily["weather_code"][1], ("未知", "🌡️")),
    }


def build_html(w):
    """生成 HTML 邮件正文"""
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
    weekday = "一二三四五六日"[now.weekday()]
    date_str = now.strftime("%Y年%m月%d日")
    quote = QUOTES[now.timetuple().tm_yday % len(QUOTES)]
    tip = TIPS[now.timetuple().tm_yday % len(TIPS)]

    if w["tmax"] >= 30:
        c1, c2 = "#ff9a44", "#fc6076"
    elif w["tmax"] >= 20:
        c1, c2 = "#4facfe", "#00f2fe"
    elif w["tmax"] >= 10:
        c1, c2 = "#43cea2", "#185a9d"
    else:
        c1, c2 = "#5b86e5", "#36d1dc"

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f6f8;font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;">
<div style="max-width:520px;margin:24px auto;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 6px 24px rgba(0,0,0,.08);">
  <div style="
