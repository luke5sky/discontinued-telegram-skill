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
import threading
import telegram

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

speak_tele = 0

__author__ = 'luke5sky'

class TelegramSkill(MycroftSkill):

    def __init__(self):
        super(TelegramSkill, self).__init__(name="TelegramSkill")

    def initialize(self):
        self.mute = self.settings.get('MuteIt','')
        self.mixer = Mixer()
        self.add_event('telegram-skill:response', self.sendHandler)
        self.add_event('speak', self.responseHandler)
        self.add_event('recognizer_loop:utterance', self.uttHandler)
        user_id1 = self.settings.get('TeleID1', '')
        user_id2 = self.settings.get('TeleID2', '')
        #user_id3 = self.settings.get('TeleID3', '') # makes web-settings too crouded
        #user_id4 = self.settings.get('TeleID4', '') # makes web-settings too crouded
        self.chat_whitelist = [user_id1,user_id2] #,user_id3,user_id4] # makes web-settings too crouded
        # Get Bot Token from settings.json
        UnitName = DeviceApi().get()['name']
        MyCroftDevice1 = self.settings.get('MDevice1','')
        MyCroftDevice2 = self.settings.get('MDevice2','')
        self.bottoken = ""
        if MyCroftDevice1 == UnitName:
           logger.debug("Found MyCroft Unit 1: " + UnitName)
           self.bottoken = self.settings.get('TeleToken1', '')
        elif MyCroftDevice2 == UnitName:
           logger.debug("Found MyCroft Unit 2: " + UnitName)
           self.bottoken = self.settings.get('TeleToken2', '')
        else:
           logger.info("No or incorrect Device Name specified! Your DeviceName is: " + UnitName)

        # Connection to Telegram API
        self.telegram_updater = Updater(token=self.bottoken) # get telegram Updates
        self.telegram_dispatcher = self.telegram_updater.dispatcher
        receive_handler = MessageHandler(Filters.text, self.TelegramMessages)
        self.telegram_dispatcher.add_handler(receive_handler)
        self.telegram_updater.start_polling(clean=True) # start clean and look for messages

    def TelegramMessages(self, bot, update):
        msg = update.message.text
        self.chat_id = str(update.message.chat_id)
        if self.chat_id in self.chat_whitelist:
           global speak_tele
           speak_tele = 1
           logger.info("Telegram-Message from User: " + msg)
           self.add_event('recognizer_loop:audio_output_start', self.muteHandler)
           self.sendMycroftUtt(msg)
          
        else:
           logger.info("Chat ID " + self.chat_id + " is not whitelisted, i don't process it")
           nowhite = ("This is your ChatID: " + self.chat_id)
           bot.send_message(chat_id=self.chat_id, text=nowhite)    

    def sendMycroftUtt(self, msg):
        uri = 'ws://localhost:8181/core'
        ws = create_connection(uri)
        utt = '{"context": null, "type": "recognizer_loop:utterance", "data": {"lang": "' + self.lang + '", "utterances": ["' + msg + '"]}}'
        ws.send(utt)
        ws.close()

    def responseHandler(self, message):
        global speak_tele
        if speak_tele == 1:
           speak_tele = 0
           response = message.data.get("utterance")
           self.emitter.emit(Message("telegram-skill:response", {"intent_name": "telegram-response", "utterance": response }))

    def sendHandler(self, message):
        sendData = message.data.get("utterance")
        logger.info("Sending to Telegram-User: " + sendData ) 
        sendbot = telegram.Bot(token=self.bottoken)
        sendbot.send_message(chat_id=self.chat_id, text=sendData)
    
    def muteHandler(self, message):
        global speak_tele
        if self.mute == 'true':
           volume_level = self.mixer.getvolume()[0]
           self.mixer.setvolume(0)
           wait_while_speaking()
           self.mixer.setvolume(volume_level)
           del volume_level
           self.remove_event('recognizer_loop:audio_output_start')

    def shutdown(self): # shutdown routine
        self.telegram_updater.stop() # will stop update and dispatcher
        self.telegram_updater.is_idle = False
        super(TelegramSkill, self).shutdown()

    def stop(self):
        global speak_tele
        speak_tele = 0

def create_skill():
    return TelegramSkill()
