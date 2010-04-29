from domination.cards import TreasureCard, VictoryCard, ActionCard, \
     AttackCard, CardSet, Intrigue
from domination.cards.base import Duchy
from domination.gameengine import InfoRequest, SelectCard, SelectHandCards, \
     YesNoQuestion
from domination.tools import _


class Ironworks(ActionCard):
    name = _("Ironworks")
    edition = Intrigue
    cost = 4


class Minion(AttackCard):
    name = _("Minion")
    edition = Intrigue
    cost = 5


class Pawn(ActionCard):
    name = _("Pawn")
    edition = Intrigue
    cost = 2


class Scout(ActionCard):
    name = _("Scout")
    edition = Intrigue
    cost = 4


class Nobles(ActionCard, VictoryCard):
    name = _("Nobles")
    edition = Intrigue
    cost = 6
    points = 2


class GreatHall(ActionCard, VictoryCard):
    name = _("Great Hall")
    edition = Intrigue
    cost = 3
    points = 1


class Duke(VictoryCard):
    name = _("Duke")
    edition = Intrigue
    optional = True
    cost = 5
    points = 0

    def get_points(self, game, player):
        return sum(isinstance(card, Duchy) for card in player.deck)


class Harem(TreasureCard, VictoryCard):
    name = _("Harem")
    edition = Intrigue
    cost = 6
    worth = 2
    points = 2


class MiningVillage(ActionCard):
    name = _("Mining Village")
    edition = Intrigue
    cost = 4


class ShantyTown(ActionCard):
    name = _("Shanty Town")
    edition = Intrigue
    cost = 3


class Saboteur(AttackCard):
    name = _("Saboteur")
    edition = Intrigue
    cost = 5


class Coppersmith(ActionCard):
    name = _("Coppersmith")
    edition = Intrigue
    cost = 4


class Bridge(ActionCard):
    name = _("Bridge")
    edition = Intrigue
    cost = 4


class Conspirator(ActionCard):
    name = _("Conspirator")
    edition = Intrigue
    cost = 4


class Courtyard(ActionCard):
    name = _("Courtyard")
    edition = Intrigue
    cost = 2


class Baron(ActionCard):
    name = _("Baron")
    edition = Intrigue
    cost = 4


class Tribute(ActionCard):
    name = _("Tribute")
    edition = Intrigue
    cost = 5


class Masquerade(ActionCard):
    name = _("Masquerade")
    edition = Intrigue
    cost = 3


class Torturer(AttackCard):
    name = _("Torturer")
    edition = Intrigue
    cost = 5


class Swindler(AttackCard):
    name = _("Swindler")
    edition = Intrigue
    cost = 3


class Upgrade(ActionCard):
    name = _("Upgrade")
    edition = Intrigue
    cost = 5


class TradingPost(ActionCard):
    name = _("Trading Post")
    edition = Intrigue
    cost = 5


class WishingWell(ActionCard):
    name = _("Wishing Well")
    edition = Intrigue
    cost = 3


class Steward(ActionCard):
    name = _("Steward")
    edition = Intrigue
    cost = 3


from domination.cards.base import Moat

card_sets = [
    CardSet(_('Test'), [Duke, Moat]),
]
