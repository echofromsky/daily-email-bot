#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 每日自动邮件机器人：抓天气 -> 生成 HTML -> 发邮件（只用 Python 自带库）
import datetime, json, os, smtplib, ssl, sys, urllib.parse, urllib.request
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formataddr

MAIL_USER = os.environ.get("MAIL_USER", "")
MAIL_PASS = os.environ.get("MAIL_PASS", "")
MAIL_TO = os.environ.get("MAIL_TO", "") or MAIL_USER
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.qq.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
CITY = os.environ.get("CITY_NAME") or "上海"
LAT = float(os.environ.get("CITY_LAT") or "31.23")
LON = float(os.environ.get("CITY_LON") or "121.47")

COORD = {"北京": (39.9, 116.4), "上海": (31.23, 121.47), "广州": (23.13, 113.26),
         "深圳": (22.54, 114.06), "杭州": (30.27, 120.15), "南京": (32.06, 118.8),
         "成都": (30.57, 104.07), "武汉": (30.59, 114.31), "西安": (34.34, 108.94),
         "长沙": (28.23, 112.94), "重庆": (29.56, 106.55), "郑州": (34.75, 113.63),
         "天津": (39.13, 117.2), "福州": (26.07, 119.3), "合肥": (31.82, 117.23),
         "南昌": (28.68, 115.86), "昆明": (25.04, 102.71), "南宁": (22.82, 108.32),
         "沈阳": (41.8, 123.43), "哈尔滨": (45.8, 126.53)}

WMO = {0: "晴 ☀️", 1: "大致晴朗 🌤️", 2: "局部多云 ⛅", 3: "阴 ☁️", 45: "雾 🌫️",
       48: "冻雾 🌫️", 51: "小毛毛雨 🌦️", 53: "毛毛雨 🌦️", 55: "大毛毛雨 🌧️",
       56: "冻毛毛雨 🌧️", 61: "小雨 🌦️", 63: "中雨 🌧️", 65: "大雨 🌧️",
       66: "冻雨 🌧️", 71: "小雪 🌨️", 73: "中雪 🌨️", 75: "大雪 ❄️",
       77: "米雪 🌨️", 80: "阵雨 🌦️", 81: "强阵雨 🌧️", 82: "暴雨 ⛈️",
       85: "阵雪 🌨️", 86: "强阵雪 ❄️", 95: "雷阵雨 ⛈️", 96: "雷阵雨伴冰雹 ⛈️",
       99: "强雷暴 ⛈️"}

QUOTES = ["种一棵树最好的时间是十年前，其次是现在。", "不要等待机会，而要创造机会。",
          "把简单的事做到极致，就是不简单。", "纸上得来终觉浅，绝知此事要躬行。",
          "路漫漫其修远兮，吾将上下而求索。", "保持热爱，奔赴山海。",
          "行动是治愈恐惧的良药。", "千里之行，始于足下。",
          "越努力，越幸运。", "星光不问赶路人，时光不负有心人。",
          "做好今天的事，就是对明天最好的准备。", "与其抱怨黑暗，不如提灯前行。"]


def get_weather():
    """从 Open-Meteo 免费接口获取天气（无需注册、无需 Key）"""
    lat, lon = COORD.get(CITY, (LAT, LON))
    p = {"latitude": lat, "longitude": lon,
         "current": "temperature_2m,weather_code,relative_humidity_2m,wind_speed_10m",
         "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
         "timezone": "Asia/Shanghai", "forecast_days": 2}
    url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(p)
    req = urllib.request.Request(url, headers={"User-Agent": "daily-email-bot/1.0"})
    d = json.loads(urllib.request.urlopen(req, timeout=20).read().decode("utf-8"))
    cur, day = d["current"], d["daily"]
    return {"city": CITY, "now": round(cur["temperature_2m"], 1),
            "desc": WMO.get(cur["weather_code"], "未知 🌡️"),
            "hum": cur["relative_humidity_2m"], "wind": round(cur["wind_speed_10m"], 1),
            "max": round(day["temperature_2m_max"][0], 1),
            "min": round(day["temperature_2m_min"][0], 1),
            "rain": day["precipitation_probability_max"][0],
            "tomo": WMO.get(day["weather_code"][1], "未知 🌡️")}


def build_html(w):
    """生成 HTML 邮件正文"""
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
    wk = "一二三四五六日"[now.weekday()]
    q = QUOTES[now.timetuple().tm_yday % len(QUOTES)]
    desc = w["desc"].rsplit(" ", 1)[0]
    icon = w["desc"].split()[-1]
    if w["max"] >= 30:
        color = ("#ff9a44", "#fc6076")
    elif w["max"] >= 20:
        color = ("#4facfe", "#00f2fe")
    elif w["max"] >= 10:
        color = ("#43cea2", "#185a9d")
    else:
        color = ("#5b86e5", "#36d1dc")
    t = """<div style="max-width:520px;margin:24px auto;background:#fff;border-radius:16px;overflow:hidden;font-family:'PingFang SC','Microsoft YaHei',sans-serif;box-shadow:0 6px 24px rgba(0,0,0,.08)">
<div style="background:linear-gradient(135deg,C1,C2);padding:28px 24px;color:#fff">
<div style="font-size:13px;opacity:.9">早上好，今天是</div>
<div style="font-size:22px;font-weight:600;margin-top:4px">DATE 星期WK</div>
<div style="margin-top:18px"><span style="font-size:44px">ICON</span><span style="font-size:40px;font-weight:700;margin-left:12px">NOW°</span><span style="margin-left:14px;font-size:16px">DESC</span></div>
<div style="margin-top:10px;font-size:14px;opacity:.95">CITY 最低 MIN° / 最高 MAX°</div></div>
<div style="padding:20px 24px">
<table style="width:100%;border-collapse:collapse;font-size:14px;color:#444">
<tr><td style="padding:10px 0;border-bottom:1px solid #f0f0f0">RH 相对湿度</td><td style="padding:10px 0;border-bottom:1px solid #f0f0f0;text-align:right">HUM%</td></tr>
<tr><td style="padding:10px 0;border-bottom:1px solid #f0f0f0">WD 风速</td><td style="padding:10px 0;border-bottom:1px solid #f0f0f0;text-align:right">WIND km/h</td></tr>
<tr><td style="padding:10px 0;border-bottom:1px solid #f0f0f0">UM 降水概率</td><td style="padding:10px 0;border-bottom:1px solid #f0f0f0;text-align:right">RAIN%</td></tr>
<tr><td style="padding:10px 0">TMR 明天</td><td style="padding:10px 0;text-align:right">TOMO</td></tr></table>
<div style="margin-top:22px;padding:16px 18px;background:#f8fafc;border-left:4px solid C1;border-radius:8px;font-size:15px;color:#222;line-height:1.7">QUOTE</div>
<div style="margin-top:14px;font-size:13px;color:#888">TIPS</div></div>
<div style="padding:14px 24px;background:#fafbfc;font-size:12px;color:#aaa;text-align:center">本邮件由 GitHub Actions 自动生成 数据源 Open-Meteo</div></div>"""
    for k, v in [("C1", color[0]), ("C2", color[1]), ("DATE", now.strftime("%Y年%m月%d日 ·")),
                 ("WK", wk), ("ICON", icon), ("NOW", str(w["now"])), ("DESC", desc),
                 ("CITY", w["city"]), ("MIN", str(w["min"])), ("MAX", str(w["max"])),
                 ("RH", "💧"), ("HUM", str(w["hum"])), ("WD", "🌬️"), ("WIND", str(w["wind"])),
                 ("UM", "☔"), ("RAIN", str(w["rain"])), ("TMR", "🌤️"),
                 ("TOMO", w["tomo"]), ("QUOTE", "“" + q + "”"),
                 ("TIPS", "💡 出门前看看窗外，别被雨淋。")]:
        t = t.replace(k, v)
    return t


def send_mail(w, html):
    """SMTP SSL 发送邮件"""
    subject = "每日简报 | %s %s %s°~%s°" % (w["city"], w["desc"].rsplit(" ", 1)[0], w["min"], w["max"])
    msg = MIMEText(html, "html", "utf-8")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = formataddr(("每日简报机器人", MAIL_USER))
    msg["To"] = MAIL_TO
    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx, timeout=30) as s:
        s.login(MAIL_USER, MAIL_PASS)
        s.sendmail(MAIL_USER, [MAIL_TO], msg.as_string())
    return subject


def main():
    w = get_weather()
    print("天气:", w["city"], w["desc"], w["now"], "°C (", w["min"], "~", w["max"], ")")
    html = build_html(w)
    open("preview.html", "w", encoding="utf-8").write(html)
    if "--dry-run" in sys.argv or not (MAIL_USER and MAIL_PASS):
        print("仅预览模式，已生成 preview.html")
        return
    print("发送成功:", send_mail(w, html))


if __name__ == "__main__":
    main()
