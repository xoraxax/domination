from domination.gameengine import Defended
from domination.tools import _


class Edition(object):
    def __init__(self, key, name, optional=True):
        self.key = key
        self.name = name
        self.optional = optional

BaseGame = Edition('base', _("Base game"), optional=False)
Intrigue = Edition('intrigue', _("Intrigue game"))

editions = [BaseGame, Intrigue]


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

    def defend_action(self, game, player, card):
        raise NotImplementedError


class ActionCard(Card):
    optional = True
    abstract = True


class AttackCard(ActionCard):
    abstract = True

    def defends_check(self, game, other_player):
        from domination.gameengine import InfoRequest, SelectHandCards
        already_selected = set()
        while True:
            if not any(isinstance(c, ReactionCard) for c in other_player.hand):
                break
            cards = yield SelectHandCards(
                game, other_player, count_lower=0, count_upper=1, cls=ReactionCard,
                msg=_("Do you want to flash a card in response to the attack?"),
                not_selectable=already_selected)
            if cards:
                card = cards[0]
                already_selected.add(card)
                # notify other players
                for info_player in game.following_players(other_player):
                    yield InfoRequest(
                        game, info_player,
                        _("%s reacts with:") % (other_player.name, ), [card])
                gen = card.defend_action(game, other_player, self)
                item = None
                while True:
                    try:
                        # this can raise Defended if the attack has been defended
                        item = (yield gen.send(item))
                    except StopIteration:
                        break
            else:
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


class CardSet(object):
    def __init__(self, name, card_classes):
        self.name = name
        self.editions = set(cls.edition for cls in card_classes)
        self.card_classes = card_classes
