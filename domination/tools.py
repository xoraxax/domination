from flaskext.babel import get_translations


class Translatable(unicode):
    def __new__(cls, string, parameters=()):
        inst = super(Translatable, cls).__new__(cls, string)
        inst.parameters = parameters
        return inst

    def __unicode__(self):
        t = get_translations()
        if t is None:
            return self % self.parameters
        return t.ugettext(self[:]) % self.parameters


def _(string, parameters=()):
	return Translatable(string, parameters)
