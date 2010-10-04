import os

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


def taint_filename(basename):
    """
    Make a filename that is supposed to be a plain name secure, i.e.
    remove any possible path components that compromise our system.

    @param basename: (possibly unsafe) filename
    @rtype: string
    @return: (safer) filename
    """
    for x in (os.pardir, ':', '/', '\\', '<', '>'):
        basename = basename.replace(x, '_')

    return basename

