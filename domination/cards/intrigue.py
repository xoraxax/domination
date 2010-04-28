from domination.cards import TreasureCard, VictoryCard, CurseCard, ActionCard, \
     AttackCard, ReactionCard, Intrigue, CardTypeRegistry
from domination.gameengine import InfoRequest, SelectCard, SelectHandCards, \
     YesNoQuestion, ActivateNextActionMultipleTimes
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
    cost = 5

    def get_points(self, game, player):
        # XXX 1 point per duchy
        return 0


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
