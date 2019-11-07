import importlib
from typing import Optional

from core.base.model.Intent import Intent
from core.base.model.Module import Module
from core.dialog.model.DialogSession import DialogSession
from core.util.Decorators import IntentHandler
from .model import MiniGame


class Minigames(Module):
	"""
	Author: Psychokiller1888
	Description: Play a collection of many little games with alice
	"""

	_INTENT_ANSWER_YES_OR_NO 	= Intent('AnswerYesOrNo', isProtected=True)
	_INTENT_ANSWER_MINI_GAME 	= Intent('AnswerMiniGame', isProtected=True)

	_SUPPORTED_GAMES 			= [
		'FlipACoin',
		'RockPaperScissors',
		'RollADice',
		'GuessTheNumber'
	]

	DATABASE = {
		'highscores': [
			'username TEXT NOT NULL',
			'score INTEGER NOT NULL',
			'timestamp INTEGER NOT NULL'
		]
	}

	def __init__(self):
		self._INTENTS = list()

		self._minigames = dict()
		self._minigame: MiniGame = None

		for game in self._SUPPORTED_GAMES:
			try:
				lib = importlib.import_module(f'modules.Minigames.model.{game}')
				klass = getattr(lib, game)
				minigame = klass()

				self._minigames[game] = minigame
				self._INTENTS += [(intent, self.minigameIntent) for intent in minigame.intents]
			except Exception as e:
				self.logError(f'Something went wrong loading the minigame "{game}": {e}')

		super().__init__(self._INTENTS, databaseSchema=self.DATABASE)


	def onSessionTimeout(self, session: DialogSession):
		if self._minigame:
			self._minigame.started = False


	def onUserCancel(self, session: DialogSession):
		if self._minigame:
			self._minigame.started = False


	def minigameIntent(self, session: DialogSession, intent: str) -> Optional[bool]:
		if session.currentState != MiniGame.MiniGame.PLAYING_MINIGAME_STATE:
			return False

		self._minigame.onMessage(intent, session)


	@IntentHandler('AnswerYesOrNo', isProtected=True)
	def answerAnotherGame(self, session: DialogSession, **_kwargs):
		if not self.Commons.isYes(session):
			self.endDialog(
				sessionId=session.sessionId,
				text=self.randomTalk('endPlaying')
			)
		elif session.currentState != MiniGame.MiniGame.ANSWERING_PLAY_AGAIN_STATE:
			self.continueDialog(
				sessionId=session.sessionId,
				intentFilter=[self._INTENT_ANSWER_MINI_GAME],
				text=self.TalkManager.randomTalk('whichGame')
			)
		else:
			self._minigame.start()


	@IntentHandler('PlayGame')
	@IntentHandler('AnswerYesOrNo', isProtected=True)
	def playGameIntent(self, intent: str, session: DialogSession):
		sessionId = session.sessionId
		slots = session.slots

		if self._minigame and self._minigame.started:
			self._minigame.onMessage(intent, session)
			return

		if 'WhichGame' not in slots:
			self.continueDialog(
				sessionId=sessionId,
				intentFilter=[self._INTENT_ANSWER_MINI_GAME],
				text=self.TalkManager.randomTalk('whichGame')
			)

		elif session.slotValue('WhichGame') not in self._SUPPORTED_GAMES:
			self.continueDialog(
				sessionId=sessionId,
				intentFilter=[self._INTENT_ANSWER_MINI_GAME, self._INTENT_ANSWER_YES_OR_NO],
				text=self.TalkManager.randomTalk('unknownGame'),
				currentDialogState='answeringPlayAnotherGamer'
			)

		else:
			game = session.slotValue('WhichGame')
			self._minigame = self._minigames[game]
			self._minigame.start(session)
