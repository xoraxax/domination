from flaskext.babel import gettext, ngettext


class Translatable(unicode):
    def __new__(cls, string, parameters=()):
        inst = super(Translatable, cls).__new__(cls, string)
        inst.parameters = parameters
        return inst

    def __unicode__(self):
        return gettext(self) % self.parameters


def _(string, parameters=()):
	return Translatable(string, parameters)
