import os, json
from flask import Flask, request, abort
from dotenv import load_dotenv

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

load_dotenv()
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")
CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
print(repr(CHANNEL_SECRET))
ADMIN_USER_IDS = [u.strip() for u in os.getenv("ADMIN_USER_IDS", "").split(",") if u.strip()]
TRIGGER_TEXT = os.getenv("TRIGGER_TEXT", "混んでる？")

app = Flask(__name__)
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

STATUS_FILE = "status.json"
print("🚀 CHANNEL_SECRET =", repr(CHANNEL_SECRET))

def read_status():
    if not os.path.exists(STATUS_FILE):
        return {"status": "未設定", "message": "現在の状況は未設定です。"}
    with open(STATUS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def write_status(s):
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False)

@app.route("/", methods=["GET"])
def health():
    return "OK"

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)

    print("[DEBUG] Signature:", signature)
    print("[DEBUG] Request Body:", body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError as e:
        print("[ERROR] Invalid Signature Error:", e)
        abort(400)
    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def on_message(event: MessageEvent):
    user_id = event.source.user_id
    text = event.message.text.strip()
    print("[DEBUG] user_id:", user_id)
    print("[DEBUG] 受信テキスト:", repr(text))
    print("[DEBUG] TRIGGER_TEXT:", repr(TRIGGER_TEXT))

    # 管理者コマンド
    if text.startswith("#"):
        if user_id in ADMIN_USER_IDS:
            cmd = text[1:].strip()
            templates = {
                "満席": "ただいま満席です。お時間を空けてのご来店をお願いします。",
                "空席": "空席あり。すぐにご案内できます。",
                "やや混雑": "やや混雑中。少しお待ちいただく場合があります。",
                "休業": "本日は休業日です。またのご来店をお待ちしています。",
                "貸切": "ただいま貸切営業中です。再開までお待ちください。",
                "再開": "貸切営業、終わりました。ご来店をお待ちしています。",
                "閉店": "営業時間外です。"
            }
            if cmd in templates:
                write_status({"status": cmd, "message": templates[cmd]})
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=f"更新しました：{cmd}")
                )
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="未対応のコマンドです（#満席 / #空席 / #やや混雑 / #休業）")
                )
        return

    # 「混んでる？」に応答
    if text == TRIGGER_TEXT:
        s = read_status()
        msg = s.get("message", "現在の状況は未設定です。")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))
        return

    # デフォルト応答
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=f"「{TRIGGER_TEXT}」と送ると最新の混雑状況をお知らせします。")
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)

