# 接口逆向

HiBT 事件合约接口逆向，利用 API 下单，可实现批量化、自动化交易；项目仅供学习交流使用，请勿用于非法用途，否则后果自负。

HiBT 可在 Web 端登录，可利用登录后的凭证进行接口调用。

- 对于 Web 端，cURL bash 接口为

```shell
curl 'https://api.hibt0.com/option/option-order/place?v=DIZw1DdpKHBjoaChKLcN1oWtKFUFdmPgsp2YzFi3nsM%3D' \
  -H 'accept: application/json, text/plain, */*' \
  -H 'accept-language: en-GB,en;q=0.9,zh-CN;q=0.8,zh;q=0.7,en-US;q=0.6' \
  -H 'client-type: web' \
  -H 'content-type: application/x-www-form-urlencoded' \
  -H 'dnt: 1' \
  -H 'future_source: 1' \
  -H 'hc-language: zh_CN' \
  -H 'hc-platform: web' \
  -H 'lang: zh_CN' \
  -H 'origin: https://hibt.com' \
  -H 'platform: PC' \
  -H 'priority: u=1, i' \
  -H 'referer: https://hibt.com/' \
  -H 'sec-ch-ua: "Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "Windows"' \
  -H 'sec-fetch-dest: empty' \
  -H 'sec-fetch-mode: cors' \
  -H 'sec-fetch-site: cross-site' \
  -H 'sec-gpc: 1' \
  -H 'user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36' \
  -H 'authorization: eyJ1eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ8.eyJzdWIiOiJIT1RTLUNPSU4tSldUIiwiYXVkIjoibWVtYmVyIiwibmJmIjoxNzY3NzgzNzQyLCJpc3MiOiJBenVyZSIsImJvZHkiOnsidUlkIjoiMjA1NTMwOTU5MDAwMTUxNyIsImZVSWQiOjIxMTgyNCwicm9sZXMiOjEsImlwIjoiNTQwYTljYWNkYjcxMjQ4YzY4YThlZjBmMDkzYmI0MDciLCJBUElfTUVNQkVSIjoie1wiY2hhbm5lbElkXCI5MCxcImlkXCI6MjAxODI0LFwibWVtYmVyTGV2ZWxcIjpcIlJFQUxOQU1FXCIsXCJtZXJjaGFudFR5cGVcIjowLFwicGFydG5lclR4cGVcIjowLFwicHJvbW90aW9uQ29kZVwiOlwiRExMRFwiLFwicmVnaXN1ZXJUaW1lXCI6MTc2NzE0NjM1MzUxOCxcInN0YXR1c1wiOlwiTk9STUFMXCIsXCJ1SWRcIjoyMDQ1MzA5NTkwMDAxNTE4fSIsInBsYXRmb3JtIjoiUEMifSwiaWF0IjoxNzY3NzgzNzQyLCJqdGkiOiJlYjg5ZTZhZDI5N2U0MDY2OGQ2ZGFjYWRhYTJhNDllMyJ9.UM6ICcPCWct_sMYupzbIAaz667reqjSt6KxcYiLsb3s' \
  -H 'x-auth-token: eyJ1eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ8.eyJzdWIiOiJIT1RTLUNPSU4tSldUIiwiYXVkIjoibWVtYmVyIiwibmJmIjoxNzY3NzgzNzQyLCJpc3MiOiJBenVyZSIsImJvZHkiOnsidUlkIjoiMjA1NTMwOTU5MDAwMTUxNyIsImZVSWQiOjIxMTgyNCwicm9sZXMiOjEsImlwIjoiNTQwYTljYWNkYjcxMjQ4YzY4YThlZjBmMDkzYmI0MDciLCJBUElfTUVNQkVSIjoie1wiY2hhbm5lbElkXCI5MCxcImlkXCI6MjAxODI0LFwibWVtYmVyTGV2ZWxcIjpcIlJFQUxOQU1FXCIsXCJtZXJjaGFudFR5cGVcIjowLFwicGFydG5lclR4cGVcIjowLFwicHJvbW90aW9uQ29kZVwiOlwiRExMRFwiLFwicmVnaXN1ZXJUaW1lXCI6MTc2NzE0NjM1MzUxOCxcInN0YXR1c1wiOlwiTk9STUFMXCIsXCJ1SWRcIjoyMDQ1MzA5NTkwMDAxNTE4fSIsInBsYXRmb3JtIjoiUEMifSwiaWF0IjoxNzY3NzgzNzQyLCJqdGkiOiJlYjg5ZTZhZDI5N2U0MDY2OGQ2ZGFjYWRhYTJhNDllMyJ9.UM6ICcPCWct_sMYupzbIAaz667reqjSt6KxcYiLsb3s' \
  -X POST \
  -d 'amount=3&direction=1&symbol=btc_usdt&timeUnit=5&langCode=zh_CN'
```

Web 端的 `v`、 `Authorization` 和 `x-auth-token` 可在浏览器的开发者工具中获取，凭证有效期未知。

本项目使用 Python 实现，模拟 Web 端登录以获取 Web 端凭证并下单，用户使用需在 `config.json` 文件填写邮箱、密码和 TOTP 秘钥。

目前只实现账号的邮箱密码验证和 TOTP 双因素验证，其他形式验证请自行修改。

---
# 安装依赖

在项目根目录下，执行

```shell
pip install -r requirements.txt 
```

本项目需使用 Chrome/Chromium, 请确保安装无误，并配置好环境变量或在代码中指定浏览器路径。

---
# 运行

在项目根目录下，执行

```shell
python main.py
```

即可运行脚本，脚本会在当前目录下生成 `token.json` 文件保存 Web 端凭证信息（`v`、`Authorization`、`x-auth-token`）；用户可根据需要调用 `place_order_web()` 函数进行下单操作。