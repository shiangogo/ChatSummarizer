from django.shortcuts import render
from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt

from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextSendMessage

from datetime import datetime

import gspread

line_bot_api = LineBotApi(settings.LINE_CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(settings.LINE_CHANNEL_SECRET)

service_account = gspread.service_account(filename=settings.GDOCS_OAUTH_JSON)
db = service_account.open(settings.GDOCS_SPREADSHEET_NAME)
table = db.worksheet(settings.GDOCS_WORKSHEET_NAME)

def message_handler(event, is_in_group):
    message_dict = {}
    if is_in_group:
        message_dict["group_id"] = event.source.group_id
        message_dict["group_name"] = line_bot_api.get_group_summary(event.source.group_id).group_name
        message_dict["user_name"] = line_bot_api.get_group_member_profile(message_dict["group_id"], event.source.user_id).display_name
    else:
        message_dict["group_id"] = ""
        message_dict["group_name"] = ""
        message_dict["user_name"] = line_bot_api.get_profile(event.source.user_id).display_name

    message_dict["id"] = event.message.id
    message_dict["user_id"] = event.source.user_id
    message_dict["sent_at"] = event.timestamp
    message_dict["unsent_at"] = ""

    if event.message.type == "text":
        message_dict["message"] = event.message.text
    elif event.message.type == "sticker":
        sticker_keywords = ", ".join(event.message.keywords)
        message_dict["message"] = f"（傳送了一個{sticker_keywords}的貼圖）"
    elif event.message.type == "image":
        message_dict["message"] = "（傳送了一張圖片）"
    else:
        message_dict["message"] = ""
    return message_dict

def parse_prompt_into_list(text):
    split_text = text.split()
    if split_text[0] != "總結":
        return False
    elif len(split_text) >= 3 and split_text[0] == "總結" and split_text[1].isdigit():
        days = split_text[1]
        keywords = "、".join(split_text[2:])
    elif len(split_text) == 2 and split_text[0] == "總結" and split_text[1].isdigit():
        days = split_text[1]
        keywords = None
    else:
        days = 1
        keywords = "、".join(split_text[1:])
    return {"days":days, "keywords":keywords}

@csrf_exempt
def callback(request):
    if request.method == 'POST':
        signature = request.META['HTTP_X_LINE_SIGNATURE']
        body = request.body.decode('utf-8')
        
        try:
            events = parser.parse(body, signature)
        except InvalidSignatureError:
            return HttpResponseForbidden()
        except LineBotApiError:
            return HttpResponseBadRequest()

        for event in events:
            print(event)
            is_in_group = event.source.type == "group"
            col_labels = table.row_values(1)

            if event.type == "message":
                if event.message.type == "text" and event.message.text.startswith("總結"):
                    print("執行總結")
                    prompts = parse_prompt_into_list(event.message.text)
                    if prompts:
                        resp_message = f"找出{prompts['days']}天內有關{prompts['keywords']}的訊息"
                    else:
                        resp_message = "命令格式有誤，請輸入「總結 (天數選填) (關鍵字)」，如：「總結 3 重要 嚴重」或「總結 重要 嚴重」請用半形空格隔開！"

                    line_bot_api.reply_message(event.reply_token,TextSendMessage(text=resp_message))

                else:
                    message_dict = message_handler(event, is_in_group)

                    table.append_row([message_dict.get(key) for key in ["id", "group_id", "group_name", "user_id", "user_name", "message", "sent_at", "unsent_at"]])

                    # resp_message = message_dict["message"]
                    # line_bot_api.reply_message(event.reply_token,TextSendMessage(text=resp_message))
            if event.type == "unsend":
                try:
                    unsent_at_index = col_labels.index("unsent_at") + 1
                    cell = table.find(event.unsend.message_id)
                    table.update_cell(cell.row, unsent_at_index, event.timestamp)
                except:
                    pass
                
        return HttpResponse()
    else:
        return HttpResponseBadRequest()
