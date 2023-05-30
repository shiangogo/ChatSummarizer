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
            message_dict = {}
            col_labels = table.row_values(1)

            if event.type == "message":
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
                    keywords = ", ".join(event.message.keywords)
                    message_dict["message"] = f"（傳送了一個{keywords}的貼圖）"
                elif event.message.type == "image":
                    message_dict["message"] = "（傳送了一張圖片）"
                else:
                    message_dict["message"] = ""

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
