import os
from django.shortcuts import render
from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt

from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextSendMessage

from firstapp.functions import message_event_to_object, parse_prompt_into_dict, fetch_data_from_message_table, ask_ai_for_summarization

from datetime import datetime, timedelta

from firstapp.models import Message

import openai

line_bot_api = LineBotApi(settings.LINE_CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(settings.LINE_CHANNEL_SECRET)

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
                if event.message.type == "text" and event.message.text.startswith("總結") and is_in_group:
                    # print("執行總結")
                    prompts = parse_prompt_into_dict(event.message.text)
                    if prompts and prompts["days"] < 7:
                        if prompts["keywords"]:
                            resp_message = f"找出{prompts['days']}天內有關{prompts['keywords']}的訊息\n"
                        else:
                            resp_message = f"找出{prompts['days']}天內的重要訊息\n"
                        group_id = event.source.group_id
                        user_id = event.source.user_id
                        
                        data = fetch_data_from_message_table(group_id, user_id, prompts['days'])
                        chat_history = '\n'.join([f"{message.user_name}：{message.message}" for message in data])

                        print(chat_history)
                        ai_resp = ask_ai_for_summarization(chat_history, prompts['keywords'])
                        print(ai_resp)
                        resp_message = resp_message + ai_resp
                        message_obj = message_event_to_object(event, is_in_group, True)
                        message_obj.save()

                    else:
                        resp_message = "命令格式有誤，請輸入「總結 (天數選填) (關鍵字)」，如：「總結 3 重要 嚴重」或「總結 重要 嚴重」請用半形空格隔開。只能查詢7天以內的聊天訊息。"

                    line_bot_api.reply_message(event.reply_token,TextSendMessage(text=resp_message))

                else:
                    # 一般聊天訊息
                    message_obj = message_event_to_object(event, is_in_group)
                    
                    message_obj.save()
                    resp_message = event.message.text
                    # line_bot_api.reply_message(event.reply_token,TextSendMessage(text=resp_message))

            if event.type == "unsend":
                # 在unsent_at欄位加上時間戳記
                print(event)
                message = Message.objects.get(id=int(event.unsend.message_id))
                unsent_time = datetime.fromtimestamp(int(event.timestamp) / 1000.0)
                message.unsent_at = unsent_time
                message.save()
                
        return HttpResponse()
    else:
        return HttpResponseBadRequest()
