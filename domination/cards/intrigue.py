from domination.cards import TreasureCard, VictoryCard, ActionCard, \
     AttackCard, ReactionCard, CardSet, Intrigue
from domination.cards.base import Duchy
from domination.gameengine import SelectHandCards, Question, MultipleChoice
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

    def activate_action(self, game, player):
        while True:
            choice = yield MultipleChoice(game, player, _("Choose two:"),
                                          [("card",   _("+1 Card")),
                                           ("action", _("+1 Action")),
                                           ("buy",    _("+1 Buy")),
                                           ("money",  _("+1 Money"))])
            if len(choice) == 2:
                break
        for item in choice:
            if item == "card":
                player.draw_cards(1)
            elif item == "action":
                player.remaining_actions += 1
            elif item == "buy":
                player.remaining_deals += 1
            elif item == "money":
                player.virtual_money += 1


class Scout(ActionCard):
    name = _("Scout")
    edition = Intrigue
    cost = 4


class Nobles(ActionCard, VictoryCard):
    # XXX color card appropriately
    name = _("Nobles")
    edition = Intrigue
    cost = 6
    points = 2

    def activate_action(self, game, player):
        answer = yield Question(game, player, _("What do you want to get?"),
                                [("cards",   _("+3 Cards")),
                                 ("actions", _("+2 Actions"))])
        if answer == "cards":
            player.draw_cards(3)
        else:
            player.remaining_actions += 2


class GreatHall(ActionCard, VictoryCard):
    name = _("Great Hall")
    edition = Intrigue
    cost = 3
    points = 1

    def activate_action(self, game, player):
        player.draw_cards(1)
        player.remaining_actions += 1


class Duke(VictoryCard):
    name = _("Duke")
    edition = Intrigue
    optional = True
    cost = 5
    points = 0
    desc = _("Worth one point for every duchy you have.")

    def get_points(self, game, player):
        return sum(isinstance(card, Duchy) for card in
                   player.deck + player.hand + player.discard_pile)


class Harem(TreasureCard, VictoryCard):
    name = _("Harem")
    edition = Intrigue
    optional = True
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
    desc = _("+3 Cards, put a card from your hand on top of your deck.")

    def activate_action(self, game, player):
        player.draw_cards(3)
        cards = yield SelectHandCards(game, player, count_upper=1,
                                      msg=_("Select a card to put on your deck."))
        if cards:
            card = cards[0]
            player.deck.append(card)
            player.hand.remove(card)


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


class SecretChamber(ReactionCard):
    name = _("Secret Chamber")
    edition = Intrigue
    cost = 2
    desc = _("Discard any number of cards. +1 Money per card discarded. "
            " When another player plays an attack card, you may"
            " reveal this from your hand. If you do, +2 Cards, then put"
            " 2 cards from your hand on top of your deck.")

    def activate_action(self, game, player):
        cards = yield SelectHandCards(
            game, player,
            msg=_("Which cards do you want to discard?"))
        if not cards:
            return
        player.virtual_money += len(cards)
        for card in cards:
            player.hand.remove(card)
            player.discard_pile.append(card)

    def defend_action(self, game, player, card):
        player.draw_cards(2)
        cards = yield SelectHandCards(
            game, player, count_lower=2, count_upper=2,
            msg=_("Which cards do you want to put on your deck?"))
        if not cards:
            return
        for card in cards:
            player.hand.remove(card)
            player.deck.append(card)


from domination.cards.base import (
    Bureaucrat, Cellar, Chancellor, CouncilRoom, Festival, Library, Mine,
    Militia, Remodel, Spy, Thief, ThroneRoom, Witch)

card_sets = [
    CardSet(_('Victory Dance'),
            [Bridge, Duke, GreatHall, Harem, Ironworks, Masquerade, Nobles,
             Pawn, Scout, Upgrade]),
    CardSet(_('Secret Schemes'),
            [Conspirator, Harem, Ironworks, Pawn, Saboteur, ShantyTown,
             Steward, Swindler, TradingPost, Tribute]),
    CardSet(_('Best Wishes'),
            [Coppersmith, Courtyard, Masquerade, Scout, ShantyTown, Steward,
             Torturer, TradingPost, Upgrade, WishingWell]),
    CardSet(_('Deconstruction'),
            [Bridge, MiningVillage, Remodel, Saboteur, SecretChamber, Spy,
             Swindler, Thief, ThroneRoom, Torturer]),
    CardSet(_('Hand Madness'),
            [Bureaucrat, Chancellor, CouncilRoom, Courtyard, Mine, Militia,
             Minion, Nobles, Steward, Torturer]),
    CardSet(_('Underlings'),
            [Baron, Cellar, Festival, Library, Masquerade, Minion, Nobles,
             Pawn, Steward, Witch]),
]
