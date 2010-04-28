from domination.tools import _


class Edition(object):
    def __init__(self, name):
        self.name = name

Promo = Edition(_("Promo Cards"))
BaseGame = Edition(_("Base game"))
Intrigue = Edition(_("Intrigue game"))
Seaside = Edition(_("Seaside expansion"))
Alchemy = Edition(_("Alchemy expansion"))


class CardTypeRegistry(type):
    card_classes = {}

    def __new__(cls, name, bases, d):
        abstract = d.pop("abstract", False)
        if not abstract:
            d['card_type'] = bases[0].__name__
        kls = type.__new__(cls, name, bases, d)
        if not abstract:
            CardTypeRegistry.card_classes[name] = kls
        return kls

    @staticmethod
    def keys2classes(keys):
        classes = []
        for key in keys:
            cls = CardTypeRegistry.card_classes[key]
            classes.append(cls)
        return classes

def card_class(key):
    return CardTypeRegistry.card_classes[key]


class Card(object):
    __metaclass__ = CardTypeRegistry
    name = "UNKNOWN"  # card name
    cost = None       # card cost
    points = 0        # victory points
    worth = 0         # monetary worth
    optional = False  # one of the mandatory cards?
    abstract = True   # abstract template?
    trash_after_playing = False  # does it go to trash after playing?
    __slots__ = ()

    def __init__(self):
        self.__name__ = type(self).__name__
        assert self.name != "UNKNOWN"
        assert self.cost is not None
        assert self.points is not None
        assert self.worth is not None

    def activate_action(self, game, player):
        raise NotImplementedError

    def get_points(self, game, player):
        return self.points

    def discard(self, player):
        player.hand.remove(self)
        player.discard_pile.append(self)

    def trash(self, game, player):
        player.hand.remove(self)
        game.trash_pile.append(self)

    def defends(self, game, player, card):
        return False


class ActionCard(Card):
    optional = True
    abstract = True


class AttackCard(ActionCard):
    abstract = True

    def defends_check(self, game, other_player, msg):
        from domination.gameengine import InfoRequest
        for card in other_player.hand:
            if card.defends(game, other_player, self):
                for info_player in game.following_players(other_player):
                    yield InfoRequest(game, info_player,
                        _(msg) % (other_player.name, ), [card])
                break


class ReactionCard(ActionCard):
    abstract = True


class VictoryCard(Card):
    abstract = True
    points = None


class TreasureCard(Card):
    abstract = True
    worth = None


class CurseCard(Card):
    abstract = True
    points = None
