import asyncio
import os
import sys
import json
import shutil
import time
import hmac
import base64
import hashlib
import struct
import tempfile
import requests
from urllib.parse import parse_qs, urlsplit
from pydoll.constants import Key
from pydoll.browser import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.protocol.network.events import NetworkEvent

current_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(current_dir)

# 复用 HTTP 连接的 Session（避免每次下单重新 TCP+TLS 握手）
_session = requests.Session()
_session.headers.update({
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'en-GB,en;q=0.9,zh-CN;q=0.8,zh;q=0.7,en-US;q=0.6',
    'client-type': 'web',
    'content-type': 'application/x-www-form-urlencoded',
    'dnt': '1',
    'future_source': '1',
    'hc-language': 'zh_CN',
    'hc-platform': 'web',
    'lang': 'zh_CN',
    'origin': 'https://hibt.com',
    'platform': 'PC',
    'priority': 'u=1, i',
    'referer': 'https://hibt.com/',
    'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'cross-site',
    'sec-gpc': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
})

with open('config.json', 'r') as f:
    configs = json.load(f)

email = configs.get("email", "email@gmail.com")
password = configs.get("password", "password")
totp_secret = configs.get("totp_secret", "ABCDEFGHIJKLMNO1234567890")

cmd_key = Key.META if sys.platform == "darwin" else Key.CONTROL

def is_writable_dir(path):
    try:
        os.makedirs(path, exist_ok=True)
        test_file = os.path.join(path, ".__pydoll_write_test__")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(test_file)
        return True
    except:
        return False

def resolve_user_data_dir():
    candidates = []

    if os.name == "nt":
        candidates.append(os.path.expanduser("~/.config/pydoll-hibt"))
        candidates.append(os.path.abspath("./pydoll-hibt"))
        local_appdata = os.environ.get("LOCALAPPDATA")
        appdata = os.environ.get("APPDATA")
        if local_appdata:
            candidates.append(os.path.join(local_appdata, "pydoll-hibt"))
        if appdata:
            candidates.append(os.path.join(appdata, "pydoll-hibt"))
        candidates.append(os.path.join(tempfile.gettempdir(), "pydoll-hibt"))
    else:
        chrome_bin = detect_chrome_bin()
        if chrome_bin.startswith("/snap/"):
            candidates.append(os.path.expanduser("~/snap/chromium/common/pydoll-hibt"))
        else:
            candidates.append(os.path.expanduser("~/.config/pydoll-hibt"))
        candidates.append(os.path.abspath("./pydoll-hibt"))
        candidates.append("/tmp/.pydoll-hibt")

    for p in candidates:
        if p and is_writable_dir(p):
            return p

    return candidates[0]

def detect_chrome_bin():
    p = os.environ.get("CHROME_BIN")
    if p and os.path.exists(p):
        return p

    candidates = [
        shutil.which("google-chrome-stable"),
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        "/snap/bin/chromium",
        "/usr/bin/chromium",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/google-chrome",
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return ""

def totp(secret):
    t = int(time.time())
    s = "".join(secret.split()).upper()
    pad = "=" * ((8 - len(s) % 8) % 8)
    key = base64.b32decode(s + pad, casefold=True)

    counter = t // 30
    msg = struct.pack(">Q", counter)
    hm = hmac.new(key, msg, hashlib.sha1).digest()

    offset = hm[-1] & 0x0F
    code_int = struct.unpack(">I", hm[offset:offset + 4])[0] & 0x7FFFFFFF
    code = code_int % (10 ** 6)

    return f"{code:06d}"

def totp_remaining():
    t = int(time.time())
    return 30 - (t % 30)

def get_token(reset=False, headless=True):
    v = ""
    x_auth_token = ""
    authorization = ""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
    user_data_dir = resolve_user_data_dir()
    if reset and os.path.exists(user_data_dir):
        shutil.rmtree(user_data_dir)

    options = ChromiumOptions()
    chrome_bin = detect_chrome_bin()
    if chrome_bin:
        options.binary_location = chrome_bin

    options.add_argument(fr"--user-data-dir={user_data_dir}")
    options.add_argument(f"--user-agent={user_agent}")
    options.add_argument("--window-size=1280,960")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-breakpad")
    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
    if sys.platform.startswith("linux"):
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-setuid-sandbox")

    browser = Chrome(options=options)

    try:
        tab = loop.run_until_complete(browser.start())
    except Exception as e:
        print("浏览器启动失败:", e)
        return
    
    loop.run_until_complete(tab.enable_network_events())

    def on_request(req):
        try:
            request = req.get("params", {}).get("request", {})
            url = request.get("url", "")
            if not url.startswith("https://api.hibt0.com/option/option-order/history-summary"):
                return

            headers = dict(request.get("headers", {}) or {})
            qs = parse_qs(urlsplit(url).query)

            v1 = qs.get("v", [""])[0]
            v2 = headers.get("x-auth-token", "")
            v3 = headers.get("Authorization", "")

            if v1 and v2 and v3:
                nonlocal v, x_auth_token, authorization
                v, x_auth_token, authorization = v1, v2, v3
        except:
            pass

    loop.run_until_complete(tab.on(NetworkEvent.REQUEST_WILL_BE_SENT, on_request))
    loop.run_until_complete(tab.go_to('https://hibt.com/member'))
    loop.run_until_complete(asyncio.sleep(2))

    while True:
        loop.run_until_complete(asyncio.sleep(1))
        
        if v and x_auth_token and authorization:
            token_dict = {"v": v, "x-auth-token": x_auth_token, "Authorization": authorization}
            with open("token.json", "w", encoding="utf-8") as f:
                f.write(json.dumps(token_dict, indent=4, ensure_ascii=False))
            print("v:", v)
            print("x-auth-token:", x_auth_token)
            print("Authorization:", authorization)
            try:
                loop.run_until_complete(browser.stop())
            except:
                pass
            try:
                loop.run_until_complete(browser.close())
            except:
                pass
            try:
                loop.close()
            except:
                pass
            break

        try:
            current_url = loop.run_until_complete(tab.current_url)
            if "login" in current_url:
                try:
                    device_container = loop.run_until_complete(tab.query("[class*='device-verify-mian']"))
                    try:
                        google_img = loop.run_until_complete(device_container.query("img[src*='google']"))
                        loop.run_until_complete(google_img.click())
                        continue
                    except:
                        pass

                    try:
                        otp_inputs = loop.run_until_complete(device_container.query("input[type='tel']", find_all=True))
                        wait_time = 1 if totp_remaining() > 3 else totp_remaining() + 1
                        loop.run_until_complete(asyncio.sleep(wait_time))
                        totp_code = totp(totp_secret)
                        if len(otp_inputs) == 6:
                            for el in otp_inputs:
                                loop.run_until_complete(el.click())
                                loop.run_until_complete(tab.keyboard.hotkey(cmd_key, Key.A))
                                loop.run_until_complete(tab.keyboard.press(Key.BACKSPACE))
                            for el, digit in zip(otp_inputs, totp_code):
                                loop.run_until_complete(el.click())
                                loop.run_until_complete(el.insert_text(digit))

                        enter_btn = loop.run_until_complete(device_container.query("button[type='button']"))
                        loop.run_until_complete(enter_btn.click())
                        loop.run_until_complete(asyncio.sleep(3))
                        continue
                    except:
                        pass

                except:
                    try:
                        email_input = loop.run_until_complete(tab.query(".email-input input[type='text']"))
                        loop.run_until_complete(email_input.click())
                        loop.run_until_complete(tab.keyboard.hotkey(cmd_key, Key.A))
                        loop.run_until_complete(tab.keyboard.press(Key.BACKSPACE))
                        loop.run_until_complete(email_input.insert_text(email))
                        pwd_input = loop.run_until_complete(tab.query(".login input[type='password']"))
                        loop.run_until_complete(pwd_input.click())
                        loop.run_until_complete(tab.keyboard.hotkey(cmd_key, Key.A))
                        loop.run_until_complete(tab.keyboard.press(Key.BACKSPACE))
                        loop.run_until_complete(pwd_input.insert_text(password))
                        login_btn = loop.run_until_complete(tab.query(".login button[type='button']"))
                        loop.run_until_complete(login_btn.click())
                        loop.run_until_complete(asyncio.sleep(3))
                        continue
                    except:
                        pass

            elif "member" in current_url:
                try:
                    loop.run_until_complete(tab.go_to('https://hibt.com/bill?tab=options'))
                    loop.run_until_complete(asyncio.sleep(3))
                except:
                    pass
        except:
            pass

def place_order_web(v, authorization, x_auth_token, amount, direction, symbol, time_unit):
    url = 'https://api.hibt0.com/option/option-order/place'
    params = {"v": v}
    data = {
        'amount': str(amount),
        'direction': str(direction),
        'symbol': str(symbol),
        'timeUnit': str(time_unit),
        'langCode': 'zh_CN'
    }
    response = _session.post(
        url, headers={'authorization': authorization, 'x-auth-token': x_auth_token},
        data=data, params=params
    )
    return response.json()

if __name__ == '__main__':
    get_token(reset=False, headless=True) # 设置 reset=True 清除浏览器缓存, headless=False 显示浏览器界面
    # with open("token.json", "r") as f:
    #     token_dict = json.load(f)
    # v = token_dict["v"]
    # authorization = token_dict["Authorization"]
    # x_auth_token = token_dict["x-auth-token"]
    # result = place_order_web(v=v, authorization=authorization, x_auth_token=x_auth_token, amount=3, direction=1, symbol="btc_usdt", time_unit=5)
    # print("下单结果:", result)