from domination.cards import TreasureCard, VictoryCard, ActionCard, \
     AttackCard, ReactionCard, CardSet, Intrigue
from domination.cards.base import Duchy
from domination.gameengine import SelectHandCards, Question, MultipleChoice, \
     InfoRequest, SelectCard, CardTypeRegistry
from domination.tools import _
from domination.macros.__macros__ import handle_defense


class Baron(ActionCard):
    # XXX to be implemented
    name = _("Baron")
    edition = Intrigue
    cost = 4


class Bridge(ActionCard):
    # XXX to be implemented
    name = _("Bridge")
    edition = Intrigue
    cost = 4


class Conspirator(ActionCard):
    # XXX to be implemented
    name = _("Conspirator")
    edition = Intrigue
    cost = 4


class Coppersmith(ActionCard):
    # XXX to be implemented
    name = _("Coppersmith")
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


class Duke(VictoryCard):
    name = _("Duke")
    edition = Intrigue
    optional = True
    cost = 5
    points = 0
    desc = _("Worth one point for every duchy you have.")

    def get_points(self, game, player):
        return sum(isinstance(card, Duchy) for card in player.deck)


class GreatHall(ActionCard, VictoryCard):
    name = _("Great Hall")
    edition = Intrigue
    cost = 3
    points = 1
    desc = _("+1 Card, +1 Action")

    def activate_action(self, game, player):
        player.draw_cards(1)
        player.remaining_actions += 1


class Harem(TreasureCard, VictoryCard):
    name = _("Harem")
    edition = Intrigue
    optional = True
    cost = 6
    worth = 2
    points = 2


class Ironworks(ActionCard):
    name = _("Ironworks")
    edition = Intrigue
    cost = 4
    desc = _("Gain a card costing up to 4. If it is an Action card: +1 Action;"
            " Treasure card: +1 Money; Victory Card: +1 Card")

    def activate_action(self, game, player):
        # copied from Feast
        card_cls = yield SelectCard(game, player, card_classes=[c for c in
            CardTypeRegistry.card_classes.itervalues() if c.cost <= 4 and
            game.supply.get(c.__name__)],
            msg=_("Select a card that you want to have."), show_supply_count=True)
        new_card = game.supply[card_cls.__name__].pop()
        player.discard_pile.append(new_card)
        for info_player in game.following_players(player):
            yield InfoRequest(game, info_player,
                    _("%s gains:") % (player.name, ), [new_card])
        for val in game.check_empty_pile(card_cls.__name__):
            yield val

        if issubclass(card_cls, ActionCard):
            player.remaining_actions += 1
        if issubclass(card_cls, TreasureCard):
            player.virtual_money += 1
        if issubclass(card_cls, VictoryCard):
            player.draw_cards(1)


class Masquerade(ActionCard):
    name = _("Masquerade")
    edition = Intrigue
    cost = 3
    desc = _("+2 Cards, Each player passes a card from his hand to the left at"
             " once. Then you may trash a card from your hand.")

    def activate_action(self, game, player):
        player.draw_cards(2)
        passed_card = {}
        for other_player in game.players:
            cards = yield SelectHandCards(
                game, other_player,
                _("Which card do you want to pass left?"), None, 1, 1)
            card = cards[0]
            passed_card[other_player.left(game)] = card
            other_player.hand.remove(card)
        for other_player in game.players:
            card = passed_card[other_player]
            yield InfoRequest(game, other_player,
                    _("You gained this card from your right:"), [card])
            other_player.hand.append(card)

        if player.hand:
            cards = yield SelectHandCards(game, player, count_lower=1, count_upper=1,
                    msg=_("Which card do you want to trash?"))
        # trash cards
        for card in cards:
            card.trash(game, player)
        for other_player in game.following_players(player):
            yield InfoRequest(game, other_player,
                    _("%s trashes this card:") % (player.name, ), cards)


class MiningVillage(ActionCard):
    # XXX to be implemented
    name = _("Mining Village")
    edition = Intrigue
    cost = 4


class Minion(AttackCard):
    # XXX to be implemented
    name = _("Minion")
    edition = Intrigue
    cost = 5


class Nobles(ActionCard, VictoryCard):
    name = _("Nobles")
    edition = Intrigue
    cost = 6
    points = 2
    desc = _("Choose one: +3 Cards, or +2 Actions.")

    def activate_action(self, game, player):
        actions = [("cards",   _("+3 Cards")),
                   ("actions", _("+2 Actions"))]

        answer = yield Question(game, player, _("What do you want to get?"),
                                actions)

        for info_player in game.following_players(player):
            yield InfoRequest(game, info_player,
                    _("%s chooses '%s'") % (player.name, _(dict(actions)[answer])), [])

        if answer == "cards":
            player.draw_cards(3)
        else:
            player.remaining_actions += 2


class Pawn(ActionCard):
    name = _("Pawn")
    edition = Intrigue
    cost = 2
    desc = _("Choose two: +1 Card, +1 Action, +1 Buy, +1 Money."
            " (The choices must be different.)")

    def activate_action(self, game, player):
        choices = [("card",   _("+1 Card")),
                   ("action", _("+1 Action")),
                   ("buy",    _("+1 Buy")),
                   ("money",  _("+1 Money"))]
        while True:
            choice = yield MultipleChoice(game, player, _("Choose two:"), choices,
                                          2, 2)
            if len(choice) == 2:
                break

        for info_player in game.following_players(player):
            chosen = ", ".join(_(dict(choices)[c]) for c in choice)
            yield InfoRequest(game, info_player,
                    _("%s chooses '%s'") % (player.name, chosen), [])

        for item in choice:
            if item == "card":
                player.draw_cards(1)
            elif item == "action":
                player.remaining_actions += 1
            elif item == "buy":
                player.remaining_deals += 1
            elif item == "money":
                player.virtual_money += 1


class Saboteur(AttackCard):
    # XXX to be implemented
    name = _("Saboteur")
    edition = Intrigue
    cost = 5


class Scout(ActionCard):
    # XXX to be implemented
    name = _("Scout")
    edition = Intrigue
    cost = 4


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
            card.discard(player)
        for other_player in game.players:
            if other_player is not player:
                yield InfoRequest(game, other_player,
                    _("%s discards these cards:") % (player.name, ), cards)

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


class ShantyTown(ActionCard):
    name = _("Shanty Town")
    edition = Intrigue
    cost = 3
    desc = _("+2 Actions, Reveal your hand. If you have no action cards in hand,"
             " +2 Cards.")

    def activate_action(self, game, player):
        player.remaining_actions += 2

        for info_player in game.following_players(player):
            yield InfoRequest(game, info_player, _("%s reveals his hand:") % \
                    (player.name, ), player.hand)

        action_cards = [c for c in player.hand if isinstance(c, ActionCard)]
        if not action_cards:
            player.draw_cards(2)


class Swindler(AttackCard):
    name = _("Swindler")
    edition = Intrigue
    cost = 3
    desc = _("+2 Money, Each other player trashes the top card of his deck and"
             " gains a card with the same cost that you choose.")

    def activate_action(self, game, player):
        player.virtual_money += 2
        for other_player in game.following_players(player):
            try:
                handle_defense(self, game, player)
            except Defended:
                continue
            player.draw_cards(1)
            card = player.hand.pop()
            for info_player in game.players:
                yield InfoRequest(game, info_player, _("%s trashes:") %
                        (info_player.name, ), [card])

            req = SelectCard(game, player, card_classes=[c for c in
                CardTypeRegistry.card_classes.itervalues() if c.cost == card.cost and
                game.supply.get(c.__name__)],
                msg=_("Select a card that you want to give."), show_supply_count=True)
            if not req.fulfillable():
                continue
            card_cls = yield req
            new_card = game.supply[card_cls.__name__].pop()
            other_player.discard_pile.append(new_card)
            for info_player in game.following_players(player):
                yield InfoRequest(game, info_player,
                        _("%s gains:") % (other_player.name, ), [new_card])
            for val in game.check_empty_pile(card_cls.__name__):
                yield val



class Steward(ActionCard):
    name = _("Steward")
    edition = Intrigue
    cost = 3
    desc = _("Choose one: +2 Cards; or +2 Money; or trash two cards from your hand.")

    def activate_action(self, game, player):
        actions = [("cards", _("+2 Cards")),
                   ("money", _("+2 Money")),
                   ("trash", _("Trash two cards"))]

        answer = yield Question(game, player, _("What do you want to do?"),
                                actions)

        for info_player in game.following_players(player):
            yield InfoRequest(game, info_player,
                    _("%s chooses '%s'") % (player.name, _(dict(actions)[answer])), [])

        if answer == "cards":
            player.draw_cards(2)
        elif answer == "money":
            player.virtual_money += 2
        elif answer == "trash":
            if player.hand:
                cards = yield SelectHandCards(game, player, count_lower=2, count_upper=2,
                        msg=_("Which cards do you want to trash?"))
            else:
                return
            # trash cards
            for card in cards:
                card.trash(game, player)
            for other_player in game.players:
                if other_player is not player:
                    yield InfoRequest(game, other_player,
                            _("%s trashes these cards:") % (player.name, ), cards)


class Torturer(AttackCard):
    # XXX to be implemented
    name = _("Torturer")
    edition = Intrigue
    cost = 5


class TradingPost(ActionCard):
    # XXX to be implemented
    name = _("Trading Post")
    edition = Intrigue
    cost = 5


class Tribute(ActionCard):
    # XXX to be implemented
    name = _("Tribute")
    edition = Intrigue
    cost = 5


class Upgrade(ActionCard):
    # XXX to be implemented
    name = _("Upgrade")
    edition = Intrigue
    cost = 5


class WishingWell(ActionCard):
    # XXX to be implemented
    name = _("Wishing Well")
    edition = Intrigue
    cost = 3


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
    CardSet('Intrigue Test',
            [Ironworks, Masquerade, ShantyTown, Steward, Swindler]),
]
