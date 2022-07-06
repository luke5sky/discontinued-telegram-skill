# Copyright 2020 Lukas Gangel
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


import telegram
import urllib
from telegram import Update, Voice

from alsaaudio import Mixer
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import LOG
from mycroft.api import DeviceApi
from mycroft.stt import MycroftSTT
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler
from websocket import create_connection, WebSocket
from mycroft.messagebus.message import Message
from speech_recognition import AudioData
from deepspeech import Model, version

from mycroft.audio import wait_while_speaking
from mycroft.client.speech.word_extractor import WordExtractor
from mycroft.util.log import getLogger

logger = getLogger(__name__)

speak_tele = 0
loaded = 0

__author__ = 'luke5sky'

class TelegramSkill(MycroftSkill):
    def __init__(self):
        super(TelegramSkill, self).__init__(name="TelegramSkill")
        self.api = MycroftSTT()

    def initialize(self):
        self.telegram_updater = None
        self.mute = str(self.settings.get('MuteIt',''))
        if (self.mute == 'True') or (self.mute == 'true'):
           try:
               self.mixer = Mixer()
               msg = "Telegram Messages will temporary Mute Mycroft"
               logger.info(msg)
           except:
               msg = "There is a problem with alsa audio, mute is not working!"
               logger.info("There is a problem with alsaaudio, mute is not working!")
               self.sendMycroftSay(msg)
               self.mute = 'false'
        else:
           logger.info("Telegram: Muting is off")
           self.mute = "false"
        self.add_event('telegram-skill:response', self.sendHandler)
        self.add_event('speak', self.responseHandler)
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
           msg = ("No or incorrect Device Name specified! Your DeviceName is: " + UnitName)
           logger.info(msg)
           self.sendMycroftSay(msg)

        # Connection to Telegram API
        try:
           self.telegram_updater = Updater(token=self.bottoken, use_context=True) # get telegram Updates
           self.telegram_dispatcher = self.telegram_updater.dispatcher
           receive_handler = MessageHandler((Filters.voice | Filters.text), self.TelegramMessages) # TODO: Make audio Files as Input possible: Filters.text | Filters.audio
           self.telegram_dispatcher.add_handler(receive_handler)
           self.telegram_updater.start_polling(clean=True) # start clean and look for messages
           wbot = telegram.Bot(token=self.bottoken)
        except:
           pass
        global loaded # get global variable
        if loaded == 0: # check if bot is just started
           loaded = 1 # make sure that users gets this message only once bot is newly loaded
           if self.mute == "false":
              msg = "Telegram Skill is loaded"
              self.sendMycroftSay(msg)
           loadedmessage = "Telegram-Skill on Mycroft Unit \""+ UnitName + "\" is loaded and ready to use!" # give User a nice message
           try:
              wbot.send_message(chat_id=user_id1, text=loadedmessage) # send welcome message to user 1
           except:
              pass             
           try:
              wbot.send_message(chat_id=user_id2, text=loadedmessage) # send welcome message to user 2
           except:
              pass
#           wbot.send_message(chat_id=user_id1, text=loadedmessage) # send welcome message to user 3
#           wbot.send_message(chat_id=user_id1, text=loadedmessage) # send welcome message to user 4

    def TelegramMessages(self, update, context):
        is_voice_message = not update.message.text and hasattr(update.message, 'voice')
        chat_id_test = update.message.chat_id
        self.chat_id = str(update.message.chat_id)
        if is_voice_message:
            msg = self.text_from_audio_file(update.message.voice)
        else:
            msg = update.message.text

        if self.chat_whitelist.count(chat_id_test) > 0 :
           global speak_tele
           speak_tele = 1
           logger.info("Telegram-Message from User: " + msg)
           msg = msg.replace('\\', ' ').replace('\"', '\\\"').replace('(', ' ').replace(')', ' ').replace('{', ' ').replace('}', ' ')
           msg = msg.casefold() # some skills need lowercase (eg. the cows list)
           self.add_event('recognizer_loop:audio_output_start', self.muteHandler)
           self.sendMycroftUtt(msg)

        else:
           logger.info("Chat ID " + self.chat_id + " is not whitelisted, i don't process it")
           nowhite = ("This is your ChatID: " + self.chat_id)
           context.bot.send_message(chat_id=self.chat_id, text=nowhite)

    def text_from_audio_file(self, voice):
        get_file = urllib.request.urlopen(voice.get_file().file_path).read()
        ds = Model('dataset/deepspeech-0.9.3-models.pbmm')
        ds.enableExternalScorer('dataset/deepspeech-0.9.3-models.scorer')
        fs_orig = get_file.getframerate()
        desired_sample_rate = ds.sampleRate()
        print(fs_orig != desired_sample_rate)
        text = self.api.execute(get_file.read(),"en-us")
        logger.info("It's audio")
        logger.info(text)
        self.sendMycroftSay("WOW ITS VOICE!!!")
        return '12'

    def sendMycroftUtt(self, msg):
        uri = 'ws://localhost:8181/core'
        ws = create_connection(uri)
        utt = '{"context": null, "type": "recognizer_loop:utterance", "data": {"lang": "' + self.lang + '", "utterances": ["' + msg + '"]}}'
        ws.send(utt)
        ws.close()

    def sendMycroftSay(self, msg):
        uri = 'ws://localhost:8181/core'
        ws = create_connection(uri)
        msg = "say " + msg
        utt = '{"context": null, "type": "recognizer_loop:utterance", "data": {"lang": "' + self.lang + '", "utterances": ["' + msg + '"]}}'
        logger.info("Lang IS: " + self.lang)
        ws.send(utt)
        ws.close()

    def responseHandler(self, message):
        global speak_tele
        if speak_tele == 1:
           speak_tele = 0
           response = message.data.get("utterance")
           self.bus.emit(Message("telegram-skill:response", {"intent_name": "telegram-response", "utterance": response }))

    def sendHandler(self, message):
        sendData = message.data.get("utterance")
        logger.info("Sending to Telegram-User: " + sendData ) 
        sendbot = telegram.Bot(token=self.bottoken)
        sendbot.send_message(chat_id=self.chat_id, text=sendData)
    
    def muteHandler(self, message):
        global speak_tele
        if (self.mute == 'true') or (self.mute == 'True'):
           self.mixer.setmute(1)
           wait_while_speaking()
           self.mixer.setmute(0)
        self.remove_event('recognizer_loop:audio_output_start')

    def shutdown(self): # shutdown routine
        if self.telegram_updater is not None:
            self.telegram_updater.stop() # will stop update and dispatcher
            self.telegram_updater.is_idle = False
        global speak_tele
        speak_tele = 0
        super(TelegramSkill, self).shutdown()

    def stop(self):
        global speak_tele
        speak_tele = 0

def create_skill():
    return TelegramSkill()
