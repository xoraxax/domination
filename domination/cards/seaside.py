from domination.cards import TreasureCard, VictoryCard, ActionCard, \
     DurationCard, AttackCard, ReactionCard, CardSet, Seaside
from domination.cards.base import Duchy, Estate, Copper
from domination.gameengine import SelectHandCards, Question, MultipleChoice, \
     InfoRequest, SelectCard, CardTypeRegistry, Defended, YesNoQuestion
from domination.tools import _
from domination.macros.__macros__ import handle_defense

#http://www.boardgamegeek.com/image/586409/dominion-seaside?size=large
class Lookout(ActionCard):
    name = _("Lookout")
    edition = Seaside
    implemented = False #FIXME not implemented completely
    cost = 3
    desc = _("+1 Action. Look at the top 3 Cards of your deck. Trash one of them. Discard one of them. Put the other on top of your deck.")

    def activate_action(self, game, player):
        player.remaining_actions += 1
        pass #FIXME

class MerchantShip(ActionCard, DurationCard):
    name = _("Merchant Ship")
    edition = Seaside
    implemented = False #FIXME not implemented completely
    cost = 5
    desc = _("Now and at the start of next turn: +2 Money")

    def activate_action(self, game, player):
        player.virtual_money += 2
        pass #FIXME

class Navigator(ActionCard):
    name = _("Navigator")
    edition = Seaside
    implemented = False #FIXME not implemented completely
    cost = 4
    desc = _("+2 Money. Look at the top 5 Cards of your deck. Either discard all of them, or put them back on top of your deck in any order.")

    def activate_action(self, game, player):
        player.virtual_money += 2
        pass #FIXME

class PirateShip(AttackCard):
    name = _("Pirate Ship")
    edition = Seaside
    implemented = False #FIXME not implemented completely
    cost = 4
    desc = _("Choose one: Each Player reveals the top 2 cards of his deck, trashes a revealed Treasure that you choose, discards the rest, and if anyone trashed a Treasure you take a Coin token; or + 1 Money per Coin token you have taken with pirate Ships this game.")

    def activate_action(self, game, player):
        pass #FIXME

class Outpost(ActionCard, DurationCard):
    name = _("Outpost")
    edition = Seaside
    implemented = False #FIXME not implemented completely
    cost = 5
    desc = _("You only draw 3 cards (instead of 5) in this turns Clean-up phase. Take an extra turn after this one. This can't cause you to take more than two consecutive turns.")

    def activate_action(self, game, player):
        def extra_turn_with_three():
            pass
        player.register_turn_cleanup(extra_turn_with_three)
        pass #FIXME

class PearlDiver(ActionCard):
    name = _("Pearl Diver")
    edition = Seaside
    implemented = False #FIXME not implemented completely
    cost = 2
    desc = _("+1 Card, +1 Action. Look at the bottom card of your deck. You may put it on top.")

    def activate_action(self, game, player):
        player.remaining_actions += 1
        player.draw_cards(1)
        pass #FIXME

class Salvager(ActionCard):
    name = _("Salvager")
    edition = Seaside
    cost = 4
    desc = _("+1 Buy. Trash a Card from your hand. + Money equal to its costs.")

    def activate_action(self, game, player):
        player.remaining_deals += 1
        if player.hand:
            cards = yield SelectHandCards(game, player, count_lower=1, count_upper=1,
                    msg=_("Which cards do you want to trash?"))
        else:
            return
        # trash cards
        for card in cards:
            player.virtual_money += card.cost
            card.trash(game, player)
        for other_player in game.participants:
            if other_player is not player:
                yield InfoRequest(game, other_player,
                        _("%s trashes these cards:") % (player.name, ), cards)

class SeaHag(AttackCard):
    name = _("Sea Hag")
    edition = Seaside
    implemented = False #FIXME not implemented completely
    cost = 4
    desc = _("Each other player discards the top card of his deck, then gains a Curse card, putting it on top of his deck.")

    def activate_action(self, game, player):
        pass #FIXME

class Smugglers(ActionCard):
    name = _("Smugglers")
    edition = Seaside
    implemented = False #FIXME not implemented completely
    cost = 3
    desc = _("Gain a copy of a Card costing up to 6 that the player to your rigth gained on his last turn.")

    def activate_action(self, game, player):
        pass #FIXME

class Caravan(ActionCard):
    name = _("Caravan")
    edition = Seaside
    implemented = False #FIXME not implemented completely
    cost = 4
    desc = _("+1 Card, +1 Action. At the start of your next turn, +1 Card.")

    def activate_action(self, game, player):
        player.remaining_actions += 1
        player.draw_cards(1)
        pass #FIXME

class Bazaar(ActionCard):
    name = _("Bazaar")
    edition = Seaside
    cost = 5
    desc = _("+1 Card, +2 Actions, +1 Money")

    def activate_action(self, game, player):
        player.remaining_actions += 2
        player.draw_cards(1)
        player.virtual_money += 1

class Cutpurse(AttackCard):
    name = _("Cutpurse")
    edition = Seaside
    cost = 4
    desc = _("+2 Money. Each other player discards a Copper card (or reveals a hand with no Copper).")

    def activate_action(self, game, player):
        player.virtual_money += 2
        #FIXME
        for other_player in game.following_players(player):
            try:
                handle_defense(self, game, other_player)
            except Defended:
                continue
            cards = yield SelectHandCards(game, other_player, count_lower=1, count_upper=1,
                    msg=_("%s played Cutpurse. Which Copper do you want to discard?") % (player.name, ), cls=Copper)
            for card in cards:
                card.discard(other_player)
            for other_player in game.participants:
                if info_player is not other_player:
                    # TODO: info players may only see one of the discarded cards
                    yield InfoRequest(game, info_player,
                            _("%s discards these cards:") % (other_player.name, ), cards)

class Embargo(ActionCard):
    name = _("Embargo")
    edition = Seaside
    implemented = False #FIXME not implemented completely
    cost = 2
    desc = _("+2 Money. Trash this card. Put an Embargo token on top of a Supply pile. When a player buys a card, he gains a Curse card per Embargo token on that pile.")

    def activate_action(self, game, player):
        player.virtual_money += 2
        pass #FIXME

class LigthHouse(ActionCard, DurationCard):
    name = _("Ligthhouse")
    edition = Seaside
    implemented = False #FIXME not implemented completely
    cost = 2
    desc = _("+1 Action. Now and at the Start of your next turn: +1 Money. While this is in play, when another player plays an Attack cardm it doesn't afffect you.")

    def activate_action(self, game, player):
        player.remaining_actions += 1
        pass #FIXME

class GhostShip(AttackCard):
    name = _("Ghost Ship")
    edition = Seaside
    cost = 5
    desc = _("+2 Cards. Each other player with 4 or more cards in hand puts cards from his hand on top of his deck until he has 3 cards in his hand.")

    def activate_action(self, game, player):
        player.draw_cards(2)
        for other_player in game.following_players(player):
            if other_player not in game.kibitzers:
                try:
                    handle_defense(self, game, other_player)
                except Defended:
                    continue
                if len(other_player.hand) < 4:
                    continue
                count = len(other_player.hand) - 3
                cards = yield SelectHandCards(game, other_player, count_lower=count, count_upper=count,
                        msg=_("%s played Ghost Ship. Which cards do you want to put on the top of your deck?") % (player.name, ))
                for card in cards:
                    card.backondeck(other_player)

#http://www.boardgamegeek.com/image/586408/dominion-seaside?size=large

class Haven(ActionCard, DurationCard):
    name = _("Haven")
    edition = Seaside
    implemented = False #FIXME not implemented completely
    cost = 2
    desc = _("+1 Card, + 1 Action. Set aside a Card from your hand face down. At the start of your next turn, put it into your hand.")

    def activate_action(self, game, player):
        player.remaining_actions += 1
        player.draw_cards(1)
        pass #FIXME

class Explorer(ActionCard):
    name = _("Explorer")
    edition = Seaside
    implemented = False #FIXME not implemented completely
    cost = 5
    desc = _("You may reveal a Province card from your hand. If you do, gain a gold card, putting it into your hand. Otherwise, gain a silver card, putting it into your hand.")

    def activate_action(self, game, player):
        pass #FIXME

class FishingVillage(ActionCard, DurationCard):
    name = _("Fishing Village")
    edition = Seaside
    implemented = False #FIXME not implemented completely
    cost = 3
    desc = _("+2 Actions, +1 Money. At the start of your next turn: +1 Action, +1 Money.")

    def activate_action(self, game, player):
        player.remaining_actions += 2
        player.virtual_money += 1
        pass #FIXME

class Warehouse(ActionCard):
    name = _("Warehouse")
    edition = Seaside
    cost = 3
    desc = _("+3 Cards, +1 Actions. Discard 3 Cards.")

    def activate_action(self, game, player):
        player.remaining_actions += 1
        player.draw_cards(2)
        cards = yield SelectHandCards(game, player, count_lower=3, count_upper=3,
                msg=_("Which 3 cards do you want to discard?"))
        # discard cards
        if cards is not None:
            for card in cards:
                card.discard(player)
            for other_player in game.participants:
                if other_player is not player:
                    yield InfoRequest(game, other_player,
                            _("%s discards these cards:") % (player.name, ), cards)

class Treasury(ActionCard):
    name = _("Treasury")
    edition = Seaside
    implemented = False #FIXME not implemented completely
    cost = 5
    desc = _("+1 Card, +1 Action, +1 Money. When you discard this from play, if you didn't buy a Victory card this turn, you may put this on top of your deck.")

    def activate_action(self, game, player):
        player.remaining_actions += 1
        player.draw_cards(1)
        player.virtual_money += 1
        pass #FIXME

class Island(ActionCard, VictoryCard):
    name = _("Island")
    edition = Seaside
    implemented = False #FIXME not implemented completely
    cost = 4
    points = 2
    desc = _("Set aside the survivors of Oceanic fligth 815 from your hand. Return them to your deck at the end of the game.")

    def activate_action(self, game, player):
        pass #FIXME

class Ambassador(AttackCard):
    name = _("Ambassador")
    edition = Seaside
    implemented = False #FIXME not implemented completely
    cost = 3
    desc = _("Reveal a card from your hand. Return 2 copies of it from your hand to the Supply. Then each other player gains a copy of it.")

    def activate_action(self, game, player):
        pass #FIXME

class Tactician(ActionCard, DurationCard):
    name = _("Tactician")
    edition = Seaside
    implemented = False #FIXME not implemented completely
    cost = 5
    desc = _("Discard your hand. If you discarded any cards this way, then at the start of your next turn, +5 Cards, +1 Buy, and +1 Action")

    def activate_action(self, game, player):
        pass #FIXME

class NativeVillage(ActionCard):
    name = _("Native Village")
    edition = Seaside
    implemented = False #FIXME not implemented completely
    cost = 2
    desc = _("+2 Actions. Choose one: Set aside the top card of your deck face down on your Native Village mat; or put all cards from your mat into your hand. You may look at the cards on your mat at any time; return them to your deck at the end of the game.")

    def activate_action(self, game, player):
        player.remaining_actions += 2
        pass #FIXME

class Wharf(ActionCard, DurationCard):
    name = _("Wharf")
    edition = Seaside
    implemented = False #FIXME not implemented completely
    cost = 5
    desc = _("Now and at the start of your next turn: +2 Cards, +1 Buy.")

    def activate_action(self, game, player):
        player.remaining_deals += 1
        player.draw_cards(2)
        pass #FIXME

class TreasureMap(ActionCard):
    name = _("TreasureMap")
    edition = Seaside
    cost = 4
    desc = _("Trash this and another copy of Treasure map from your hand. If you do trash two Treasure maps, gain 4 Gold cards, putting them on top of your deck.")

    def activate_action(self, game, player):
        treasure_map_cards = [c for c in player.hand if isinstance(c, TreasureMap)]
        if len(treasure_map_cards) >= 2:
            for i in range(0, 4):
                card = treasure_map_cards[0]
                card.trash(game, player)
                for other_player in game.participants:
                    yield InfoRequest(game, other_player,
                            _("%s trashes:") % (player.name, ), [card])
            for i in range(0, 4):
                new_card = game.supply["Gold"].pop()
                player.discard_pile.append(new_card)
                for other_player in game.participants:
                    yield InfoRequest(game, other_player,
                            _("%s gains:") % (player.name, ), [new_card])
                for val in game.check_empty_pile("Gold"):
                    yield val


from domination.cards.base import (
    Cellar, CouncilRoom, Festival, Mine)

card_sets = [
    CardSet('Seaside Test',
            [Salvager, Bazaar, Cutpurse, GhostShip, Warehouse, TreasureMap,
             Mine, Cellar, CouncilRoom, Festival])
]
