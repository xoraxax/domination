from flask import request
import gettext 

class Translatable:

	def __init__(self, string, parameters = []):
		self.string = string;
		self.parameters = parameters;

	def __str__(self):
		return request.translation.lgettext(self.string % self.parameters).decode("UTF-8")

def _(string, parameters = []):
	return Translatable(string, parameters)
