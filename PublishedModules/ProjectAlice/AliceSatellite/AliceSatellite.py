# -*- coding: utf-8 -*-

import json

import core.base.Managers as managers
from core.base.model.Intent import Intent
from core.base.model.Module import Module
from core.dialog.model.DialogSession import DialogSession


class AliceSatellite(Module):

	_INTENT_TEMPERATURE 	= Intent('GetTemperature')
	_INTENT_HUMIDITY 		= Intent('GetHumidity')
	_INTENT_CO2 			= Intent('GetCo2Level')
	_INTENT_PRESSURE 		= Intent('GetPressure')

	_FEEDBACK_SENSORS 		= 'projectAlice/devices/alice/sensorsFeedback'
	_DEVICE_DISCONNECTION 	= 'projectAlice/devices/alice/disconnection'

	def __init__(self):
		self._SUPPORTED_INTENTS	= [
			self._FEEDBACK_SENSORS,
			self._INTENT_TEMPERATURE,
			self._INTENT_HUMIDITY,
			self._INTENT_CO2,
			self._INTENT_PRESSURE,
			self._DEVICE_DISCONNECTION
		]

		self._temperatures 		= dict()
		self._sensorReadings 	= dict()

		managers.ProtectedIntentManager.protectIntent(self._FEEDBACK_SENSORS)
		managers.ProtectedIntentManager.protectIntent(self._DEVICE_DISCONNECTION)

		super().__init__(self._SUPPORTED_INTENTS)


	def onBooted(self):
		confManager = managers.ConfigManager
		if confManager.configAliceExists('onReboot') and confManager.getAliceConfigByName('onReboot') == 'greetAndRebootModules':
			self.restartDevice()


	def onSleep(self):
		self.broadcast('projectAlice/devices/sleep')


	def onWakeup(self):
		self.broadcast('projectAlice/devices/wakeup')


	def onGoingBed(self):
		self.broadcast('projectAlice/devices/goingBed')


	def onFullMinute(self):
		self.getSensorReadings()


	def onMessage(self, intent: str, session: DialogSession) -> bool:
		if not self.filterIntent(intent, session):
			return False

		sessionId = session.sessionId
		siteId = session.siteId
		slots = session.slots

		if 'Place' in slots:
			place = slots['Place']
		else:
			place = siteId

		if intent == self._INTENT_TEMPERATURE:
			temp = self.getSensorValue(place, 'temperature')

			if temp == 'undefined':
				return False

			if place != siteId:
				managers.MqttServer.endTalk(sessionId, managers.TalkManager.randomTalk('temperaturePlaceSpecific').format(place, temp.replace('.0', '')), client=siteId)
			else:
				managers.MqttServer.endTalk(sessionId, managers.TalkManager.randomTalk('temperature').format(temp.replace('.0', '')), client=siteId)

			return True

		elif intent == self._INTENT_HUMIDITY:
			humidity = self.getSensorValue(place, 'humidity')

			if humidity == 'undefined':
				return False
			else:
				humidity = int(round(float(humidity), 0))

			if place != siteId:
				managers.MqttServer.endTalk(sessionId, managers.TalkManager.randomTalk('humidityPlaceSpecific').format(place, humidity), client=siteId)
			else:
				managers.MqttServer.endTalk(sessionId, managers.TalkManager.randomTalk('humidity').format(humidity), client=siteId)

			return True

		elif intent == self._INTENT_CO2:
			co2 = self.getSensorValue(place, 'gas')

			if co2 == 'undefined':
				return False

			if place != siteId:
				managers.MqttServer.endTalk(sessionId, managers.TalkManager.randomTalk(self.name, 'co2PlaceSpecific').format(place, co2), client=siteId)
			else:
				managers.MqttServer.endTalk(sessionId, managers.TalkManager.randomTalk(self.name, 'co2').format(co2), client=siteId)

			return True

		elif intent == self._INTENT_PRESSURE:
			pressure = self.getSensorValue(place, 'pressure')

			if pressure == 'undefined':
				return False
			else:
				pressure = int(round(float(pressure), 0))

			if place != siteId:
				managers.MqttServer.endTalk(sessionId, managers.TalkManager.randomTalk('pressurePlaceSpecific').format(place, pressure), client=siteId)
			else:
				managers.MqttServer.endTalk(sessionId, managers.TalkManager.randomTalk('pressure').format(pressure), client=siteId)

			return True

		elif intent == self._FEEDBACK_SENSORS:
			payload = session.payload
			if 'data' in payload:
				self._sensorReadings[siteId] = payload['data']
			return True

		elif intent == self._DEVICE_DISCONNECTION:
			payload = session.payload
			if 'uid' in payload:
				managers.DeviceManager.deviceDisconnecting(payload['uid'])

		return False


	def getSensorReadings(self):
		self.broadcast('projectAlice/devices/alice/getSensors')


	def temperatureAt(self, siteId: str) -> str:
		return self.getSensorValue(siteId, 'temperature')


	def getSensorValue(self, siteId: str, value: str) -> str:
		if siteId not in self._sensorReadings.keys():
			return 'undefined'

		data = self._sensorReadings[siteId]
		if value in data:
			ret = data[value]
			return ret
		else:
			return 'undefined'


	def restartDevice(self):
		uids = managers.DeviceManager.getDeviceUidByType(deviceType=self.name, connectedOnly=True, onlyOne=False)
		if not uids:
			return

		for uid in uids:
			managers.MqttServer.publish(topic='projectAlice/devices/restart', payload=json.dumps({'uid': uid}))
