import copy

from domination.gameengine import Defended, TLS
from domination.tools import _

from domination.macros.__macros__ import generator_forward, generator_forward_ex


class Edition(object):
    def __init__(self, key, name, optional=True):
        self.key = key
        self.name = name
        self.optional = optional

BaseGame = Edition('base', _("Base game"), optional=False)
Intrigue = Edition('intrigue', _("Intrigue game"))
Alchemy = Edition('alchemy', _("Alchemy game"))
Seaside = Edition('seaside', _("Seaside game"))
Prosperity = Edition('prosperity', _("Prosperity game"))
Cornucopia = Edition('cornucopia', _("Cornucopia game"))
Hinterlands = Edition('hinterlands', _("Hinterlands game"))
editions = [BaseGame, Intrigue, Alchemy, Seaside, Prosperity, Cornucopia, Hinterlands]


class CardTypeRegistry(type):
    raw_card_classes = {}

    def __new__(cls, name, bases, d):
        abstract = d.pop("abstract", False)
        orig_bases = bases[:]
        bases = [b for b in bases if b.__name__ != "PrizeCard"]
        if not abstract:
            d['card_type'] = bases[0].__name__
            d['second_card_type'] = len(bases) > 1 and bases[1].__name__ or ''
        if name != "Card":
            cost = d.pop("cost", None)
            d["raw_cost"] = cost
        kls = type.__new__(cls, name, orig_bases, d)
        if not abstract:
            CardTypeRegistry.raw_card_classes[name] = kls
        return kls

    def _get_cost(self):
        if getattr(TLS, "game", None) is None:
            return self.raw_cost
        return self.raw_cost + TLS.game.cost_delta.get(self.__name__, 0)
    def _set_cost(self, value):
        cd = TLS.game.cost_delta
        cd[self.__name__] = value - self.raw_cost
    cost = property(_get_cost, _set_cost)

    @staticmethod
    def keys2classes(keys):
        classes = []
        for key in keys:
            cls = CardTypeRegistry.raw_card_classes[key]
            classes.append(cls)
        return classes

    @staticmethod
    def cards_from_edition(edition):
        return [c for c in CardTypeRegistry.raw_card_classes.values() if c.edition == edition and c.implemented]

class Card(object):
    __metaclass__ = CardTypeRegistry
    name = "UNKNOWN"   # card name
    points = 0         # victory points
    worth = 0          # monetary worth
    potion = 0         # potion worth (alchemy)
    potioncost = 0     # potion cost (alchemy)
    optional = False   # one of the mandatory cards?
    implemented = True # show card for selection
    abstract = True    # abstract template?
    trash_after_playing = False  # does it go to trash after playing?
    durationaction_activated = False # Seaside duration cards
    __slots__ = ()

    def __init__(self):
        self.__name__ = type(self).__name__
        assert self.name != "UNKNOWN"
        assert self.cost is not None or self.__class__.__dict__.get("get_cost")
        assert self.points is not None or self.__class__.__dict__.get("get_points")
        assert self.worth is not None or self.__class__.__dict__.get("get_worth")
        assert self.potion is not None

    def _get_cost(self):
        return type(self).cost
    def _set_cost(self, value):
        type(self).cost = value
    cost = property(_get_cost, _set_cost)

    @classmethod
    def classnames(cls):
        if issubclass(cls, VictoryCard) and issubclass(cls, TreasureCard):
            return _("Victory/Treasure card")
        if issubclass(cls, VictoryCard) and issubclass(cls, ActionCard):
            return _("Action/Victory card")
        return cls.classname

    @classmethod
    def get_card_infos(self, game):
        return list(game.fire_hook("on_render_card_info", game, self))

    def activate_action(self, game, player):
        raise NotImplementedError

    def get_points(self, game, player):
        return self.points

    @classmethod
    def get_cost(self, game=None, player=None):
        return self.cost

    def get_worth(self, player):
        return self.worth

    def discard(self, player):
        player.hand.remove(self)
        player.discard_pile.append(self)

    def trash(self, game, player):
        player.hand.remove(self)
        game.trash_pile.append(self)

    def backondeck(self, game, player):
        player.hand.remove(self)
        player.deck.append(self)

    def defend_action(self, game, player, card):
        raise NotImplementedError

    @classmethod
    def on_buy_card(cls, game, player, card):
        gen = game.fire_hook("on_gain_card", game, player, card)
        generator_forward(gen)


class ActionCard(Card):
    optional = True
    abstract = True
    classname = _("Action card")
    throne_room_duplicates = False


class DurationCard(Card):
    optional = True
    abstract = True
    classname = _("Duration card")


class AttackCard(ActionCard):
    abstract = True
    classname = _("Attack card")

    def defends_check(self, game, other_player):
        from domination.gameengine import InfoRequest, SelectHandCards
        already_selected = set()
        while True:
            for c in other_player.aux_cards:
                if hasattr(c, "process_defense"):
                    c.process_defense(game, other_player, self)
            if not any(isinstance(c, ReactionCard) for c in other_player.hand):
                break
            req = SelectHandCards(
                game, other_player, count_lower=0, count_upper=1, cls=ReactionCard,
                msg=_("Do you want to flash a card in response to the attack?"),
                not_selectable=already_selected)
            if not req.fulfillable():
                break
            cards = yield req
            if cards:
                card = cards[0]
                already_selected.add(card)
                # notify other players
                for info_player in game.following_participants(other_player):
                    yield InfoRequest(
                        game, info_player,
                        _("%s reacts with:", (other_player.name, )), [card])
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
    classname = _("Action/Reaction card")


class VictoryCard(Card):
    abstract = True
    points = None
    classname = _("Victory card")


class TreasureCard(Card):
    abstract = True
    worth = None
    classname = _("Treasure card")


class CurseCard(Card):
    abstract = True
    points = None
    classname = _("Curse card")


class PrizeCard(Card):
    optional = False
    abstract = True
    classname = _("Prize card")


class CardSet(object):
    def __init__(self, name, card_classes):
        self.name = name
        self.editions = set(cls.edition for cls in card_classes)
        self.card_classes = card_classes

