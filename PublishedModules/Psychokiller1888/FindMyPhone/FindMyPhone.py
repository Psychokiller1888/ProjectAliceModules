from core.base.model.Intent import Intent
from core.base.model.Module import Module
from core.dialog.model.DialogSession import DialogSession

try:
	from modules.Ifttt.Ifttt import IftttException
except:
	pass

class FindMyPhone(Module):
	"""
	Author: Psychokiller1888
	Description: Using ifttt one can ask alice to find his phone. sets the ring tone at max volume and initiates a call on it.
	"""

	_INTENT_FIND_PHONE = Intent('FindPhone')
	_INTENT_ANSWER_NAME = Intent('AnswerName', isProtected=True)

	def __init__(self):
		self._INTENTS = {
			self._INTENT_FIND_PHONE: self.findPhoneIntent,
			self._INTENT_ANSWER_NAME: self.answerNameIntent
		}

		super().__init__(self._INTENTS)


	def answerNameIntent(self, intent: str, session: DialogSession) -> bool:
		if session.previousIntent == self._INTENT_FIND_PHONE:
			return self.findPhoneIntent(intent=intent, session=session)
		return False


	def findPhoneIntent(self, intent: str, session: DialogSession) -> bool:
		sessionId = session.sessionId
		slots = session.slots

		who = slots.get('Who', slots.get('Name', session.user))
		if who == 'unknown':
			self.continueDialog(
				sessionId=sessionId,
				text=self.randomTalk('whosPhone'),
				intentFilter=[self._INTENT_ANSWER_NAME],
				previousIntent=self._INTENT_FIND_PHONE
			)
			return True

		module = self.getModuleInstance('Ifttt')
		if not module:
			self.endDialog(sessionId=sessionId, text=self.randomTalk('error'))
			return True

		answer = module.sendRequest(endPoint='locatePhone', user=who)
		if answer == IftttException.NOT_CONNECTED:
			self.endDialog(sessionId=sessionId, text=self.randomTalk('notConnected'))
		elif answer in {IftttException.ERROR, IftttException.BAD_REQUEST}:
			self.endDialog(sessionId=sessionId, text=self.randomTalk('error'))
		elif answer == IftttException.NO_USER:
			self.endDialog(sessionId=sessionId, text=self.randomTalk('unknown', replace=[who]))
		else:
			self.endDialog(sessionId=sessionId, text=self.randomTalk('acknowledge'))

		return True
