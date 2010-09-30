from domination.cards import TreasureCard, VictoryCard, ActionCard, \
     AttackCard, ReactionCard, CardSet, Alchemy
from domination.cards.base import Duchy, Estate, Copper
from domination.gameengine import SelectHandCards, Question, MultipleChoice, \
     InfoRequest, SelectCard, CardTypeRegistry, Defended, YesNoQuestion
from domination.tools import _
from domination.macros.__macros__ import handle_defense


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
    points = 0
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
        if any(isinstance(c, Potion) for c in player.hand):
            if (yield YesNoQuestion(game, player, _("Do you want to put your alchemist card"
                " onto your deck?"))):
                player.aux_cards.remove(self)
                player.deck.append(self)


class Apothecary(ActionCard):
    name = _("Apothecary")
    edition = Alchemy
    implemented = False #FIXME not implemented completely
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
                    [new_cards])
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
    desc = _("+1 Action. Trash a card from your hand. +1 Card per Money it costs. +2 Cards if it has potion in its cost.")

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
    implemented = False #FIXME not implemented completely
    cost = 4
    potioncost = 1
    desc = _("Reveal cards from your deck until you reveal 2 Action cards other than Golem cards. Discard the other cards, then play the Action cards in any order.")

    def activate_action(self, game, player):
        pass #FIXME


class Herbalist(ActionCard):
    name = _("Herbalist")
    edition = Alchemy
    implemented = False #FIXME not implemented completely
    cost = 2
    desc = _("+1 Buy, +1 Money. If you discard this from play, you may put one of your Treasures from play on top of your deck.")

    def activate_action(self, game, player):
        player.remaining_deals += 1
        player.virtual_money += 1
        pass #FIXME


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
    desc = _("The player to your left takes an extra turn after this one, in which you can see all the cards he can and make all decisions for him. Any cards he would gain on that turn, you gain instead, any cards of his that are trashed are set aside and returned to his discard pile at the end of turn.")

    def activate_action(self, game, player):
        pass #FIXME


class ScryingPool(AttackCard):
    name = _("Scrying Pool")
    edition = Alchemy
    implemented = False #FIXME not implemented completely
    cost = 2
    potioncost = 1
    desc = _("Each player (including you) reveals the top card of his deck and either discards it or puts it back, your choice. The reveal cards from the top of your deck until you reveal one that is not an Action. Put all your revealed cards into your hand.")

    def activate_action(self, game, player):
        pass #FIXME


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
                new_card = game.supply["Duchy"].pop()
                for val in game.check_empty_pile("Duchy"):
                    yield val
                player.discard_pile.append(new_card)
                for info_player in game.following_participants(player):
                    yield InfoRequest(game, info_player,
                            _("%s gains:") % (other_player.name, ), [new_card])
            if isinstance(card, TreasureCard):
                new_card = game.supply["Transmute"].pop()
                for val in game.check_empty_pile("Transmute"):
                    yield val
                player.discard_pile.append(new_card)
                for info_player in game.following_participants(player):
                    yield InfoRequest(game, info_player,
                            _("%s gains:") % (other_player.name, ), [new_card])
            if isinstance(card, VictoryCard):
                new_card = game.supply["Gold"].pop()
                for val in game.check_empty_pile("Gold"):
                    yield val
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

