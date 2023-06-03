import os
from django.shortcuts import render
from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt

from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextSendMessage

from datetime import datetime, timedelta

from firstapp.models import Message


line_bot_api = LineBotApi(settings.LINE_CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(settings.LINE_CHANNEL_SECRET)

def message_event_to_object(event, is_in_group):
    message_obj = Message()
    if is_in_group:
        message_obj.group_id = event.source.group_id
        message_obj.group_name = line_bot_api.get_group_summary(event.source.group_id).group_name
        message_obj.user_name = line_bot_api.get_group_member_profile(event.source.group_id, event.source.user_id).display_name
    else:
        message_obj.group_id = None
        message_obj.group_name = None
        message_obj.user_name = line_bot_api.get_profile(event.source.user_id).display_name

    message_obj.id = int(event.message.id)
    message_obj.user_id = event.source.user_id
    message_obj.sent_at = datetime.fromtimestamp(int(event.timestamp) / 1000.0) + timedelta(hours=8)
    message_obj.unsent_at = None

    if event.message.type == "text":
        message_obj.message = event.message.text
    elif event.message.type == "sticker":
        sticker_keywords = ", ".join(event.message.keywords)
        message_obj.message = f"（傳送了一個{sticker_keywords}的貼圖）"
    elif event.message.type == "image":
        message_obj.message = "（傳送了一張圖片）"
    else:
        message_obj.message = None

    return message_obj


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

def fetch_data_from_message_table(group_id, days):
    #TODO
    return


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
                    # 一般聊天訊息
                    message_obj = message_event_to_object(event, is_in_group)
                    
                    message_obj.save()
                    # line_bot_api.reply_message(event.reply_token,TextSendMessage(text=resp_message))

            if event.type == "unsend":
                # 在unsent_at欄位加上時間戳記
                print(event)
                message = Message.objects.get(id=int(event.unsend.message_id))
                unsent_time = datetime.fromtimestamp(int(event.timestamp) / 1000.0) + timedelta(hours=8)
                message.unsent_at = unsent_time
                message.save()
                
        return HttpResponse()
    else:
        return HttpResponseBadRequest()
