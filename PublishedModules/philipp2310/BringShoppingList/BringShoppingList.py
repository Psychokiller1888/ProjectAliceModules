from typing import Tuple

import requests
from BringApi.BringApi import BringApi

from core.ProjectAliceExceptions import ModuleStartingFailed
from core.base.model.Intent import Intent
from core.base.model.Module import Module
from core.dialog.model.DialogSession import DialogSession
from core.util.Decorators import Decorators


class BringShoppingList(Module):
	"""
	Author: philipp2310
	Description: maintaines a Bring! shopping list
	"""

	### Intents
	_INTENT_ADD_ITEM = Intent('addItem_bringshop')
	_INTENT_DEL_ITEM = Intent('deleteItem_bringshop')
	_INTENT_READ_LIST = Intent('readList_bringshop')
	_INTENT_CHECK_LIST = Intent('checkList_bringshop', isProtected=True)
	_INTENT_DEL_LIST = Intent('deleteList_bringshop')
	_INTENT_CONF_DEL = Intent('AnswerYesOrNo', isProtected=True)
	_INTENT_ANSWER_SHOP = Intent('whatItem_bringshop', isProtected=True)
	_INTENT_SPELL_WORD = Intent('SpellWord', isProtected=True)


	def __init__(self):
		self._INTENTS = [
			(self._INTENT_ADD_ITEM, self.addItemIntent),
			(self._INTENT_DEL_ITEM, self.delItemIntent),
			(self._INTENT_CHECK_LIST, self.checkListIntent),
			(self._INTENT_READ_LIST, self.readListIntent),
			(self._INTENT_DEL_LIST, self.delListIntent),
			self._INTENT_CONF_DEL,
			self._INTENT_ANSWER_SHOP,
			self._INTENT_SPELL_WORD
		]

		super().__init__(self._INTENTS)

		self._INTENT_ANSWER_SHOP.dialogMapping = {
			self._INTENT_ADD_ITEM: self.addItemIntent,
			self._INTENT_DEL_ITEM: self.delItemIntent,
			self._INTENT_CHECK_LIST: self.checkListIntent
		}

		self._INTENT_SPELL_WORD.dialogMapping = {
			self._INTENT_ADD_ITEM: self.addItemIntent,
			self._INTENT_DEL_ITEM: self.delItemIntent,
			self._INTENT_CHECK_LIST: self.checkListIntent
		}

		self._INTENT_CONF_DEL.dialogMapping = {
			'confDelList': self.confDelIntent
		}

		self._uuid = self.getConfig('uuid')
		self._uuidlist = self.getConfig('listUuid')
		self._bring = None
	
	
	def onStart(self) -> dict:
		if not self.getConfig('uuid') or not self.getConfig('listUuid'):
			self._connectAccount()

		self._uuid = self.getConfig('uuid')
		self._uuidlist = self.getConfig('listUuid')

		self._bring = BringApi(self._uuid, self._uuidlist)
		
		return super().onStart()


	@Decorators.online
	def _connectAccount(self):
		try:
			req = requests.get(f'https://api.getbring.com/rest/bringlists?email={self.getConfig("bringEmail")}&password={self.getConfig("bringPassword")}')
			if req.status_code != 200:
				raise Exception

			data = req.json()
			if data:
				if 'errorcode' in data or 'uuid' not in data or 'bringListUUID' not in data:
					raise Exception

				self.updateConfig('uuid', data['uuid'])
				self.updateConfig('listUuid', data['bringListUUID'])
			else:
				raise Exception
		except:
			raise ModuleStartingFailed(self._name, 'Please check your account login and password')


	@Decorators.online
	def _deleteCompleteList(self) -> str:
		"""
		perform the deletion of the complete list
		-> load all and delete item by item
		"""
		items = self._bring.get_items().json()['purchase']
		for item in items:
			self._bring.recent_item(item['name'])
		return self.randomTalk('del_all')


	def _addItemInt(self, items) -> Tuple[list, list]:
		"""
		internal method to add a list of items to the shopping list
		:returns: two splitted lists of successfull adds and items that already existed.
		"""
		bringItems = self._bring.get_items().json()['purchase']
		added = list()
		exist = list()
		for item in items:
			if not any(entr['name'].lower() == item.lower() for entr in bringItems):
				self._bring.purchase_item(item, "")
				added.append(item)
			else:
				exist.append(item)
		return added, exist


	def _deleteItemInt(self, items: list) -> Tuple[list, list]:
		"""
		internal method to delete a list of items from the shopping list
		:returns: two splitted lists of successfull deletions and items that were not on the list
		"""
		bringItems = self._bring.get_items().json()['purchase']
		removed = list()
		exist = list()
		for item in items:
			for entr in bringItems:
				if entr['name'].lower() == item.lower():
					self._bring.recent_item(entr['name'])
					removed.append(item)
					break	
			else:
				exist.append(item)
		return removed, exist


	def _checkListInt(self, items: list) -> Tuple[list, list]:
		"""
		internal method to check if a list of items is on the shopping list
		:returns: two splitted lists, one with the items on the list, one with the missing ones
		"""
		bringItems = self._bring.get_items().json()['purchase']
		found = list()
		missing = list()
		for item in items:
			if any(entr['name'].lower() == item.lower() for entr in bringItems):
				found.append(item)
			else:
				missing.append(item)
		return found, missing


	def _getShopItems(self, answer: str, intent: str, session: DialogSession) -> list:
		"""get the values of shopItem as a list of strings"""
		if intent == self._INTENT_SPELL_WORD:
			item = ''.join([slot.value['value'] for slot in session.slotsAsObjects['Letters']])
			return [item.capitalize()]
		
		items = [x.value['value'] for x in session.slotsAsObjects.get('shopItem', list()) if x.value['value'] != "unknownword"]

		if not items:
			self.continueDialog(
				sessionId=session.sessionId,
				text=self.randomTalk(f'{answer}_what'),
				intentFilter=[self._INTENT_ANSWER_SHOP, self._INTENT_SPELL_WORD],
				currentDialogState=intent)
		return items


	### INTENTS ###
	def delListIntent(self, session: DialogSession, **_kwargs):
		self.continueDialog(
			sessionId=session.sessionId,
			text=self.randomTalk('chk_del_all'),
			intentFilter=[self._INTENT_CONF_DEL],
			currentDialogState='confDelList')


	def confDelIntent(self, session: DialogSession, **_kwargs):
		if self.Commons.isYes(session):
			self.endDialog(session.sessionId, text=self._deleteCompleteList())
		else:
			self.endDialog(session.sessionId, text=self.randomTalk('nodel_all'))


	@Decorators.online
	def addItemIntent(self, intent: str, session: DialogSession):
		items = self._getShopItems('add', intent, session)
		if items:
			added, exist = self._addItemInt(items)
			self.endDialog(session.sessionId, text=self._combineLists('add', added, exist))


	@Decorators.online
	def delItemIntent(self, intent: str, session: DialogSession):
		items = self._getShopItems('rem', intent, session)
		if items:
			removed, exist = self._deleteItemInt(items)
			self.endDialog(session.sessionId, text=self._combineLists('rem', removed, exist))


	@Decorators.online
	def checkListIntent(self, intent: str, session: DialogSession):
		items = self._getShopItems('chk', intent, session)
		if items:
			found, missing = self._checkListInt(items)
			self.endDialog(session.sessionId, text=self._combineLists('chk', found, missing))


	@Decorators.online
	def readListIntent(self,session: DialogSession, **_kwargs):
		"""read the content of the list"""
		items = self._bring.get_items().json()['purchase']
		itemlist = [item['name'] for item in items]
		self.endDialog(session.sessionId, text=self._getTextForList('read', itemlist))


	#### List/Text operations
	def _combineLists(self, answer: str, first: list, second: list) -> str:
		firstAnswer = self._getTextForList(answer, first) if first else ''
		secondAnswer = self._getTextForList(f'{answer}_f', second) if second else ''
		combinedAnswer = self.randomTalk('state_con', [firstAnswer, secondAnswer]) if first and second else ''

		return combinedAnswer or firstAnswer or secondAnswer


	def _getTextForList(self, pref: str, items: list) -> str:
		"""Combine entries of list into wrapper sentence"""
		if not items:
			return self.randomTalk(f'{pref}_none')
		elif len(items) == 1:
			return self.randomTalk(f'{pref}_one', [items[0]])

		value = self.randomTalk(text='gen_list', replace=[', '.join(items[:-1]), items[-1]])
		return self.randomTalk(f'{pref}_multi', [value])
