from domination.cards import TreasureCard, VictoryCard, ActionCard, \
     AttackCard, ReactionCard, CardSet, Alchemy
from domination.cards.base import Duchy, Estate, Copper, Gold
from domination.gameengine import SelectHandCards, Question, MultipleChoice, \
     InfoRequest, SelectCard, CardTypeRegistry, Defended, YesNoQuestion
from domination.tools import _
from domination.macros.__macros__ import handle_defense, generator_forward,\
        fetch_card_from_supply


class Potion(TreasureCard):
    name = _("Potion")
    edition = Alchemy
    cost = 4
    worth = 0
    potion = 1


class Vineyard(VictoryCard):
    name = _("Vineyard")
    edition = Alchemy
    optional = True
    cost = 2
    desc = _("Worth 1 point for every 3 Action Cards in your deck (rounded down)")

    def get_points(self, game, player):
        assert not player.hand and not player.discard_pile
        return len([card for card in player.deck if isinstance(card, ActionCard) ]) / 3


class Alchemist(ActionCard):
    name = _("Alchemist")
    edition = Alchemy
    cost = 3
    potioncost = 1
    desc = _("+2 Cards, + 1 Action. When you discard this from play, you may put"
             " this on top of your deck if you have a Potion in play.")

    def activate_action(self, game, player):
        player.remaining_actions += 1
        player.draw_cards(2)
        def remove_from_aux_cards(p):
            player.deck.append(self)
            player.aux_cards.remove(self)

        if any(isinstance(c, Potion) for c in player.hand):
            if (yield YesNoQuestion(game, player, _("Do you want to put your alchemist card"
                " onto your deck when cleaning up?"))):
                player.register_turn_cleanup(remove_from_aux_cards)


class Apothecary(ActionCard):
    name = _("Apothecary")
    edition = Alchemy
    cost = 2
    potioncost = 1
    desc = _("+1 Card, +1 Action. Reveal the top 4 cards of your deck. Put the revealed"
             " Coppers and Potions into your hand. Put the other cards back on top of"
             " your deck in any order.")

    def activate_action(self, game, player):
        player.remaining_actions += 1
        player.draw_cards(1)
        player.draw_cards(4)
        player.hand, new_cards = player.hand[:-4], player.hand[-4:]
        for info_player in game.participants:
            yield InfoRequest(game, info_player, _("%s reveals:") % (player.name, ),
                    new_cards)
        copper_and_potions = [c for c in new_cards if isinstance(c, (Copper, Potion))]
        remaining_cards = [c for c in new_cards if not isinstance(c, (Copper, Potion))]
        player.hand.extend(copper_and_potions)
        while remaining_cards:
            card_classes = [type(c) for c in remaining_cards]
            card_cls = (yield SelectCard(game, player,
                _("Which card do you want to put onto your deck next?"),
                card_classes=card_classes))
            card = [c for c in remaining_cards if isinstance(c, card_cls)][0]
            remaining_cards.remove(card)
            player.deck.append(card)

class Apprentice(ActionCard):
    name = _("Apprentice")
    edition = Alchemy
    cost = 5
    desc = _("+1 Action. Trash a card from your hand. +1 Card per Money it costs."
             " +2 Cards if it has potion in its cost.")

    def activate_action(self, game, player):
        player.remaining_actions += 1
        if player.hand:
            cards = yield SelectHandCards(game, player, count_lower=1, count_upper=1,
                    msg=_("Which card do you want to trash?"))
        else:
            return
        # trash card
        if cards:
            card = cards[0]
            drawcount = card.cost
            if card.potioncost:
                drawcount += 2
            card.trash(game, player)
            player.draw_cards(drawcount)
        for other_player in game.participants:
            if other_player is not player:
                yield InfoRequest(game, other_player,
                        _("%s trashes these cards:") % (player.name, ), cards)


class Familiar(AttackCard):
    name = _("Familiar")
    edition = Alchemy
    cost = 3
    potioncost = 1
    desc = _("+1 Card, +1 Action. Each other player gains a Curse.")

    def activate_action(self, game, player):
        player.remaining_actions += 1
        player.draw_cards(1)
        curse_cards = game.supply["Curse"]
        for other_player in game.following_players(player):
            if curse_cards:
                try:
                    handle_defense(self, game, other_player)
                except Defended:
                    continue
                other_player.discard_pile.append(curse_cards.pop())
                yield InfoRequest(game, other_player,
                        _("%s curses you. You gain a curse card.") % (player.name, ), [])
                for val in game.check_empty_pile("Curse"):
                    yield val


class Golem(ActionCard):
    name = _("Golem")
    edition = Alchemy
    cost = 4
    potioncost = 1
    desc = _("Reveal cards from your deck until you reveal 2 Action cards other"
             " than Golem cards. Discard the other cards, then play the Action"
             " cards in any order.")

    def activate_action(self, game, player):
        action_cards_found = 0
        shuffled = 0
        found_cards = []
        to_be_discarded = []
        while True:
            ret = player.draw_cards(1)
            if ret is None: # no cards left
                break
            shuffled += ret
            if shuffled == 2: # we shuffled our discard_pile 2 times, abort
                break
            card = player.hand.pop()
            for info_player in game.participants:
                yield InfoRequest(game, info_player, _("%s reveals:") % (player.name, ), [card])
            if isinstance(card, ActionCard) and not isinstance(card, Golem):
                found_cards.append(card)
                action_cards_found += 1
                if action_cards_found == 2:
                    break
            else:
                to_be_discarded.append(card)
        player.discard_pile.extend(to_be_discarded)
        while found_cards:
            card_classes = [type(c) for c in found_cards]
            card_cls = (yield SelectCard(game, player,
                _("Which card do you want to play next?"),
                card_classes=card_classes))
            card = [c for c in found_cards if isinstance(c, card_cls)][0]
            found_cards.remove(card)

            player.aux_cards.append(card)
            gen = game.play_action_card(player, card)
            generator_forward(gen)
            if card.trash_after_playing:
                player.aux_cards.remove(card)
                game.trash_pile.append(card)


class Herbalist(ActionCard):
    name = _("Herbalist")
    edition = Alchemy
    cost = 2
    desc = _("+1 Buy, +1 Money. If you discard this from play, you may put one"
             " of your Treasures from play on top of your deck.")

    def activate_action(self, game, player):
        player.remaining_deals += 1
        player.virtual_money += 1
        def handle_discard_action(p):
            treasure_cards = [c for c in player.hand if isinstance(c, TreasureCard)]
            treasure_card_classes = [type(c) for c in treasure_cards]
            if treasure_card_classes:
                card_cls = (yield SelectCard(game, player,
                    _("Which treasure do you want to put on top of your deck?"),
                    card_classes=treasure_card_classes))
                card = [c for c in treasure_cards if isinstance(c, card_cls)][0]
                player.deck.append(card)
                player.hand.remove(card)
        player.register_turn_cleanup(handle_discard_action)


class PhilosophersStone(TreasureCard):
    name = _("Philosophers Stone")
    edition = Alchemy
    cost = 3
    potioncost = 1
    desc = _("Worth 1 Point for every three Action cards in your deck (rounded down).")

    def get_worth(self, player):
        return (len(player.hand) + len(player.discard_pile)) / 3


class Possession(ActionCard):
    name = _("Possession")
    edition = Alchemy
    implemented = False #FIXME not implemented completely
    cost = 6
    potioncost = 1
    desc = _("The player to your left takes an extra turn after this one, in which you"
             " can see all the cards he can and make all decisions for him. Any cards"
             " he would gain on that turn, you gain instead, any cards of his that are"
             " trashed are set aside and returned to his discard pile at the end of turn.")

    def activate_action(self, game, player):
        pass #FIXME


class ScryingPool(AttackCard):
    name = _("Scrying Pool")
    edition = Alchemy
    cost = 2
    potioncost = 1
    desc = _("Each player (including you) reveals the top card of his deck and either"
             " discards it or puts it back, your choice. Then reveal cards from the top"
             " of your deck until you reveal one that is not an Action. Put all your"
             " revealed cards into your hand.")

    def activate_action(self, game, player):
        for other_player in game.players:
            try:
                handle_defense(self, game, other_player)
            except Defended:
                continue
            other_player.draw_cards(1)
            card = other_player.hand.pop()
            for info_player in game.participants:
                yield InfoRequest(game, info_player, _("%s reveals the top card of his deck:") %
                        (other_player.name, ), [card])
            if (yield YesNoQuestion(game, player,
                _("Do you want to discard %(name)s's card '%(cardname)s'?") %
                {"cardname": card.name, "name": other_player.name})):
                other_player.discard_pile.append(card)
                for info_player in game.following_participants(player):
                    yield InfoRequest(game, info_player,
                            _("%(playername)s discarded %(player2name)s's card:") %
                            {"playername": player.name, "player2name": other_player.name},
                            [card])
            else:
                other_player.deck.append(card)

        shuffled = 0
        while True:
            ret = player.draw_cards(1)
            if ret is None: # no cards left
                break
            shuffled += ret
            if shuffled == 2: # we shuffled our discard_pile 2 times, abort
                break
            card = player.hand.pop()
            for info_player in game.participants:
                yield InfoRequest(game, info_player, _("%s reveals:") % (player.name, ),
                        [card])
            player.hand.append(card)
            if not isinstance(card, ActionCard):
                break


class Transmute(ActionCard):
    name = _("Transmute")
    edition = Alchemy
    cost = 0
    potioncost = 1
    desc = _("Trash a card from your hand. If it is an Action Card, gain a Duchy. If it is a Treasure card, gain a Transmute. If it is a Victory Card, gain a Gold.")

    def activate_action(self, game, player):
        cards = yield SelectHandCards(game, player, count_lower=1, count_upper=1,
                msg=_("Which card do you want to trash?"))
        if cards:
            card = cards[0]
            for other_player in game.following_participants(player):
                yield InfoRequest(game, other_player,
                        _("%s trashes this card:") % (player.name, ), cards)
            card.trash(game, player)
            if isinstance(card, ActionCard):
                with fetch_card_from_supply(game, Duchy) as new_card:
                    player.discard_pile.append(new_card)
                    for info_player in game.following_participants(player):
                        yield InfoRequest(game, info_player,
                            _("%s gains:") % (other_player.name, ), [new_card])
            if isinstance(card, TreasureCard):
                with fetch_card_from_supply(game, Transmute) as new_card:
                    player.discard_pile.append(new_card)
                    for info_player in game.following_participants(player):
                        yield InfoRequest(game, info_player,
                                _("%s gains:") % (other_player.name, ), [new_card])
            if isinstance(card, VictoryCard):
                with fetch_card_from_supply(game, Gold) as new_card:
                    player.discard_pile.append(new_card)
                    for info_player in game.following_participants(player):
                        yield InfoRequest(game, info_player,
                                _("%s gains:") % (other_player.name, ), [new_card])


class University(ActionCard):
    name = _("University")
    edition = Alchemy
    cost = 2
    potioncost = 1
    desc = _("+2 Actions. You may gain an Action card costing up to 5.")

    def activate_action(self, game, player):
        player.remaining_actions += 2
        card_classes = [c for c in CardTypeRegistry.card_classes.itervalues()
                        if c.cost <= 5 and c.potioncost == 0 and
                        game.supply.get(c.__name__) and
                        issubclass(c, ActionCard)]
        card_cls = yield SelectCard(game, player, card_classes=card_classes,
            msg=_("Select a action card that you want to have."), show_supply_count=True)
        if card_cls:
            new_card = game.supply[card_cls.__name__].pop()
            player.discard_pile.append(new_card)

            for info_player in game.participants:
                if info_player is not player:
                    yield InfoRequest(game, info_player,
                            _("%s gains:") % (player.name, ), [new_card])
            for val in game.check_empty_pile(card_cls.__name__):
                yield val


from domination.cards.base import \
    Bureaucrat, Cellar, CouncilRoom, Library, Mine, ThroneRoom,\
    Gardens, Laboratory, Thief, Chancellor, Festival, Militia, Smithy,\
    Market, Moat, Remodel, Witch, Woodcutter

from domination.cards.intrigue import \
    GreatHall, Minion, Pawn, Steward, Bridge, Masquerade, Nobles, ShantyTown,\
    Torturer, Baron, WishingWell, Conspirator, Coppersmith, Ironworks,\
    TradingPost

card_sets = [
        CardSet(u"Forbidden Arts [A&D]",
            [Apprentice, Familiar, Possession, University, Cellar, CouncilRoom,
                Gardens, Laboratory, Thief, ThroneRoom]),
        CardSet(u"Potion Mixers [A&D]",
            [Alchemist, Apothecary, Golem, Herbalist, Transmute, Cellar, Chancellor,
                Festival, Militia, Smithy]),
        CardSet(u"Chemistry Lesson [A&D]",
            [Alchemist, Golem, PhilosophersStone, University, Bureaucrat, Market,
                Moat, Remodel, Witch, Woodcutter]),
        CardSet(u"Servants [A&I]",
            [Golem, Possession, ScryingPool, Transmute, Vineyard, Conspirator,
                GreatHall, Minion, Pawn, Steward]),
        CardSet(u"Secret Research [A&I]",
            [Familiar, Herbalist, PhilosophersStone, University, Bridge,
                Masquerade, Minion, Nobles, ShantyTown, Torturer]),
        CardSet(u"Pools, Tools, and Fools [A&I]",
            [Apothecary, Apprentice, Golem, ScryingPool, Baron, Coppersmith,
                Ironworks, Nobles, TradingPost, WishingWell]),
]

