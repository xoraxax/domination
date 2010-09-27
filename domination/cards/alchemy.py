from domination.cards import TreasureCard, VictoryCard, ActionCard, \
     AttackCard, ReactionCard, CardSet, Alchemy
from domination.cards.base import Duchy, Estate, Copper
from domination.gameengine import SelectHandCards, Question, MultipleChoice, \
     InfoRequest, SelectCard, CardTypeRegistry, Defended, YesNoQuestion
from domination.tools import _
from domination.macros.__macros__ import handle_defense

#http://www.boardgamegeek.com/image/709729/dominion-alchemy?size=large

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
    implemented = False #FIXME not implemented completely
    cost = 3
    potioncost = 1
    desc = _("+2 Cards, + 1 Action. When you discard this from play, you may put this on top of your deck if you have a Potion in play.")

    def activate_action(self, game, player):
        player.remaining_actions += 1
        player.draw_cards(2)
        pass #FIXME


class Apothecary(ActionCard):
    name = _("Apothecary")
    edition = Alchemy
    implemented = False #FIXME not implemented completely
    cost = 2
    potioncost = 1
    desc = _("+1 Card, +1 Action. Reveal the top 4 cards of your deck. Put the revealed Coppers and Potions into your hand. Put the other cartds back on top of your deck in any order.")

    def activate_action(self, game, player):
        player.remaining_actions += 1
        player.draw_cards(1)
        pass #FIXME


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
        for other_player in game.players:
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


class PhilosophersStone(TreasureCard): #Fehlt
    name = _("Philosophers Stone")
    edition = Alchemy
    cost = 3
    potioncost = 1
    desc = _("")

    def get_worth(self, player):
        return (len(player.hand) + len(player.discard_pile))/5


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
    implemented = False #FIXME not implemented completely
    cost = 0
    potioncost = 1
    desc = _("Trash a card from your hand. If it is an Action Card, gain a Duchy. If it is a Treasure card, gain a Transmute. If it is a Victory Card, gain a Gold.")

    def activate_action(self, game, player):
        pass #FIXME


class University(ActionCard):
    name = _("University")
    edition = Alchemy
    cost = 2
    potioncost = 1
    desc = _("+2 Actions. You may gain an Action card costing up to 5.")

    def activate_action(self, game, player):
        player.remaining_actions += 2
        card_classes = [c for c in CardTypeRegistry.card_classes.itervalues()
                        if c.cost <= 5 and
                        game.supply.get(c.__name__) and
                        issubclass(c, ActionCard)]
        card_cls = yield SelectCard(game, player, card_classes=card_classes,
            msg=_("Select a action card that you want to have."), show_supply_count=True)
        new_card = game.supply[card_cls.__name__].pop()
        player.discard_pile.append(new_card)

        for info_player in game.players:
            if info_player is not player:
                yield InfoRequest(game, info_player,
                        _("%s gains:") % (player.name, ), [new_card])
        for val in game.check_empty_pile(card_cls.__name__):
            yield val


from domination.cards.base import (
    Bureaucrat, Cellar, CouncilRoom, Library, Mine, ThroneRoom)

card_sets = [
    CardSet('Alchemy Test',
            [Apprentice, Potion, Familiar, PhilosophersStone, University,
             Mine, CouncilRoom, Cellar, Library, ThroneRoom])
]
