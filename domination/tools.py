import os
import gettext
from StringIO import StringIO

from flask import _request_ctx_stack
from flaskext.babel import get_locale
from babel.support import Translations
from babel.messages.pofile import read_po
from babel.messages.mofile import write_mo
from jinja2 import Markup


class Translatable(unicode):
    def __new__(cls, string, parameters=()):
        inst = super(Translatable, cls).__new__(cls, string)
        inst.parameters = parameters
        return inst

    def __str__(self):
        raise NotImplementedError

    def __unicode__(self):
        t = get_translations()
        if t is None:
            return self % self.parameters
        return t.ugettext(self[:]) % self.parameters

    def __newargs__(self):
        return (unicode.__unicode__(self), self.parameters)


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


def get_translations():
    """ Load .po file, cache .mo file repr in memory and return
    a Babel Translations object. This function is meant for monkey patching
    into Flask-Babel."""
    ctx = _request_ctx_stack.top
    if ctx is None:
        return None
    translations_dict = ctx.app.babel_translations_dict
    lock = ctx.app.babel_translations_lock
    locale = str(get_locale())
    lock.acquire()
    if translations_dict.get(locale) is None:
        mo_file = StringIO()
        dirname = os.path.join(ctx.app.root_path, 'translations')
        transfilename = os.path.join(dirname, taint_filename(locale),
                'LC_MESSAGES', "messages.po")
        if os.path.exists(transfilename):
            catalog = read_po(file(transfilename, "r"))
            write_mo(mo_file, catalog)
            mo_file.seek(0)
            translations = Translations(fileobj=mo_file)
        else:
            translations = gettext.NullTranslations()
        translations_dict[locale] = translations
    else:
        translations = translations_dict[locale]
    lock.release()
    return translations

def ngettext(sing, plu, n, args=None):
    raise NotImplementedError

