from domination.cards import TreasureCard, VictoryCard, ActionCard, \
     DurationCard, AttackCard, ReactionCard, CardSet, Seaside
from domination.cards.base import Duchy, Estate, Copper, Province
from domination.gameengine import SelectHandCards, Question, MultipleChoice, \
     InfoRequest, SelectCard, Defended, YesNoQuestion
from domination.tools import _
from domination.macros.__macros__ import handle_defense


class Lookout(ActionCard):
    name = _("Lookout")
    edition = Seaside
    cost = 3
    desc = _("+1 Action. Look at the top 3 Cards of your deck. Trash one of them. Discard one of them. Put the other one on top of your deck.")

    def activate_action(self, game, player):
        player.remaining_actions += 1
        player.draw_cards(3)
        cards = []
        cards.append(player.hand.pop())
        cards.append(player.hand.pop())
        cards.append(player.hand.pop())
        yield InfoRequest(game, player, _("You draw:",), cards)

        card_classes = [type(c) for c in cards]
        card_cls = (yield SelectCard(game, player,
            _("Which card do you want to trash?"),
            card_classes=card_classes))
        card = [c for c in cards if isinstance(c, card_cls)][0]
        cards.remove(card)
        game.trash_pile.append(card)
        for info_player in game.participants:
            yield InfoRequest(game, info_player, _("%s trashes:", (player.name, )), [card])

        card_classes = [type(c) for c in cards]
        card_cls = (yield SelectCard(game, player,
            _("Which card do you want to discard?"),
            card_classes=card_classes))
        card = [c for c in cards if isinstance(c, card_cls)][0]
        cards.remove(card)
        player.discard_pile.append(card)
        for info_player in game.participants:
            yield InfoRequest(game, info_player, _("%s discards:", (player.name, )), [card])

        card_classes = [type(c) for c in cards]
        card_cls = (yield SelectCard(game, player,
            _("Which card do you want to put back on deck?"),
            card_classes=card_classes))
        card = [c for c in cards if isinstance(c, card_cls)][0]
        cards.remove(card)
        card.backondeck()

class MerchantShip(ActionCard, DurationCard):
    name = _("Merchant Ship")
    edition = Seaside
    cost = 5
    desc = _("Now and at the start of next turn: +2 Money")

    def activate_action(self, game, player):
        player.virtual_money += 2
        self.durationaction_activated = True

    def duration_action(self, game, player):
        player.virtual_money += 2

class Navigator(ActionCard):
    name = _("Navigator")
    edition = Seaside
    cost = 4
    desc = _("+2 Money. Look at the top 5 Cards of your deck. Either discard all of them, or put them back on top of your deck in any order.")

    def activate_action(self, game, player):
        player.virtual_money += 2
        player.draw_cards(5)
        cards = []
        cards.append(player.hand.pop())
        cards.append(player.hand.pop())
        cards.append(player.hand.pop())
        cards.append(player.hand.pop())
        cards.append(player.hand.pop())
        yield InfoRequest(game, info_player, _("You draw:",), cards)
        actions = [("discard",    _("discard all 5 cards")),
                   ("backondeck", _("put the cards back in your specified order"))]

        answer = yield Question(game, player, _("What do you want to do?"), actions)
        if answer == "discard":
            player.discard_pile.extend(cards)
        else:
            while cards:
                card_classes = [type(c) for c in cards]
                card_cls = (yield SelectCard(game, player,
                    _("Which card do you want to put back?"),
                    card_classes=card_classes))
                card = [c for c in cards if isinstance(c, card_cls)][0]
                cards.remove(card)
                player.discard_pile.append(card)


class PirateShip(AttackCard):
    name = _("Pirate Ship")
    edition = Seaside
    cost = 4
    desc = _("Choose one: Each Player reveals the top 2 cards of his deck, trashes a revealed Treasure that you choose, discards the rest, and if anyone trashed a Treasure you take a Coin token; or +1 Money per Coin token you have taken with pirate Ships this game.")

    def activate_action(self, game, player):
        actions = [("cardstrashtreasure", _("Others reveal 2 cards and trash a Treasure you choose")),
                   ("moneyfortokens",     _("+1 Money per Coin token"))]

        answer = yield Question(game, player, _("What do you want to do?"),
                                actions)
        if answer == "cardstrashtreasure":
            for other_player in game.following_players(player):
                try:
                    handle_defense(self, game, other_player)
                except Defended:
                    continue
                other_player.draw_cards(2)
                cards = []
                cards.append(other_player.hand.pop())
                cards.append(other_player.hand.pop())
                for info_player in game.participants:
                    yield InfoRequest(game, info_player, _("%s reveals the top card of his deck:",
                            (other_player.name, )), cards)
                trashed = False
                for card in cards:
                    if isinstance(card, TreasureCard) and not trashed:
                        if (yield YesNoQuestion(game, player,
                            _("Do you want to trash %(name)s's card '%(cardname)s'?",
                            {"cardname": card.name, "name": other_player.name}))):
                            for info_player in game.participants:
                                yield InfoRequest(game, info_player, _("%s trashes %s Treasure:",
                                        (player.name, other_player.name, )), cards)
                            card.trash(game, other_player)
                            trashed = True
                        else:
                            other_player.discard_pile.append(card)
        else:
            player.virtual_money += player.pirateshipcointokens


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

class PearlDiver(ActionCard):
    name = _("Pearl Diver")
    edition = Seaside
    cost = 2
    desc = _("+1 Card, +1 Action. Look at the bottom card of your deck. You may put it on top.")

    def activate_action(self, game, player):
        player.remaining_actions += 1
        player.draw_cards(1)
        card = player.deck.pop(0)
        if (yield YesNoQuestion(game, player,
            _("Do you want to put your '%(cardname)' on top of your deck?",
            {"cardname": card.name}))):
            player.deck.append(card)
        else:
            player.deck.insert(0,card)

class Salvager(ActionCard):
    name = _("Salvager")
    edition = Seaside
    cost = 4
    desc = _("+1 Buy. Trash a Card from your hand. +Money equal to its costs.")

    def activate_action(self, game, player):
        player.remaining_deals += 1
        if player.hand:
            cards = yield SelectHandCards(game, player, count_lower=1, count_upper=1,
                    msg=_("Which card do you want to trash?"))
        else:
            return
        # trash cards
        for card in cards:
            player.virtual_money += card.cost
            card.trash(game, player)
        for info_player in game.following_participants(player):
            yield InfoRequest(game, info_player,
                   _("%s trashes these cards:", (player.name, )), cards)

class SeaHag(AttackCard):
    name = _("Sea Hag")
    edition = Seaside
    cost = 4
    desc = _("Each other player discards the top card of his deck, then gains a Curse card, putting it on top of his deck.")

    def activate_action(self, game, player):
        curse_cards = game.supply["Curse"]
        for other_player in game.following_players(player):
            try:
                handle_defense(self, game, other_player)
            except Defended:
                continue
            other_player.draw_cards(1)
            card = other_player.hand.pop()
            for info_player in game.participants:
                yield InfoRequest(game, info_player, _("%s discards the top card of his deck:",
                        (other_player.name, )), [card])
            other_player.discard_pile.append(card)
            if curse_cards:
                other_player.deck.append(curse_cards.pop())
                yield InfoRequest(game, other_player,
                        _("%s curses you. You gain a curse card.", (player.name, )), [])
                for val in game.check_empty_pile("Curse"):
                    yield val


class Smugglers(ActionCard):
    name = _("Smugglers")
    edition = Seaside
    cost = 3
    desc = _("Gain a copy of a Card costing up to 6 that the player to your rigth gained on his last turn.")

    def activate_action(self, game, player):
        if len(player.right(game).cards_gained) > 1:
            card_classes = [c for c in player.right(game).cards_gained
                            if c.cost <= 6 and
                            game.supply.get(c.__name__)]
            card_cls = yield SelectCard(game, player, card_classes=card_classes,
                msg=_("Select a treasure card that you want to have."), show_supply_count=True)
        else:
            card_cls = type(player.right(game).cards_gained[0])
            new_card = game.supply[card_cls.__name__].pop()
            player.discard_pile.append(new_card)

            for other_player in game.following_participants(player):
                yield InfoRequest(game, info_player,
                        _("%s gains:", (player.name, )), [new_card])
            for val in game.check_empty_pile(card_cls.__name__):
                yield val



class Caravan(ActionCard, DurationCard):
    name = _("Caravan")
    edition = Seaside
    cost = 4
    desc = _("+1 Card, +1 Action. At the start of your next turn, +1 Card.")

    def activate_action(self, game, player):
        player.remaining_actions += 1
        player.draw_cards(1)
        self.durationaction_activated = True

    def duration_action(self, game, player):
        player.draw_cards(1)

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
            copper_cards = [c for c in other_player.hand if isinstance(c, Copper)]
            if copper_cards:
                cards = yield SelectHandCards(game, other_player, count_lower=1, count_upper=1,
                        msg=_("%s played Cutpurse. Which Copper do you want to discard?", (player.name, )), cls=Copper)
                for card in cards:
                    card.discard(other_player)
                    for info_player in game.following_participants(other_player):
                        yield InfoRequest(game, info_player,
                            _("%s discards these cards:", (other_player.name, )), cards)
            else:
                for info_player in game.following_participants(player):
                    yield InfoRequest(game, info_player, _("%s reveals his hand:",
                            (other_player.name, )), other_player.hand[:])


class Embargo(ActionCard):
    name = _("Embargo")
    edition = Seaside
    implemented = False #FIXME not implemented completely
    cost = 2
    desc = _("+2 Money. Trash this card. Put an Embargo token on top of a Supply pile. When a player buys a card, he gains a Curse card per Embargo token on that pile.")

    def activate_action(self, game, player):
        player.virtual_money += 2
        pass #FIXME

class Lighthouse(ActionCard, DurationCard):
    name = _("Lighthouse")
    edition = Seaside
    cost = 2
    desc = _("+1 Action. Now and at the start of your next turn: +1 Money. While this is in play, when another player plays an Attack card it doesn't affect you.")

    def defend_action(self, game, player, card):
        # Lighthouse always defends
        # FIXME: Lighthouse does not only defend while on hand, but when on play (duration_cards, aux_cards), too
        raise Defended

    def activate_action(self, game, player):
        player.remaining_actions += 1
        player.virtual_money += 1
        self.durationaction_activated = True

    def duration_action(self, game, player):
        player.virtual_money += 1

class GhostShip(AttackCard):
    name = _("Ghost Ship")
    edition = Seaside
    cost = 5
    desc = _("+2 Cards. Each other player with 4 or more cards in hand puts cards from his hand on top of his deck until he has 3 cards in his hand.")

    def activate_action(self, game, player):
        player.draw_cards(2)
        for other_player in game.following_players(player):
            try:
                handle_defense(self, game, other_player)
            except Defended:
                continue
            if len(other_player.hand) < 4:
                continue
            count = len(other_player.hand) - 3
            cards = yield SelectHandCards(game, other_player, count_lower=count, count_upper=count,
                    msg=_("%s played Ghost Ship. Which cards do you want to put on the top of your deck?", (player.name, )))
            for card in cards:
                card.backondeck(game, other_player)


class Haven(ActionCard, DurationCard):
    name = _("Haven")
    edition = Seaside
    implemented = False #FIXME not implemented completely
    cost = 2
    desc = _("+1 Card, + 1 Action. Set aside a card from your hand face down. At the start of your next turn, put it into your hand.")

    def activate_action(self, game, player):
        player.remaining_actions += 1
        player.draw_cards(1)
        pass #FIXME

class Explorer(ActionCard):
    name = _("Explorer")
    edition = Seaside
    cost = 5
    desc = _("You may reveal a Province card from your hand. If you do, gain a Gold card, putting it into your hand. Otherwise, gain a Silver card, putting it into your hand.")

    def activate_action(self, game, player):
        province_cards = [c for c in player.hand if isinstance(c, Province)]
        if province_cards:
            new_card = game.supply["Gold"].pop()
            player.hand.append(new_card)
            for info_player in game.following_participants(player):
                yield InfoRequest(game, info_player,
                        _("%s gains:", (player.name, )), [new_card])
            for val in game.check_empty_pile("Gold"):
                yield val
        else:
            new_card = game.supply["Silver"].pop()
            player.hand.append(new_card)
            for info_player in game.following_participants(player):
                yield InfoRequest(game, info_player,
                        _("%s gains:", (player.name, )), [new_card])
            for val in game.check_empty_pile("Silver"):
                yield val


class FishingVillage(ActionCard, DurationCard):
    name = _("Fishing Village")
    edition = Seaside
    cost = 3
    desc = _("+2 Actions, +1 Money. At the start of your next turn: +1 Action, +1 Money.")

    def activate_action(self, game, player):
        player.remaining_actions += 2
        player.virtual_money += 1
        self.durationaction_activated = True

    def duration_action(self, game, player):
        player.remaining_actions += 1
        player.virtual_money += 1

class Warehouse(ActionCard):
    name = _("Warehouse")
    edition = Seaside
    cost = 3
    desc = _("+3 Cards, +1 Actions. Discard 3 Cards.")

    def activate_action(self, game, player):
        player.remaining_actions += 1
        player.draw_cards(3)
        cards = yield SelectHandCards(game, player, count_lower=3, count_upper=3,
                msg=_("Which 3 cards do you want to discard?"))
        # discard cards
        if cards is not None:
            for card in cards:
                card.discard(player)
            for info_player in game.following_participants(player):
                yield InfoRequest(game, info_player,
                       _("%s discards these cards:", (player.name, )), cards)

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
    desc = _("Set aside this and another card from your hand. Return them to"
             " your deck at the end of the game.")

    def activate_action(self, game, player):
        pass #FIXME

class Ambassador(AttackCard):
    name = _("Ambassador")
    edition = Seaside
    implemented = False #FIXME not implemented completely
    cost = 3
    desc = _("Reveal a card from your hand. Return 2 copies of it from your hand to the Supply. Then each other player gains a copy of it.")

    def activate_action(self, game, player):
        if player.hand:
#            card_classes = [type(c) for c in player.hand]
#            card_classes_count = {}
#            for card_class in card_classes:
#                same_cards = [c for c in player.hand if isinstance(c, TreasureMap)]
#                if len(treasure_map_cards) >= 1: # only need one other treasure map in hand, because the other has already been played

            cards = yield SelectHandCards(game, player, count_lower=1, count_upper=1,
                    msg=_("Which card do you want to Ambassador?"))
            card = cards[0]
            samecards = [c for c in player.hand if isinstance(c, type(card))]
            if len(samecards) >=2:
                for info_player in game.participants:
                    yield InfoRequest(game, info_player, _("%s reveals:",
                            (player.name, )), [samecards[0]])
                for i in range(2):
                    player.hand.remove(samecards[i])
                    game.supply(type(samecards[i])).append(samecards[i])
                curse_cards = game.supply["Curse"]
                for other_player in game.following_players(player):
                    if curse_cards:
                        try:
                            handle_defense(self, game, other_player)
                        except Defended:
                            continue
                        other_player.discard_pile.append(game.supply(type(card)).pop(0))
                        yield InfoRequest(game, other_player,
                                _("%s curses you. You gain a curse card.", (player.name, )), [])
                        for val in game.check_empty_pile(type(card)):
                            yield val


class Tactician(ActionCard, DurationCard):
    name = _("Tactician")
    edition = Seaside
    cost = 5
    desc = _("Discard your hand. If you discarded any cards this way, then at the start of your next turn, +5 Cards, +1 Buy, and +1 Action")

    def activate_action(self, game, player):
        original_hand = player.hand[:]
        for card in original_hand:
            card.discard(player)
        for info_player in game.following_participants(player):
            yield InfoRequest(
                game, info_player,
                _("%s discards this hand:",
                (player.name, )), original_hand)
        if original_hand:
            self.durationaction_activated = True

    def duration_action(self, game, player):
        player.remaining_actions += 1
        player.remaining_deals += 1
        player.draw_cards(5)

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
    cost = 5
    desc = _("Now and at the start of your next turn: +2 Cards, +1 Buy.")

    def activate_action(self, game, player):
        player.remaining_deals += 1
        player.draw_cards(2)
        self.durationaction_activated = True

    def duration_action(self, game, player):
        player.remaining_deals += 1
        player.draw_cards(2)

class TreasureMap(ActionCard):
    name = _("Treasure Map")
    edition = Seaside
    cost = 4
    trash_after_playing = True
    desc = _("Trash this and another copy of Treasure map from your hand. If you do trash two Treasure maps, gain 4 Gold cards, putting them on top of your deck.")

    def activate_action(self, game, player):
        treasure_map_cards = [c for c in player.hand if isinstance(c, TreasureMap)]
        if len(treasure_map_cards) >= 1: # only need one other treasure map in hand, because the other has already been played
            card = treasure_map_cards[0]
            card.trash(game, player)
            for info_player in game.participants:
                yield InfoRequest(game, info_player,
                            _("%s trashes:", (player.name, )), [card])
            new_cards = []
            for i in range(0, 4):
                new_cards.append(game.supply["Gold"].pop())
                for val in game.check_empty_pile("Gold"):
                    yield val
            player.deck.extend(new_cards)
            for info_player in game.participants:
                yield InfoRequest(game, info_player,
                        _("%s gains on top of his deck:", (player.name, )), new_cards)


from domination.cards.base import \
    Cellar, CouncilRoom, Festival, Mine, Adventurer, Spy, Village,\
    Chancellor, Festival, Militia, Workshop, Library, Market, Moneylender,\
    Witch

card_sets = [
    CardSet(u"High Seas [S]",
        [Bazaar, Caravan, Embargo, Explorer, Haven, Island, Lookout, PirateShip,
            Smugglers, Wharf]),
    CardSet(u"Buried Treasure [S]",
        [Ambassador, Cutpurse, FishingVillage, Lighthouse, Outpost, PearlDiver,
            Tactician, TreasureMap, Warehouse, Wharf]),
    CardSet(u"Shipwrecks [S]",
        [GhostShip, MerchantShip, NativeVillage, Navigator, PearlDiver, Salvager,
            SeaHag, Smugglers, Treasury, Warehouse]),
    CardSet(u"Reach for Tomorrow [S&D]",
        [Adventurer, Cellar, CouncilRoom, Cutpurse, GhostShip, Lookout, SeaHag,
            Spy, TreasureMap, Village]),
    CardSet(u"Repetition [S&D]",
        [Caravan, Chancellor, Explorer, Festival, Militia, Outpost, PearlDiver,
            PirateShip, Treasury, Workshop]),
    CardSet(u"Give and Take [S&D]",
        [Ambassador, FishingVillage, Haven, Island, Library, Market, Moneylender,
            Salvager, Smugglers, Witch]),
]
