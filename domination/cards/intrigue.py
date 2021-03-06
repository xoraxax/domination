from domination.cards import TreasureCard, VictoryCard, ActionCard, \
     AttackCard, ReactionCard, CardSet, Intrigue
from domination.cards.base import Duchy, Estate, Copper, Curse
from domination.gameengine import SelectHandCards, Question, MultipleChoice, \
     InfoRequest, SelectCard, Defended, YesNoQuestion
from domination.tools import _
from domination.macros.__macros__ import handle_defense, generator_forward,\
        fetch_card_from_supply


class Baron(ActionCard):
    name = _("Baron")
    edition = Intrigue
    cost = 4
    desc = _("+1 Buy, You may discard an Estate card. If you do, +4 Money."
            " Otherwise gain an Estate card.")

    def activate_action(self, game, player):
        player.remaining_deals += 1
        estate_cards = [c for c in player.hand if isinstance(c, Estate)]
        if estate_cards and (yield YesNoQuestion(game, player,
            _("Do you want to discard an Estate card?"))):
            player.virtual_money += 4
            card = estate_cards[0]
            card.discard(player)
            for info_player in game.following_participants(player):
                yield InfoRequest(game, info_player,
                        _("%s discards:", (player.name, )), [card])
        else:
            estate_pile = game.supply["Estate"]
            if estate_pile:
                new_card = estate_pile.pop()
                player.discard_pile.append(new_card)
                for val in game.check_empty_pile("Estate"):
                    yield val


class Bridge(ActionCard):
    name = _("Bridge")
    edition = Intrigue
    cost = 4
    desc = _("+1 Buy, +1 Money, All cards (including cards in players'"
            " hands) cost 1 Money less this turn, but not less than"
            " 0 Money.")

    def activate_action(self, game, player):
        player.remaining_deals += 1
        player.virtual_money += 1
        decreased_for_cards = []
        for card in game.card_classes.itervalues():
            if card.cost >= 1:
                card.cost -= 1
                decreased_for_cards.append(card)
        def restore_cards(player):
            for card in decreased_for_cards:
                card.cost += 1
        player.register_turn_cleanup(restore_cards)


class Conspirator(ActionCard):
    name = _("Conspirator")
    edition = Intrigue
    cost = 4
    desc = _("+2 Money, If you've played 3 or more Actions this turn (counting"
             " this): +1 Card, +1 Action")

    def activate_action(self, game, player):
        player.virtual_money += 2
        if len(player.activated_cards) >= 3:
            player.draw_cards(1)
            player.remaining_actions += 1


class Coppersmith(ActionCard):
    name = _("Coppersmith")
    edition = Intrigue
    cost = 4
    desc = _("Copper produces an extra 1 Money this turn.")

    def activate_action(self, game, player):
        Copper.worth += 1
        def restore_copper(player):
            Copper.worth -= 1
        player.register_turn_cleanup(restore_copper)



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
            game.card_classes.itervalues() if c.cost <= 4 and
            game.supply.get(c.__name__) and c.potioncost == 0],
            msg=_("Select a card that you want to have."), show_supply_count=True)
        new_card = game.supply[card_cls.__name__].pop()
        player.discard_pile.append(new_card)
        for info_player in game.following_participants(player):
            yield InfoRequest(game, info_player,
                    _("%s gains:", (player.name, )), [new_card])
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
            cards = yield SelectHandCards(game, player, count_lower=0, count_upper=1,
                    msg=_("Which card do you want to trash?"))
        # trash cards
        if cards:
            for card in cards:
                card.trash(game, player)
            for other_player in game.following_participants(player):
                yield InfoRequest(game, other_player,
                        _("%s trashes this card:", (player.name, )), cards)


class MiningVillage(ActionCard):
    name = _("Mining Village")
    edition = Intrigue
    cost = 4
    desc = _("+1 Card, +2 Actions, You may trash this card immediately."
             " If you do, +2 Money.")

    def activate_action(self, game, player):
        player.draw_cards(1)
        player.remaining_actions +=2

        if (yield YesNoQuestion(game, player,
            _("Do you want to trash your Mining Village?"))):
            self.trash_after_playing = True
            player.virtual_money += 2


class Minion(AttackCard):
    name = _("Minion")
    edition = Intrigue
    cost = 5
    desc = _("+1 Action, Choose one: +2 Money, or discard your hand, +4 Cards, and each"
            " other player with at least 5 cards in hand discards his hand"
            " and draws 4 cards.")

    def activate_action(self, game, player):
        player.remaining_actions += 1
        actions = [("money", _("+2 Money")),
                   ("cards", _("Discard hand and draw 4 cards, "
                               "attack other players"))]
        answer = yield Question(game, player, _("What do you want to do?"),
                                actions)

        for info_player in game.following_participants(player):
            yield InfoRequest(game, info_player,
                    _("%(player)s chooses '%(action)s'", {"player": player.name, "action": _(dict(actions)[answer])}), [])

        if answer == "money":
            player.virtual_money += 2
        else:
            original_hand = player.hand[:]
            for card in original_hand:
                card.discard(player)
            player.draw_cards(4)
            for info_player in game.following_participants(player):
                yield InfoRequest(
                    game, info_player,
                    _("%s discards this hand and draws 4 cards:",
                    (player.name, )), original_hand)

            for other_player in game.following_players(player):
                if len(other_player.hand) < 5:
                    continue
                try:
                    handle_defense(self, game, other_player)
                except Defended:
                    continue
                original_hand = other_player.hand[:]
                for card in original_hand:
                    card.discard(other_player)
                other_player.draw_cards(4)
                yield InfoRequest(
                    game, other_player,
                    _("You discard your hand and draw 4 cards."), [])
                for info_player in game.following_participants(other_player):
                    yield InfoRequest(
                        game, info_player,
                        _("%s discards this hand and draws 4 cards:",
                        (other_player.name, )), original_hand)


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

        for info_player in game.following_participants(player):
            yield InfoRequest(game, info_player,
                    _("%(player)s chooses '%(action)s'", {"player": player.name, "action": _(dict(actions)[answer])}), [])

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

        for info_player in game.following_participants(player):
            chosen = ", ".join(_(dict(choices)[c]) for c in choice)
            yield InfoRequest(game, info_player,
                    _("%(player)s chooses '%(action)s'", {"player": player.name, "action": chosen}), [])

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
    name = _("Saboteur")
    edition = Intrigue
    cost = 5
    desc = _("Each other player reveals cards from the top of his deck until "
             "revealing one costing 3 or more. He trashes that card and may gain "
             "a card costing at most 2 less than it. He discards the other "
             "revealed cards.")

    def activate_action(self, game, player):
        for other_player in game.following_participants(player):
            revealed_cards = []
            try:
                handle_defense(self, game, other_player)
            except Defended:
                continue
            cost = None
            while cost is None or cost < 3:
                if other_player.draw_cards(1) is None:
                    break
                card = other_player.hand.pop()
                revealed_cards.append(card)
                cost = card.cost
            for info_player in game.participants:
                yield InfoRequest(game, info_player, _("%s reveals these cards:",
                (other_player.name, )), revealed_cards)
            # last card in revealed cards is the one costing 3 or more
            # except if the deck is empty
            if revealed_cards and revealed_cards[-1].cost >= 3:
                game.trash_pile.append(revealed_cards[-1])

                # gain a card, XXX missing cancel
                card_cls = yield SelectCard(game, other_player, card_classes=[c for c in
                    game.card_classes.itervalues() if c.cost <= revealed_cards[-1].cost - 2 and
                    game.supply.get(c.__name__) and c.potioncost == 0],
                    msg=_("Select a card that you want to have."), show_supply_count=True)
                new_card = game.supply[card_cls.__name__].pop()
                other_player.discard_pile.append(new_card)
                for info_player in game.following_participants(other_player):
                    yield InfoRequest(game, info_player,
                            _("%s gains:", (other_player.name, )), [new_card])
                for val in game.check_empty_pile(card_cls.__name__):
                    yield val
            # We put nearly all cards together onto the discard pile
            other_player.discard_pile.extend(revealed_cards[:-1])


class Scout(ActionCard):
    name = _("Scout")
    edition = Intrigue
    cost = 4
    desc = _("+1 Action, Reveal the top 4 cards of your deck. Put the revealed"
             " Victory cards into your hand. Put the other cards on top of your"
             " deck in any order.")

    def activate_action(self, game, player):
        player.remaining_actions += 1
        player.draw_cards(4)
        drawn, player.hand = player.hand[-4:], player.hand[:-4]

        for info_player in game.participants:
            yield InfoRequest(game, info_player, _("%s reveals the top 4 cards of his"
                " deck:", (player.name, )), drawn)
        victory_cards = [c for c in drawn if isinstance(c, VictoryCard)]
        player.hand.extend(victory_cards)
        drawn = [c for c in drawn if not isinstance(c, VictoryCard)]
        while drawn:
            drawn_classes = [type(c) for c in drawn]
            card_cls = (yield SelectCard(game, player,
                _("Which card do you want to put onto the deck next?"),
                card_classes=drawn_classes))
            card = [c for c in drawn if isinstance(c, card_cls)][0]
            drawn.remove(card)
            player.deck.append(card)


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
        for info_player in game.following_participants(player):
            yield InfoRequest(game, info_player,
                _("%s discards these cards:", (player.name, )), cards)

    def defend_action(self, game, player, card):
        player.draw_cards(2)
        cards = yield SelectHandCards(
            game, player, count_lower=2, count_upper=2,
            msg=_("Which cards do you want to put on your deck?"))
        if not cards:
            return
        for card in cards:
            card.backondeck(game, player)


class ShantyTown(ActionCard):
    name = _("Shanty Town")
    edition = Intrigue
    cost = 3
    desc = _("+2 Actions, Reveal your hand. If you have no action cards in hand,"
             " +2 Cards.")

    def activate_action(self, game, player):
        player.remaining_actions += 2

        for info_player in game.following_participants(player):
            yield InfoRequest(game, info_player, _("%s reveals his hand:",
                    (player.name, )), player.hand[:])

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
                handle_defense(self, game, other_player)
            except Defended:
                continue
            if other_player.draw_cards(1) is None:
                continue
            card = other_player.hand.pop()
            for info_player in game.participants:
                yield InfoRequest(game, info_player, _("%s trashes:",
                        (other_player.name, )), [card])

            req = SelectCard(game, player, card_classes=[c for c in
                game.card_classes.itervalues() if c.cost == card.cost and
                game.supply.get(c.__name__)],
                msg=_("Select a card that you want to give."), show_supply_count=True)
            if not req.fulfillable():
                continue
            card_cls = yield req
            new_card = game.supply[card_cls.__name__].pop()
            other_player.discard_pile.append(new_card)
            for info_player in game.following_participants(player):
                yield InfoRequest(game, info_player,
                        _("%s gains:", (other_player.name, )), [new_card])
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

        for info_player in game.following_participants(player):
            yield InfoRequest(game, info_player,
                    _("%(player)s chooses '%(action)s'", {"player": player.name, "action": _(dict(actions)[answer])}), [])

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
            for other_player in game.participants:
                if other_player is not player:
                    yield InfoRequest(game, other_player,
                            _("%s trashes these cards:", (player.name, )), cards)


class Torturer(AttackCard):
    name = _("Torturer")
    edition = Intrigue
    cost = 5
    desc = _("+3 Cards, Each other player chooses one: he discards 2 cards; or he gains a Curse card, putting it in his hand.")

    def activate_action(self, game, player):
        player.draw_cards(3)
        for other_player in game.following_players(player):
            try:
                handle_defense(self, game, other_player)
            except Defended:
                continue
            choices = [("discard",   _("discard 2 cards")),
                       ("curse",  _("gain a Curse"))]
            choice = yield Question(game, other_player, _("What do you want to do?"), choices)

            for info_player in game.following_participants(player):
                yield InfoRequest(game, info_player,
                        _("%(player)s choose to '%(action)s'", {"player": other_player.name, "action": choice}), [])

            if choice == "discard":
                cards = yield SelectHandCards(game, other_player, count_lower=2, count_upper=2,
                        msg=_("%s played Torturer, you chose to discard two cards. Which cards do you want to discard?", (player.name, )))
                for card in cards:
                    card.discard(other_player)
                for info_player in game.participants:
                    if info_player is not other_player:
                        # TODO: info players may only see one of the discarded cards
                        yield InfoRequest(game, info_player,
                                _("%s discards these cards:", (other_player.name, )), cards)
            elif choice == "curse":
                with fetch_card_from_supply(game, Curse) as new_card:
                    other_player.discard_pile.append(new_card)
                for info_player in game.following_participants(other_player):
                    yield InfoRequest(game, info_player,
                            _("%s tortures %s. He gains a curse card.", (player.name, other_player.name)), [])

class TradingPost(ActionCard):
    name = _("Trading Post")
    edition = Intrigue
    cost = 5
    desc = _("Trash 2 cards from your hand. If you do, gain a Silver card; put it into your hand.")

    def activate_action(self, game, player):
        if player.hand:
            cards = yield SelectHandCards(game, player, count_lower=2, count_upper=2,
                    msg=_("Which cards do you want to trash?"))
        else:
            return
        # trash cards
        for card in cards:
            card.trash(game, player)
        for info_player in game.following_participants(player):
            yield InfoRequest(game, info_player,
                    _("%s trashes these cards:", (player.name, )), cards)
        if game.supply["Silver"]:
            new_card = game.supply["Silver"].pop()
            player.hand.append(new_card)
            for info_player in game.following_participants(player):
                yield InfoRequest(game, info_player,
                        _("%s gains:", (player.name, )), [new_card])
            for val in game.check_empty_pile("Silver"):
                yield val

class Tribute(ActionCard):
    name = _("Tribute")
    edition = Intrigue
    cost = 5
    desc = _("The player to your left reveals then discards the top 2 cards "
             "of his deck. For each differently named card revealed, if it is "
             "an Action Card: +2 Actions. If it is a Treasure Card: +2 Money. "
             "If it is a Victory Card: +2 Cards.")

    def activate_action(self, game, player):
        cards = []
        other_player = player.left(game)
        other_player.draw_cards(2)
        drawn, other_player.hand = other_player.hand[-2:], other_player.hand[:-2]
        for info_player in game.participants:
            yield InfoRequest(game, info_player, _("%s reveals the top 2 cards of his deck:",
                    (other_player.name, )), drawn)
        for i,card in enumerate(drawn):
            if i == 1 and drawn[1].__name__ == drawn[0].__name__:
                other_player.discard_pile.append(card)
                break
            if isinstance(card, ActionCard):
                player.remaining_actions += 2
            if isinstance(card, TreasureCard):
                player.virtual_money += 2
            if isinstance(card, VictoryCard):
                player.draw_cards(2)
            other_player.discard_pile.append(card)

class Upgrade(ActionCard):
    name = _("Upgrade")
    edition = Intrigue
    cost = 5
    desc = _("+1 Card, +1 Action, Trash a card from your hand. Gain a card costing exactly 1 more than it.")

    def activate_action(self, game, player):
        player.remaining_actions += 1
        player.draw_cards(1)

        if not player.hand:
            return
        cards = yield SelectHandCards(game, player,
                    count_lower=0, count_upper=1,
                    msg=_("Select a card you want to trash."))
        if cards:
            card = cards[0]
            selectable_card_classes=[c for c in game.card_classes.itervalues() if c.cost == card.cost + 1 and game.supply.get(c.__name__) and c.potioncost == card.potioncost]
            new_card = None
            if selectable_card_classes:
                card_cls = yield SelectCard(game, player, card_classes=selectable_card_classes,
                    msg=_("Select a card that you want to have."), show_supply_count=True)
                new_card = game.supply[card_cls.__name__].pop()
                player.discard_pile.append(new_card)
            card.trash(game, player)

            for info_player in game.following_participants(player):
                yield InfoRequest(game, info_player,
                        _("%s trashes:", (player.name, )), [card])
                if new_card:
                    yield InfoRequest(game, info_player,
                            _("%s gains:", (player.name, )), [new_card])
            if new_card:
                for val in game.check_empty_pile(card_cls.__name__):
                    yield val



class WishingWell(ActionCard):
    name = _("Wishing Well")
    edition = Intrigue
    cost = 3
    desc = _("+1 Card, +1 Action, Name a card. Reveal the top card of your "
             "deck. If it's the named card, put it into your hand.")

    def activate_action(self, game, player):
        player.draw_cards(1)
        player.remaining_actions += 1
        card_cls = yield SelectCard(game, player, card_classes=[c for c in
            game.card_classes.itervalues() if
            c.__name__ in game.supply],
            msg=_("Name a card."), show_supply_count=True)

        for info_player in game.following_participants(player):
            yield InfoRequest(game, info_player, _("%s names:", (player.name, )),
                    [card_cls])
        player.draw_cards(1)
        card = player.hand.pop()
        for info_player in game.participants:
            yield InfoRequest(game, info_player, _("%s reveals:",
                    (player.name, )), [card])
        if isinstance(card, card_cls):
            player.hand.append(card)
        else:
            player.deck.append(card)


from domination.cards.base import (
    Bureaucrat, Cellar, Chancellor, CouncilRoom, Festival, Library, Mine,
    Militia, Remodel, Spy, Thief, ThroneRoom, Witch)

card_sets = [
    CardSet(_('Victory Dance [I]'),
            [Bridge, Duke, GreatHall, Harem, Ironworks, Masquerade, Nobles,
             Pawn, Scout, Upgrade]),
    CardSet(_('Secret Schemes [I]'),
            [Conspirator, Harem, Ironworks, Pawn, Saboteur, ShantyTown,
             Steward, Swindler, TradingPost, Tribute]),
    CardSet(_('Best Wishes [I]'),
            [Coppersmith, Courtyard, Masquerade, Scout, ShantyTown, Steward,
             Torturer, TradingPost, Upgrade, WishingWell]),
    CardSet(_('Deconstruction [B&I]'),
            [Bridge, MiningVillage, Remodel, Saboteur, SecretChamber, Spy,
             Swindler, Thief, ThroneRoom, Torturer]),
    CardSet(_('Hand Madness [B&I]'),
            [Bureaucrat, Chancellor, CouncilRoom, Courtyard, Mine, Militia,
             Minion, Nobles, Steward, Torturer]),
    CardSet(_('Underlings [B&I]'),
            [Baron, Cellar, Festival, Library, Masquerade, Minion, Nobles,
             Pawn, Steward, Witch]),
]
