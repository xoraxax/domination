from flask import request
from flaskext.babel import gettext, ngettext


class Translatable:
	def __init__(self, string, parameters=[]):
		self.string = string
		self.parameters = parameters

	def __str__(self):
		return gettext(self.string % self.parameters)


def _(string, parameters=[]):
	return Translatable(string, parameters)
