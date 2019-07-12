# -*- coding: utf-8 -*-

import json
import RPi.GPIO as GPIO
import core.base.Managers as managers
from core.base.model.Intent import Intent
from core.base.model.Module import Module
from core.dialog.model.DialogSession import DialogSession


class LocalButtonPress(Module):
    """
    Author: mjlill
    Description: Press an imaginary button on or off
    """

    _INTENT_BUTTON_ON   = Intent('DoButtonOn')
    _INTENT_BUTTON_OFF      = Intent('DoButtonOff')
    _LIGHT_PIN         = 4

    def __init__(self):
        self._SUPPORTED_INTENTS   = [
            self._INTENT_BUTTON_ON,
            self._INTENT_BUTTON_OFF
        ]
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self._LIGHT_PIN, GPIO.OUT)
        GPIO.output(self._LIGHT_PIN, GPIO.LOW)

        super().__init__(self._SUPPORTED_INTENTS)


    def onMessage(self, intent: str, session: DialogSession) -> bool:
        if not self.filterIntent(intent, session):
            return False

        sessionId = session.sessionId
        siteId = session.siteId

        if intent == self._INTENT_BUTTON_ON:
            GPIO.output(self._LIGHT_PIN, GPIO.HIGH)
            managers.MqttServer.endTalk(sessionId, managers.TalkManager.randomTalk('DoButtonOn'), client=siteId)

        elif intent == self._INTENT_BUTTON_OFF:
            GPIO.output(self._LIGHT_PIN, GPIO.LOW)
            managers.MqttServer.endTalk(sessionId, managers.TalkManager.randomTalk('DoButtonOff'), client=siteId)

        return True
