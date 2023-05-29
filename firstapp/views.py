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
            if isinstance(event, MessageEvent):
                message_dict = {}
                message_dict["user_id"] = event.source.user_id[:8]
                message_dict["message"] = event.message.text
                message_dict["sent_at"] = event.timestamp
                try:
                    message_dict["group_id"] = event.source.group_id
                except AttributeError:
                    message_dict["group_id"] = ""
                    pass

                resp_message = "用戶ID：" + message_dict["user_id"] + " 說：「" + message_dict["message"] + "」"
                table.append_row([message_dict["group_id"], message_dict["user_id"], message_dict["message"], message_dict["sent_at"]])

                line_bot_api.reply_message(event.reply_token,TextSendMessage(text=resp_message))
                
        return HttpResponse()
    else:
        return HttpResponseBadRequest()
