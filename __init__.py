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
from alsaaudio import Mixer

from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill, intent_handler
from mycroft.util.log import LOG
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler
from websocket import create_connection, WebSocket
from mycroft.messagebus.message import Message
from mycroft.api import DeviceApi
from mycroft.audio import wait_while_speaking
from mycroft.util.log import getLogger

logger = getLogger(__name__)
global_resp = ""
speak_tele = 0

__author__ = 'luke5sky'

class TelegramSkill(MycroftSkill):

    def __init__(self):
        super(TelegramSkill, self).__init__(name="TelegramSkill")

    def initialize(self):
        self.mute = self.settings.get('MuteIt','')
        self.mixer = Mixer()
        self.add_event('recognizer_loop:audio_output_start', self.muteHandler)
        user_id1 = self.settings.get('TeleID1', '')
        user_id2 = self.settings.get('TeleID2', '')
        #user_id3 = self.settings.get('TeleID3', '') # makes web-settings too crouded
        #user_id4 = self.settings.get('TeleID4', '') # makes web-settings too crouded
        chat_whitelist = [user_id1,user_id2] #,user_id3,user_id4] # makes web-settings too crouded
        # Get Bot Token from settings.json
        UnitName = DeviceApi().get()['name']
        MyCroftDevice1 = self.settings.get('MDevice1','')
        MyCroftDevice2 = self.settings.get('MDevice2','')
        bottoken = ""
        if MyCroftDevice1 == UnitName:
           logger.debug("found dev1 " + UnitName)
           bottoken = self.settings.get('TeleToken1', '')
        elif MyCroftDevice2 == UnitName:
           logger.debug("Found Dev2 " + UnitName)
           bottoken = self.settings.get('TeleToken2', '')
        else:
           logger.info("No or incorrect Device Name specified! Your DeviceName is: " + UnitName + " " + MyCroftDevice1 + " " + MyCroftDevice2)

        def TelegramMessages(bot, update):
            msg = update.message.text
            chat_id = str(update.message.chat_id)
            if chat_id in chat_whitelist:
               logger.info("Telegram-Message from User: " + msg)
               global speak_tele
               speak_tele = 1
               self.add_event('speak', responseHandler)
               sendMycroftUtt(msg)
               global global_resp
               mtime = time.time()
               count = 0 
               while len(global_resp) < 1:
               # TODO: make the following go away
               # Queen - Break free routine: not proud of it, move along 
                     if count > 5:
                        count = 0 # just in case
                        break
                     now = time.time()
                     count = now - mtime 
               # Let's not talk about this again... ever

               if len(global_resp) > 1:
                  bot.send_message(chat_id=chat_id, text=global_resp)
                  global_resp = ""
            else:
               logger.info("Chat ID " + user_id1 + " is not whitelisted, i don't process it")
               nowhite = ("This is your ChatID: " + chat_id)
               bot.send_message(chat_id=chat_id, text=nowhite)

        def sendMycroftUtt(msg):
            uri = 'ws://localhost:8181/core'
            ws = create_connection(uri)
            utt = '{"context": null, "type": "recognizer_loop:utterance", "data": {"lang": "en-us", "utterances": ["' + msg + '"]}}'
            ws.send(utt)
            ws.close()

        def responseHandler(message):
            global speak_tele
            if speak_tele == 1:
               telresp = message.data.get("utterance")
               logger.info("Response for Telegram-User: " + telresp )
               global global_resp
               global_resp = telresp
               self.remove_event('speak')
            
        # Connection to Telegram API
        self.telegram_updater = Updater(token=bottoken) # get telegram Updates
        self.telegram_dispatcher = self.telegram_updater.dispatcher
        receive_handler = MessageHandler(Filters.text, TelegramMessages)
        self.telegram_dispatcher.add_handler(receive_handler)
        self.telegram_updater.start_polling(clean=True) # start clean and look for messages

    def muteHandler(self, message):
        global speak_tele
        if self.mute == 'true' and speak_tele == 1:
           volume_level = self.mixer.getvolume()[0]
           self.mixer.setvolume(0)
           wait_while_speaking()
           self.mixer.setvolume(volume_level)
           speak_tele = 0

    def shutdown(self): # shutdown routine
        self.telegram_updater.stop() # will stop update and dispatcher
        self.telegram_updater.is_idle = False
        super(TelegramSkill, self).shutdown()

    def stop(self):
        global speak_tele
        speak_tele = 0
        global global_resp 
        global_resp = ""

def create_skill():
    return TelegramSkill()
