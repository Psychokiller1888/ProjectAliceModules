import json
from collections import defaultdict
from pathlib import Path
from typing import Generator

from abc import ABC, abstractmethod
from jsonschema import Draft7Validator, exceptions


class Validation(ABC):

	def __init__(self, modulePath: Path):
		self._modulePath = modulePath
		self._validModule = self.infinidict()
		self._dirPath = Path(__file__).resolve().parent
		self._basePath = self._dirPath.parent.parent.parent
		self._error = False


	def infinidict(self):
		return defaultdict(self.infinidict)


	@property
	def validModules(self) -> dict:
		return self._validModule


	@property
	@abstractmethod
	def jsonSchema(self) -> dict:
		pass


	@property
	@abstractmethod
	def jsonFiles(self) -> Generator[Path, None, None]:
		pass


	@property
	def moduleName(self) -> str:
		return self._modulePath.name


	@property
	def moduleAuthor(self) -> str:
		return self._modulePath.parent.name


	def validateSyntax(self, file: Path) -> dict:
		data: dict = dict()
		try:
			data = json.loads(file.read_text())
		except ValueError as e:
			self._validModule['syntax'][file.name] = str(e)
			self._error = True
		return data


	def validateSchema(self) -> None:
		schema = self.jsonSchema
		for file in self.jsonFiles:
			self._validModule['schema'][file.name] = list()
			jsonPath = self._validModule['schema'][file.name]
			# try to load json from file and return error when the format is invalid
			data = self.validateSyntax(file)

			# validate the loaded json
			try:
				Draft7Validator(schema).validate(data)
			except exceptions.ValidationError:
				self._error = True
				for error in sorted(Draft7Validator(schema).iter_errors(data), key=str):
					jsonPath.append(error.message)


	@abstractmethod
	def validate(self, verbosity: int = 0) -> bool:
		pass
