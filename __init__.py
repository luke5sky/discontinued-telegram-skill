# Copyright 2018 Lukas Gangel
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# TODO: Documentation

import os
import re
import logging
import sys
import time


from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill, intent_handler
from mycroft.util.log import LOG
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler
from websocket import create_connection, WebSocket
from mycroft.messagebus.message import Message


__author__ = 'luke5sky'

class TelegramSkill(MycroftSkill):

    def __init__(self):
        super(TelegramSkill, self).__init__(name="TelegramSkill")

        user_id1 = self.settings.get('TeleID1', '')
        user_id2 = self.settings.get('TeleID2', '')
        user_id3 = self.settings.get('TeleID3', '')
        user_id4 = self.settings.get('TeleID4', '')
        chat_whitelist = [user_id1,user_id2,user_id3,user_id4]
#	    get_intro_message()
################################################################################
        def telegramMessages(bot, update):
            msg = update.message.text
            chat_id = update.message.chat_id
            
            if chat_id in chat_whitelist:
               print("Telegram-Message from User: " + msg)
               uri = 'ws://localhost:8181/core'
               ws = create_connection(uri)
               utt = '{"context": null, "type": "recognizer_loop:utterance", "data": {"lang": "en-us", "utterances": ["' + msg + '"]}}'
               
               if not chat_id in chat_whitelist:
                  print("WHITECHat_ID is: %d" % chat_id)
               ws.send(utt)
 #              def handle_listener_started(self):
 #                  print("listener started wupdidudl: ")
 #              self.add_event('recognizer_loop:utterance', handle_listener_started)
               mtime = time.time()
               count = 0
               while count < 10:
                     test_resp = ws.recv()
                     if ('"utterance"' in test_resp) and ('"speak"' in test_resp):
                #        print("Found response: " + test_resp)
                        response = re.sub(".*utterance\":\s\"([\w\s'(),.;:?!]+)\".*", r"\1", test_resp)
                        print("Response to Telegram Message found: " + response)
                        bot.send_message(chat_id=chat_id, text=response)
                        mtime = time.time()
                        break
                     now = time.time()
                     count = now - mtime
               ws.close()
            else:
               print("Chat ID is not whitelisted, i don't process it")
               nowhite = ("This is your ChatID: %d" % chat_id)
               bot.send_message(chat_id=chat_id, text=nowhite)
################################################################################

        # Get Bot Token from settings.json
        bottoken = self.settings.get('TeleToken', '')

        # Connection to Telegram API
        self.telegram_updater = Updater(token=bottoken) # get telegram Updates
        telegram_dispatcher = self.telegram_updater.dispatcher
       # logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.WARNING)
        start_handler = MessageHandler(Filters.text, telegramMessages)
        telegram_dispatcher.add_handler(start_handler)
        self.telegram_updater.start_polling(clean=True) # start clean and look for messages

    def shutdown(self): # shutdown routine
        self.telegram_updater.stop() # stop updater
        self.telegram_updater.is_idle = False
        super(TelegramSkill, self).shutdown()

    def stop(self):
        pass

def create_skill():
    return TelegramSkill()
