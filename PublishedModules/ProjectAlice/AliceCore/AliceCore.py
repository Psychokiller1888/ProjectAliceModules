# -*- coding: utf-8 -*-

import getpass
import json
import subprocess
import time
from zipfile import ZipFile

import core.base.Managers as managers
from core.ProjectAliceExceptions import ConfigurationUpdateFailed, LanguageManagerLangNotSupported, ModuleStartDelayed
from core.base.model.Intent import Intent
from core.base.model.Module import Module
from core.commons import commons
from core.dialog.model.DialogSession import DialogSession


class AliceCore(Module):
	_DEVING_CMD = 'projectAlice/deving'

	_INTENT_MODULE_GREETING = 'projectAlice/devices/greeting'
	_INTENT_ANSWER_YES_OR_NO = Intent('AnswerYesOrNo', isProtected=True)
	_INTENT_ANSWER_ROOM = Intent('AnswerRoom', isProtected=True)
	_INTENT_SWITCH_LANGUAGE = Intent('SwitchLanguage')
	_INTENT_UPDATE_BUNDLE = Intent('UpdateAssistantBundle', isProtected=True)
	_INTENT_REBOOT = Intent('RebootSystem')
	_INTENT_INVADE_SONOS = Intent('InvadeSonos')
	_INTENT_RETREAT = Intent('RetreatSonos')
	_INTENT_STOP_LISTEN = Intent('StopListening')
	_INTENT_ADD_DEVICE = Intent('AddComponent')
	_INTENT_ANSWER_HARDWARE_TYPE = Intent('AnswerHardwareType', isProtected=True)
	_INTENT_ANSWER_ESP_TYPE = Intent('AnswerEspType', isProtected=True)
	_INTENT_ANSWER_NAME = Intent('AnswerName', isProtected=True)
	_INTENT_SPELL_WORD = Intent('SpellWord', isProtected=True)
	_INTENT_DUMMY_ADD_USER = Intent('Dummy', isProtected=True)


	def __init__(self):
		self._SUPPORTED_INTENTS = [
			self._INTENT_MODULE_GREETING,
			self._INTENT_ANSWER_YES_OR_NO,
			self._INTENT_ANSWER_ROOM,
			self._INTENT_SWITCH_LANGUAGE,
			self._INTENT_UPDATE_BUNDLE,
			self._INTENT_REBOOT,
			self._INTENT_INVADE_SONOS,
			self._INTENT_RETREAT,
			self._INTENT_STOP_LISTEN,
			self._DEVING_CMD,
			self._INTENT_ADD_DEVICE,
			self._INTENT_ANSWER_HARDWARE_TYPE,
			self._INTENT_ANSWER_ESP_TYPE,
			self._INTENT_ANSWER_NAME,
			self._INTENT_SPELL_WORD,
			self._INTENT_DUMMY_ADD_USER
		]

		self._threads = {}
		super().__init__(self._SUPPORTED_INTENTS)


	def onStart(self):
		self.changeFeedbackSound(inDialog=False)

		if not managers.UserManager.users:
			if not self.delayed:
				self._logger.warning('[{}] No user found in database'.format(self.name))
				raise ModuleStartDelayed(self.name)
			else:
				self._addFirstUser()
		else:
			return super().onStart()


	def _addFirstUser(self):
		managers.MqttServer.ask(
			text=managers.TalkManager.randomTalk('addAdminUser'),
			intentFilter=[self._INTENT_ANSWER_NAME, self._INTENT_SPELL_WORD],
			previousIntent=self._INTENT_DUMMY_ADD_USER
		)


	def onUserCancel(self, session: DialogSession):
		if self.delayed:
			managers.MqttServer.say(
				text=managers.TalkManager.randomTalk('noStartWithoutAdmin'),
				client=session.siteId
			)
			self.delayed = False


			def stop():
				subprocess.run(['sudo', 'systemctl', 'stop', 'ProjectAlice'])


			managers.ThreadManager.doLater(interval=10, func=stop)


	def onSessionTimeout(self, session: DialogSession):
		if self.delayed:
			self._addFirstUser()


	def onSessionError(self, session: DialogSession):
		if self.delayed:
			self._addFirstUser()


	def onSessionStarted(self, session: DialogSession):
		self.changeFeedbackSound(inDialog=True)


	def onSessionEnded(self, session: DialogSession):
		self.changeFeedbackSound(inDialog=False)

		if self.delayed:
			self._addFirstUser()


	def onSleep(self):
		managers.MqttServer.toggleFeedbackSounds('off')


	def onWakeup(self):
		managers.MqttServer.toggleFeedbackSounds('on')


	def onBooted(self):
		if not super().onBooted():
			return

		onReboot = managers.ConfigManager.getAliceConfigByName('onReboot')
		if onReboot:
			if onReboot == 'greet':
				managers.ThreadManager.doLater(
					interval=3,
					func=managers.MqttServer.say,
					args=[managers.TalkManager.randomTalk('confirmRebooted'), 'all']
				)
			elif onReboot == 'greetAndRebootModules':
				managers.ThreadManager.doLater(
					interval=3,
					func=managers.MqttServer.say,
					args=[managers.TalkManager.randomTalk('confirmRebootingModules'), 'all']
				)
			else:
				self._logger.warning('[{}] onReboot config has an unknown value'.format(self.name))

			managers.ConfigManager.updateAliceConfiguration('onReboot', '')
		else:
			managers.ThreadManager.doLater(
				interval=3,
				func=managers.MqttServer.playSound,
				args=[
					self.getResource(self.name, 'sounds/boot.wav'),
					'boot-session-id',
					True,
					'all'
				]
			)


	def onGoingBed(self):
		managers.UserManager.goingBed()


	def onLeavingHome(self):
		managers.UserManager.leftHome()


	def onReturningHome(self):
		managers.UserManager.home()


	def onSnipsAssistantDownloaded(self, *args):
		try:
			with ZipFile('/tmp/assistant.zip') as zipfile:
				zipfile.extractall('/tmp')

			subprocess.run(['sudo', 'rm', '-rf', commons.rootDir() + '/trained/assistants/assistant_{}'.format(managers.LanguageManager.activeLanguage)])
			subprocess.run(['sudo', 'cp', '-R', '/tmp/assistant', commons.rootDir() + '/trained/assistants/assistant_{}'.format(managers.LanguageManager.activeLanguage)])
			subprocess.run(['sudo', 'chown', '-R', getpass.getuser(), commons.rootDir() + '/trained/assistants/assistant_{}'.format(managers.LanguageManager.activeLanguage)])

			subprocess.run(['sudo', 'ln', '-sfn', commons.rootDir() + '/trained/assistants/assistant_{}'.format(managers.LanguageManager.activeLanguage), commons.rootDir() + '/assistant'])
			subprocess.run(['sudo', 'ln', '-sfn', commons.rootDir() + '/system/sounds/{}/start_of_input.wav'.format(managers.LanguageManager.activeLanguage), commons.rootDir() + '/assistant/custom_dialogue/sound/start_of_input.wav'])
			subprocess.run(['sudo', 'ln', '-sfn', commons.rootDir() + '/system/sounds/{}/end_of_input.wav'.format(managers.LanguageManager.activeLanguage), commons.rootDir() + '/assistant/custom_dialogue/sound/end_of_input.wav'])
			subprocess.run(['sudo', 'ln', '-sfn', commons.rootDir() + '/system/sounds/{}/error.wav'.format(managers.LanguageManager.activeLanguage), commons.rootDir() + '/assistant/custom_dialogue/sound/error.wav'])

			managers.SnipsServicesManager.runCmd('restart')

			managers.MqttServer.say(
				text=managers.TalkManager.randomTalk('confirmBundleUpdate')
			)
		except:
			managers.MqttServer.say(
				text=managers.TalkManager.randomTalk('bundleUpdateFailed')
			)


	def onSnipsAssistantDownloadFailed(self, *args):
		managers.MqttServer.say(
			text=managers.TalkManager.randomTalk('bundleUpdateFailed')
		)


	def onMessage(self, intent: str, session: DialogSession) -> bool:
		if not self.filterIntent(intent, session):
			return False

		siteId = session.siteId
		slots = session.slots
		slotsObj = session.slotsAsObjects
		sessionId = session.sessionId
		customData = session.customData
		payload = session.payload

		if intent == self._INTENT_ADD_DEVICE or session.previousIntent == self._INTENT_ADD_DEVICE:
			if managers.DeviceManager.isBusy():
				managers.MqttServer.endTalk(
					sessionId=sessionId,
					text=managers.TalkManager.randomTalk('busy')
				)
				return True

			if 'Hardware' not in slots:
				managers.MqttServer.continueDialog(
					sessionId=sessionId,
					text=managers.TalkManager.randomTalk('whatHardware'),
					intentFilter=[self._INTENT_ANSWER_HARDWARE_TYPE, self._INTENT_ANSWER_ESP_TYPE],
					previousIntent=self._INTENT_ADD_DEVICE
				)
				return True

			elif slotsObj['Hardware'][0].value['value'] == 'esp' and 'EspType' not in slots:
				managers.MqttServer.continueDialog(
					sessionId=sessionId,
					text=managers.TalkManager.randomTalk('whatESP'),
					intentFilter=[self._INTENT_ANSWER_HARDWARE_TYPE, self._INTENT_ANSWER_ESP_TYPE],
					previousIntent=self._INTENT_ADD_DEVICE
				)
				return True

			elif 'Room' not in slots:
				managers.MqttServer.continueDialog(
					sessionId=sessionId,
					text=managers.TalkManager.randomTalk('whichRoom'),
					intentFilter=[self._INTENT_ANSWER_ROOM],
					previousIntent=self._INTENT_ADD_DEVICE
				)
				return True

			hardware = slotsObj['Hardware'][0].value['value']
			if hardware == 'esp':
				if not managers.ModuleManager.isModuleActive('Tasmota'):
					managers.MqttServer.endTalk(
						sessionId=sessionId,
						text=managers.TalkManager.randomTalk('requireTasmotaModule')
					)
					return True

				if managers.DeviceManager.isBusy():
					managers.MqttServer.endTalk(
						sessionId=sessionId,
						text=managers.TalkManager.randomTalk('busy')
					)
					return True

				if not managers.DeviceManager.startTasmotaFlashingProcess(commons.cleanRoomNameToSiteId(slots['Room']), slotsObj['EspType'][0].value['value'], session):
					managers.MqttServer.endTalk(
						sessionId=sessionId,
						text=managers.TalkManager.randomTalk('espFailed')
					)

			elif hardware == 'satellite':
				if managers.DeviceManager.startBroadcastingForNewDevice(commons.cleanRoomNameToSiteId(slots['Room']), siteId):
					managers.MqttServer.endTalk(
						sessionId=sessionId,
						text=managers.TalkManager.randomTalk('confirmDeviceAddingMode')
					)
				else:
					managers.MqttServer.endTalk(
						sessionId=sessionId,
						text=managers.TalkManager.randomTalk('busy')
					)
			else:
				managers.MqttServer.continueDialog(
					sessionId=sessionId,
					text=managers.TalkManager.randomTalk('unknownHardware'),
					intentFilter=[self._INTENT_ANSWER_HARDWARE_TYPE],
					previousIntent=self._INTENT_ADD_DEVICE,
				)
				return True

		elif intent == self._INTENT_MODULE_GREETING:
			if 'uid' not in payload or 'siteId' not in payload:
				self._logger.warning('A device tried to connect but is missing informations in the payload, refused')
				managers.MqttServer.publish(
					topic='projectAlice/devices/connectionRefused',
					payload=json.dumps({'siteId': payload['siteId']})
				)
				return True

			device = managers.DeviceManager.deviceConnecting(uid=payload['uid'])
			if device:
				self._logger.info('Device with uid {} of type {} in room {} connected'.format(device.uid, device.deviceType, device.room))
				managers.MqttServer.publish(
					topic='projectAlice/devices/connectionAccepted',
					payload=json.dumps({'siteId': payload['siteId'], 'uid': payload['uid']})
				)
			else:
				managers.MqttServer.publish(
					topic='projectAlice/devices/connectionRefused',
					payload=json.dumps({'siteId': payload['siteId'], 'uid': payload['uid']})
				)

		elif intent == self._INTENT_ANSWER_YES_OR_NO:
			if session.previousIntent == self._INTENT_REBOOT:
				if 'step' in customData:
					if customData['step'] == 1:
						if commons.isYes(session.message):
							managers.MqttServer.continueDialog(
								sessionId=sessionId,
								text=managers.TalkManager.randomTalk('askRebootModules'),
								intentFilter=[self._INTENT_ANSWER_YES_OR_NO],
								previousIntent=self._INTENT_REBOOT,
								customData=json.dumps({
									'module': self.name,
									'step'  : 2
								})
							)
						else:
							managers.MqttServer.endTalk(
								sessionId=sessionId,
								text=managers.TalkManager.randomTalk('abortReboot')
							)
					else:
						value = 'greet'
						if commons.isYes(session.message):
							value = 'greetAndRebootModules'

						managers.ConfigManager.updateAliceConfiguration('onReboot', value)
						managers.MqttServer.endTalk(
							sessionId=sessionId,
							text=managers.TalkManager.randomTalk('confirmRebooting')
						)
						managers.ThreadManager.doLater(
							interval=5,
							func=self.restart
						)
				else:
					managers.MqttServer.endTalk(sessionId)
					self._logger.warn('Asked to reboot, but missing params')

			elif session.previousIntent == self._INTENT_DUMMY_ADD_USER:
				if commons.isYes(session.message):
					# TODO accesslevel checks!
					self.delayed = False
					managers.UserManager.addNewUser(customData['name'], 'admin')
					managers.MqttServer.endTalk(
						sessionId=sessionId,
						text=managers.TalkManager.randomTalk('confirmNewUser').format(customData['name'])
					)
					managers.ThreadManager.doLater(interval=2, func=self.onStart)
				else:
					managers.MqttServer.continueDialog(
						sessionId=sessionId,
						text=managers.TalkManager.randomTalk('soWhatsTheName'),
						intentFilter=[self._INTENT_ANSWER_NAME, self._INTENT_SPELL_WORD],
						previousIntent=str(self._INTENT_DUMMY_ADD_USER)
					)
			else:
				return False

		elif intent == self._INTENT_SWITCH_LANGUAGE:
			managers.MqttServer.publish(
				topic='hermes/asr/textCaptured',
				payload=json.dumps({'siteId': siteId})
			)
			if 'ToLang' not in slots:
				managers.MqttServer.endTalk(
					text=managers.TalkManager.randomTalk('noDestinationLanguage')
				)
				return True

			try:
				managers.LanguageManager.changeActiveLanguage(slots['ToLang'])
				managers.ThreadManager.doLater(
					interval=3,
					func=self.langSwitch,
					args=[slots['ToLang'], siteId, False]
				)
			except LanguageManagerLangNotSupported:
				managers.MqttServer.endTalk(
					text=managers.TalkManager.randomTalk('langNotSupported').format(slots['ToLang'])
				)
			except ConfigurationUpdateFailed:
				managers.MqttServer.endTalk(
					text=managers.TalkManager.randomTalk('langSwitchFailed')
				)

		elif intent == self._INTENT_UPDATE_BUNDLE:
			if not managers.LanguageManager.activeSnipsProjectId:
				managers.MqttServer.endTalk(
					sessionId=sessionId,
					text=managers.TalkManager.randomTalk('noProjectIdSet')
				)
			elif not managers.SnipsConsoleManager.loginCredentialsAreConfigured():
				managers.MqttServer.endTalk(
					sessionId=sessionId,
					text=managers.TalkManager.randomTalk('bundleUpdateNoCredentials')
				)
			elif managers.InternetManager.online:
				self._logger.info('[{}] User asked for assistant update'.format(self.name))
				managers.MqttServer.endTalk(
					sessionId=sessionId,
					text=managers.TalkManager.randomTalk('confirmAssistantUpdate')
				)
				managers.ThreadManager.doLater(
					interval=2,
					func=managers.SnipsConsoleManager.doDownload
				)
			else:
				managers.MqttServer.endTalk(
					sessionId=sessionId,
					text=managers.TalkManager.randomTalk('noAssistantUpdateOffline')
				)

		elif intent == self._INTENT_REBOOT:
			managers.MqttServer.continueDialog(
				sessionId=sessionId,
				text=managers.TalkManager.randomTalk('confirmReboot'),
				intentFilter=[self._INTENT_ANSWER_YES_OR_NO],
				previousIntent=self._INTENT_REBOOT,
				customData=json.dumps({
					'module': self.name,
					'step'  : 1
				})
			)

		elif intent == self._INTENT_INVADE_SONOS:
			if 'Room' in slots:
				room = slots['Room']
			elif siteId == 'default':
				room = managers.ConfigManager.getAliceConfigByName('room')
			else:
				room = siteId

			sonosModule = managers.ModuleManager.getModuleInstance('Sonos')
			if sonosModule is None:
				managers.MqttServer.endTalk(
					sessionId=sessionId,
					text=managers.TalkManager.randomTalk('noActiveModule')
				)
				return True

			if not sonosModule.anyModuleHere(room):
				managers.MqttServer.endTalk(
					sessionId=sessionId,
					text=managers.TalkManager.randomTalk('sorryNoSonosHere')
				)
			else:
				managers.MqttServer.endTalk(
					sessionId=sessionId,
					text=managers.TalkManager.randomTalk('takingOverSonos')
				)
				time.sleep(4)
				managers.ConfigManager.updateAliceConfiguration('outputOnSonos', '1')
				managers.ConfigManager.updateAliceConfiguration('outputOnSonosIn', room)
				managers.MqttServer.say(
					text=managers.TalkManager.randomTalk('confirmSonosAction'),
					client=siteId
				)

		elif intent == self._INTENT_RETREAT:
			managers.MqttServer.endTalk(
				sessionId=sessionId,
				text=managers.TalkManager.randomTalk('retreatSonos')
			)
			time.sleep(2.5)
			managers.ConfigManager.updateAliceConfiguration('outputOnSonos', '0')

		elif intent == self._INTENT_STOP_LISTEN:
			if 'Duration' in slots:
				duration = commons.getDuration(session.message)
				if duration > 0:
					managers.ThreadManager.doLater(
						interval=duration,
						func=self.unmuteSite,
						args=[siteId]
					)

			aliceModule = managers.ModuleManager.getModuleInstance('AliceSatellite')
			if aliceModule is not None:
				aliceModule.notifyDevice('projectAlice/devices/stopListen', siteId=siteId)

			managers.MqttServer.endTalk(sessionId=sessionId)

		elif session.previousIntent == self._INTENT_DUMMY_ADD_USER and intent in (self._INTENT_ANSWER_NAME, self._INTENT_SPELL_WORD):
			if not managers.UserManager.users:
				if intent == self._INTENT_ANSWER_NAME:
					name: str = str(slots['Name']).lower()
					if commons.isSpelledWord(name):
						name = name.replace(' ', '')
				else:
					name = ''
					for slot in slotsObj['Letters']:
						name += slot.value['value']

				if name in managers.UserManager.getAllUserNames(skipGuests=False):
					managers.MqttServer.continueDialog(
						sessionId=sessionId,
						text=managers.TalkManager.randomTalk('userAlreadyExist').format(name),
						intentFilter=[self._INTENT_ANSWER_NAME, self._INTENT_SPELL_WORD],
						previousIntent=str(self._INTENT_DUMMY_ADD_USER)
					)
				else:
					managers.MqttServer.continueDialog(
						sessionId=sessionId,
						text=managers.TalkManager.randomTalk('confirmUsername').format(name),
						intentFilter=[self._INTENT_ANSWER_YES_OR_NO],
						previousIntent=self._INTENT_DUMMY_ADD_USER,
						customData=json.dumps({
							'name': name
						})
					)
			else:
				managers.MqttServer.endTalk(sessionId)

		return True


	def unmuteSite(self, siteId):
		managers.ModuleManager.getModuleInstance('AliceSatellite').notifyDevice('projectAlice/devices/startListen', siteId=siteId)
		managers.ThreadManager.doLater(
			interval=1,
			func=managers.MqttServer.say,
			args=[managers.TalkManager.randomTalk('listeningAgain'), siteId]
		)


	@staticmethod
	def reboot():
		subprocess.run(['sudo', 'reboot'])


	@staticmethod
	def restart():
		subprocess.run(['sudo', 'systemctl', 'restart', 'ProjectAlice'])


	def cancelUnregister(self):
		if 'unregisterTimeout' in self._threads:
			thread = self._threads['unregisterTimeout']
			thread.cancel()
			del self._threads['unregisterTimeout']


	def langSwitch(self, newLang: str, siteId: str):
		managers.MqttServer.publish(
			topic='hermes/asr/textCaptured',
			payload=json.dumps({'siteId': siteId})
		)
		subprocess.call([commons.rootDir() + '/system/scripts/langSwitch.sh', newLang])
		managers.ThreadManager.doLater(
			interval=3,
			func=self._confirmLangSwitch,
			args=[newLang, siteId]
		)


	def _confirmLangSwitch(self, siteId: str):
		managers.MqttServer.publish(
			topic='hermes/leds/onStop',
			payload=json.dumps({'siteId': siteId})
		)
		managers.MqttServer.say(
			text=managers.TalkManager.randomTalk('langSwitch'),
			client=siteId
		)


	@staticmethod
	def changeFeedbackSound(inDialog: bool):
		if inDialog:
			state = '_ask'
		else:
			state = ''

		subprocess.run(['sudo', 'ln', '-sfn', commons.rootDir() + '/system/sounds/{}/start_of_input{}.wav'.format(managers.LanguageManager.activeLanguage, state), commons.rootDir() + '/assistant/custom_dialogue/sound/start_of_input.wav'])
		subprocess.run(['sudo', 'ln', '-sfn', commons.rootDir() + '/system/sounds/{}/error{}.wav'.format(managers.LanguageManager.activeLanguage, state), commons.rootDir() + '/assistant/custom_dialogue/sound/error.wav'])
