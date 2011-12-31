from domination.cards import TreasureCard, VictoryCard, CurseCard, ActionCard, \
     AttackCard, ReactionCard, CardSet, Hinterlands
from domination.cards.base import Duchy, Copper, Silver, Gold, Province, Curse
from domination.cards.prosperity import Platinum
from domination.gameengine import InfoRequest, SelectCard, SelectHandCards, \
     YesNoQuestion, Question, Defended, SelectActionCard
from domination.tools import _
from domination.macros.__macros__ import handle_defense, generator_forward, fetch_card_from_supply


class BorderVillage(ActionCard):
    name = _("Border Village")
    edition = Hinterlands
    cost = 6
    desc = _("+1 Card +2 Actions. | When you gain this, gain a card costing less than this.")

    def activate_action(self, game, player):
        player.remaining_actions += 2
        player.draw_cards(1)

    @classmethod
    def on_gain_card(cls, game, player, card):
        if not isinstance(card, BorderVillage):
            return

        card_classes = [c for c in game.card_classes.itervalues()
                        if c.cost < cls.cost and
                        game.supply.get(c.__name__)]
        card_cls = yield SelectCard(game, player, card_classes=card_classes,
            msg=_("Select a card that you want to have."), show_supply_count=True)
        with fetch_card_from_supply(game, card_cls) as new_card:
            player.discard_pile.append(new_card)
            for info_player in game.following_participants(player):
                yield InfoRequest(game, info_player,
                        _("%s gains:", (player.name, )), [new_card])

class Cache(TreasureCard):
    name = _("Cache")
    edition = Hinterlands
    implemented = False #FIXME Second half of the action should be triggered when card is gained.
    cost = 5
    worth = 3
    desc = _("3 Money. | When you gain this, gain two Coppers.")

    def gainedthis(self, game, player):
        copper_cards = game.supply["Copper"]
        if copper_cards:
            player.discard_pile.append(copper_cards.pop())
            new_card = copper_cards.pop()
            for info_player in game.following_participants(player):
                yield InfoRequest(game, info_player,
                        _("%s gains:", (player.name, )), [new_card])
            for val in game.check_empty_pile("Copper"):
                yield val

class Cartographer(ActionCard):
    name = _("Cartographer")
    edition = Hinterlands
    implemented = False
    cost = 5
    desc = _("+1 Card +1 Action. Look at the top 4 Cards of your deck "
            "Discard any number of them. Put the rest back on top in any order.")

    def activate_action(self, game, player):
        player.remaining_actions += 1
        player.draw_cards(1)

        player.draw_cards(4)
        drawn, player.hand = player.hand[-4:], player.hand[:-4]

        card_classes = [type(c) for c in drawn]
        # FIXME any numer part still missing
        card_cls = (yield SelectCard(game, player,
            _("Which card do you want to discard?"),
            card_classes=card_classes))
        card = [c for c in drawn if isinstance(c, card_cls)][0]
        drawn.remove(card)
        player.discard_pile.append(card)

        while drawn:
            card_classes = [type(c) for c in drawn]
            card_cls = (yield SelectCard(game, player,
                _("Which card do you want to put back?"),
                card_classes=card_classes))
            card = [c for c in drawn if isinstance(c, card_cls)][0]
            drawn.remove(card)
            player.discard_pile.append(card)

class Crossroads(ActionCard):
    name = _("Crossroads")
    edition = Hinterlands
    cost = 2
    desc = _("Reveal your hand. +1 Card per Victory card revealed. "
            "If this is the first time you played a Crossroads this turn, +3 Actions.")

    def activate_action(self, game, player):
        for info_player in game.following_participants(player):
            yield InfoRequest(game, info_player, _("%s reveals his hand:",
                    (player.name, )), player.hand[:])
        player.draw_cards(len([card for card in player.hand if isinstance(card, VictoryCard) ]))
        if len([card for card in player.aux_cards if isinstance(card, Crossroads)]) == 1:
            player.remaining_actions += 3

class Develop(ActionCard):
    name = _("Develop")
    edition = Hinterlands
    cost = 3
    desc = _("Trash a card from your hand. "
            "Gain a card costing exactly 1 Money more than it "
            "and a card costing exactly 1 Money less than it, "
            "in either order, putting them on top of your deck.")

    #FIXME in EITHER order
    def activate_action(self, game, player):
        cards = yield SelectHandCards(game, player,
                    count_lower=1, count_upper=1,
                    msg=_("Select a card you want to trash for a better and a worse card."))
        new_cards = []
        if cards:
            card = cards[0]
            card_classes = [c for c in game.card_classes.itervalues()
                            if c.cost == card.cost + 1 and
                            game.supply.get(c.__name__)]
            if card_classes:
                card_cls = yield SelectCard(game, player, card_classes=card_classes,
                    msg=_("Select a card that you want to have."), show_supply_count=True)
                new_cards.append(game.supply[card_cls.__name__].pop())
                for val in game.check_empty_pile(card_cls.__name__):
                    yield val
            card_classes = [c for c in game.card_classes.itervalues()
                            if c.cost == card.cost - 1 and
                            game.supply.get(c.__name__)]
            if card_classes:
                card_cls = yield SelectCard(game, player, card_classes=card_classes,
                    msg=_("Select a card that you want to have."), show_supply_count=True)
                new_cards.append(game.supply[card_cls.__name__].pop())
                for val in game.check_empty_pile(card_cls.__name__):
                    yield val
            card.trash(game, player)
            player.deck.extend(new_cards)
            for info_player in game.following_participants(player):
                yield InfoRequest(game, info_player,
                        _("%s trashes:", (player.name, )), [card])
                yield InfoRequest(game, info_player,
                        _("%s gains:", (player.name, )), new_cards)

class Duchess(ActionCard):
    name = _("Duchess")
    edition = Hinterlands
    implemented = False #FIXME Second half of the action should be triggered when card is gained.
    cost = 2
    desc = _("+2 Money. Each player (including you) looks at the top card of his deck, "
            "and discards it or puts it back. | "
            "In games using this, when you gain a Duchy, you may gain a Duchess.")

    def activate_action(self, game, player):
        player.virtual_money += 2

        for any_player in game.all_players(player):
            any_player.draw_cards(1)
            drawn, any_player.hand = any_player.hand[-1:], any_player.hand[:-1]
            if (yield YesNoQuestion(game, any_player, _("Do you want to keep this %s?"%drawn[0].name, {}))):
                any_player.hand.extend(drawn)
            else:
                any_player.discard_pile.extend(drawn)

class Embassy(ActionCard):
    name = _("Embassy")
    edition = Hinterlands
    implemented = False #FIXME Second half of the action should be triggered when card is gained.
    cost = 5
    desc = _("+5 Cards. Discard 3 Cards. | When you gain this, each other player gains a Silver.")

    def activate_action(self, game, player):
        player.draw_cards(5)
        cards = yield SelectHandCards(game, player, count_lower=3, count_upper=3,
                msg=_("Which cards do you want to discard?"))
        #FIXME make sure player has enough cards to do that
        # discard cards
        if cards is not None:
            for card in cards:
                card.discard(player)
            player.draw_cards(len(cards))
            for info_player in game.participants:
                if info_player is not player:
                    yield InfoRequest(game, info_player,
                            _("%s discards these cards:", (player.name, )), cards)

    def gainedthis(self, game, player):
        for other_player in game.following_players(player):
            silver_cards = game.supply["Silver"]
            if silver_cards:
                other_player.discard_pile.append(silver_cards.pop())
                new_card = silver_cards.pop()
                for info_player in game.following_participants(other_player):
                    yield InfoRequest(game, info_player,
                            _("%s gains:", (other_player.name, )), [new_card])
                for val in game.check_empty_pile("Silver"):
                    yield val

class Farmland(VictoryCard):
    name = _("Farmland")
    edition = Hinterlands
    implemented = False #FIXME Second half of the action should be triggered when card is gained.
    cost = 6
    points = 2
    desc = _("2 (VICTORY) | When you buy this, trash a card from your hand. "
            "Gain a card costing exactly 2 Money more than the trashed card.")

    def boughtthis(self, game, player):
        cards = yield SelectHandCards(game, player,
                    count_lower=0, count_upper=1,
                    msg=_("Select a card you want to convert to a 2 Money more expensive Card."))
        if cards:
            card = cards[0]
            card_classes = [c for c in game.card_classes.itervalues()
                            if c.cost == card.cost + 2 and
                            game.supply.get(c.__name__)]
            card_cls = yield SelectCard(game, player, card_classes=card_classes,
                msg=_("Select a treasure card that you want to have."), show_supply_count=True)
            card.trash(game, player)
            new_card = game.supply[card_cls.__name__].pop()
            player.hand.append(new_card)
            for info_player in game.following_participants(player):
                yield InfoRequest(game, info_player,
                        _("%s trashes:", (player.name, )), [card])
                yield InfoRequest(game, info_player,
                        _("%s gains:", (player.name, )), [new_card])
            for val in game.check_empty_pile(card_cls.__name__):
                yield val

class FoolsGold(TreasureCard, ReactionCard):
    name = _("Fool's Gold")
    edition = Hinterlands
    implemented = False #FIXME Second half of the action should be triggered when card is gained.
    cost = 2
    desc = _("If this is the first time you played a Fool's Gold this turn, this is worth 1 Money, "
            "otherwise it's worth 4. | When another player gains a Province, you may trash this from your hand. "
            "If you do, gain a Gold, putting it on top of your deck")

    def get_worth(self, player):
        if len([card for card in player.aux_cards if isinstance(card, FoolsGold)]) == 0:
            return 1
        else:
            return 4

class Haggler(ActionCard):
    name = _("Haggler")
    edition = Hinterlands
    implemented = False #FIXME Second half of the action should be triggered when card is gained.
    cost = 5
    desc = _("+2 Money. | While this is in play, when you buy a card, gain a card costing less than it that is not a Victory card.")

    def activate_action(self, game, player):
        player.virtual_money += 2

class Highway(ActionCard):
    name = _("Highway")
    edition = Hinterlands
    implemented = False #FIXME Second half of the action should be triggered when card is gained.
    cost = 5
    desc = _("+1 Card +1 Action. | While this is in play, cards cost 1 Money less, but not less than 0 Money.")

    def activate_action(self, game, player):
        player.remaining_actions += 1
        player.draw_cards(1)

class IllGottenGains(TreasureCard):
    name = _("Ill-Gotten Gains")
    edition = Hinterlands
    implemented = False #FIXME Second half of the action should be triggered when card is gained.
    cost = 5
    worth = 1
    desc = _("When you play this, you may gain a Copper, putting it into your hand. | "
            "When you gain this, each other player gains a Curse.")

    def activate_action(self, game, player):
        if (yield YesNoQuestion(game, player, _("Do you want to a Copper?", {}))):
            copper_cards = game.supply["Copper"]
            if copper_cards:
                player.discard_pile.append(copper_cards.pop())
                new_card = copper_cards.pop()
                for info_player in game.following_participants(player):
                    yield InfoRequest(game, info_player,
                            _("%s gains:", (player.name, )), [new_card])
                for val in game.check_empty_pile("Copper"):
                    yield val

    def gainedthis(self, game, player):
        curse_cards = game.supply["Curse"]
        for other_player in game.following_players(player):
            try:
                handle_defense(self, game, other_player)
            except Defended:
                continue
            if curse_cards:
                other_player.discard_pile.append(curse_cards.pop())
                yield InfoRequest(game, other_player,
                        _("%s curses you. You gain a curse card.", (player.name, )), [])
                for val in game.check_empty_pile("Curse"):
                    yield val

class Inn(ActionCard):
    name = _("Inn")
    edition = Hinterlands
    implemented = False #FIXME Second half of the action should be triggered when card is gained.
    cost = 5
    desc = _("+2 Cards +2 Actions. Discard 2 Cards. | When you gain this, look through your "
            "discard pile (including this), reveal any number of Action cards from it, "
            "and shuffle them into your deck.")

    def activate_action(self, game, player):
        player.remaining_actions += 2
        player.draw_cards(2)
        cards = yield SelectHandCards(game, player, count_lower=2, count_upper=2,
                msg=_("Which cards do you want to discard?"))
        #FIXME make sure player has enough cards to do that
        if cards is not None:
            for card in cards:
                card.discard(player)
            player.draw_cards(len(cards))
            for info_player in game.participants:
                if info_player is not player:
                    yield InfoRequest(game, info_player,
                            _("%s discards these cards:", (player.name, )), cards)

class JackOfAllTrades(ActionCard):
    name = _("Jack of all Trades")
    edition = Hinterlands
    cost = 4
    desc = _("Gain a Silver. Look at the top card of your deck: discard it or put it back. "
            "Draw until you have 5 cards in hand. "
            "You may trash a card from your hand that is not a Treasure.")

    def activate_action(self, game, player):
        with fetch_card_from_supply(game, Silver) as new_card:
            player.discard_pile.append(new_card)
            for info_player in game.following_participants(player):
                yield InfoRequest(game, info_player,
                        _("%s gains:", (player.name, )), [new_card])
        player.draw_cards(1)
        drawn, player.hand = player.hand[-1:], player.hand[:-1]
        if (yield YesNoQuestion(game, player, _("Do you want to keep the card '%s' on your hand?", (drawn[0].name,) ))):
            player.hand.extend(drawn)
        else:
            player.discard_pile.extend(drawn)

        while len(player.hand) < 5:
            if player.draw_cards(1) is None:
                break

        #FIXME only cards that are no treasure
        cards = yield SelectHandCards(game, player,
                    count_lower=0, count_upper=1, not_selectable=[c for c in player.hand if isinstance(c, TreasureCard)],
                    msg=_("Select a card you want to trash."))
        if cards:
            card = cards[0]
            card.trash(game, player)

class Mandarin(ActionCard):
    name = _("Mandarin")
    edition = Hinterlands
    implemented = False #FIXME Second half of the action should be triggered when card is gained.
    cost = 5
    desc = _("+3 Money. Put a card from your hand on top of your deck. "
            "| When you gain this, put all Treasures you have in play on top of your deck "
            "in any order.")

    def activate_action(self, game, player):
        player.virtual_money += 3
        cards = yield SelectHandCards(game, player,
                count_lower=1, count_upper=1,
                msg=_("Which card do you want to put on top of your deck?"))
        if cards:
            card = cards[0]
            player.deck.append(card)
            player.hand.remove(card)

    def gainedthis(self, game, player):
        cards = [card for card in player.aux_cards if isinstance(card, TreasureCard)]
        for card in cards:
            player.aux_cards.remove(card)
        while cards:
            card_classes = [type(c) for c in cards]
            card_cls = (yield SelectCard(game, player,
                _("Which card do you want to put on top next?"),
                card_classes=card_classes))
            card = [c for c in cards if isinstance(c, card_cls)][0]
            cards.remove(card)
            player.deck.append(card)

class Margrave(AttackCard):
    name = _("Margrave")
    edition = Hinterlands
    cost = 5
    desc = _("+3 Cards +1 Buy. Each other player draws a Card, then discards down to 3 cards in hand.")

    def activate_action(self, game, player):
        player.draw_cards(3)
        player.remaining_deals += 1
        for other_player in game.following_players(player):
            try:
                handle_defense(self, game, other_player)
            except Defended:
                continue
            other_player.draw_cards(1)
            if len(other_player.hand) < 4:
                continue
            count = len(other_player.hand) - 3
            if count <= 0:
                continue
            cards = yield SelectHandCards(game, other_player, count_lower=count, count_upper=count,
                    msg=_("%s played Margrave, you need to discard your hand down to three cards. Which cards do you want to discard?", (player.name, )))
            for card in cards:
                card.discard(other_player)
            for info_player in game.participants:
                if info_player is not other_player:
                    # TODO: info players may only see one of the discarded cards
                    yield InfoRequest(game, info_player,
                            _("%s discards these cards:", (other_player.name, )), cards)

class NobleBrigand(AttackCard):
    name = _("Noble Brigand")
    edition = Hinterlands
    implemented = False # XXX doesnt work at all
    cost = 4
    desc = _("+1 Money. When you buy this or play it, each other player reveals the top 2 cards of his deck,"
            "trashes a revealed Silver or Gold you choose, and discards the rest. "
            "If he didn't reveal a Treasure, he gains a Copper. "
            "You gain the trashed cards.")

    def activate_action(self, game, player):
        player.virtual_money += 1
        self.action(game, player)

    def boughtthis(self, game, player):
        self.action(game, player)

    def action(self, game, player):
        for other_player in game.following_players(player):
            other_player.draw_cards(2)
            drawn, other_player.hand = other_player.hand[-2:], other_player.hand[:-2]
            for info_player in game.participants:
                yield InfoRequest(game, info_player, _("%s reveals the top two cards of his deck:",
                        (other_player.name, )), drawn)

            silver_gold_platinum_cards = [c for c in drawn if isinstance(c, Silver) or isinstance(c, Gold) or isinstance(c, Platinum)]
            if silver_gold_platinum_cards:
                for card in silver_gold_platinum_cards:
                    drawn.remove(card)
                    other_player.discard_pile.append(card)
                for card in drawn:
                    if (yield YesNoQuestion(game, player,
                        _("Do you want to trash %(name)s's card '%(cardname)s'?",
                        {"cardname": card.name, "name": other_player.name}))):
                        player.discard_pile.append(card)
                        for info_player in game.following_participants(player):
                            yield InfoRequest(game, info_player,
                                    _("%(playername)s trashes %(player2name)s's card:",
                                    {"playername": player.name, "player2name": other_player.name}),
                                    [card])
                    else:
                        other_player.discard_pile.append(card)
            else:
                copper_cards = game.supply["Copper"]
                if copper_cards:
                    other_player.discard_pile.append(copper_cards.pop())
                    new_card = copper_cards.pop()
                    for info_player in game.following_participants(other_player):
                        yield InfoRequest(game, info_player,
                                _("%s gains:", (other_player.name, )), [new_card])
                    for val in game.check_empty_pile("Copper"):
                        yield val


class NomadCamp(ActionCard):
    name = _("Nomad Camp")
    edition = Hinterlands
    implemented = False #FIXME Second half of the action should be triggered when card is gained.
    cost = 4
    desc = _("+1 Buy +2 Money. | When you gain this, put it on top of your deck.")

    def activate_action(self, game, player):
        player.remaining_deals += 1
        player.virtual_money += 2

class Oasis(ActionCard):
    name = _("Oasis")
    edition = Hinterlands
    cost = 3
    desc = _("+1 Card +1 Action +1 Money. Discard a card.")

    def activate_action(self, game, player):
        player.virtual_money += 1
        player.draw_cards(1)
        player.remaining_actions += 1
        cards = yield SelectHandCards(game, player, count_lower=1, count_upper=1,
                msg=_("Which cards do you want to discard?"))
        #FIXME make sure player has enough cards to do that
        # discard cards
        if cards is not None:
            for card in cards:
                card.discard(player)
            player.draw_cards(len(cards))
            for info_player in game.participants:
                if info_player is not player:
                    yield InfoRequest(game, info_player,
                            _("%s discards these cards:", (player.name, )), cards)

class Oracle(AttackCard):
    name = _("Oracle")
    edition = Hinterlands
    cost = 3
    desc = _("Each player (including you) reveals the top 2 cards of his deck, "
            "and you choose one: Either he discards them, or he puts them back on top "
            "in an order he chooses. +2 Cards")

    def activate_action(self, game, player):
        for any_player in game.all_players(player):
            any_player.draw_cards(2)
            drawn, any_player.hand = any_player.hand[-2:], any_player.hand[:-2]
            for info_player in game.participants:
                yield InfoRequest(game, info_player, _("%s reveals:", (any_player.name, )), drawn)

            actions = [("discard",   _("Discard the cards")),
                       ("backontop", _("Put the cards back on top of your deck"))]

            answer = yield Question(game, any_player, _("What do you want to do?"),
                                    actions)

            for info_player in game.following_participants(any_player):
                yield InfoRequest(game, info_player,
                        _("%(player)s chooses '%(action)s'", {"player": any_player.name, "action": _(dict(actions)[answer])}), [])

            if answer=="discard":
                any_player.discard_pile.extend(drawn)
            else:
                any_player.deck.extend(drawn)


        player.draw_cards(2)

class Scheme(ActionCard):
    name = _("Scheme")
    edition = Hinterlands
    implemented = False
    cost = 3
    desc = _("+1 Card +1 Action. At the start of Clean-up this turn, "
            "you may choose an Action Card you have in play. "
            "If you discard it from play this turn, put it on your deck.")

    def activate_action(self, game, player):
        player.remaining_actions += 1
        player.draw_cards(1)

class SilkRoad(VictoryCard):
    name = _("Silk Road")
    edition = Hinterlands
    cost = 4
    desc = _("Worth 1 (VICTORY) for every 4 Victory cards in your deck (rounded down)")

    def get_points(self, game, player):
        assert not player.hand and not player.discard_pile
        return sum(isinstance(card, VictoryCard) for card in player.deck) / 4

class SpiceMerchant(ActionCard):
    name = _("Spice Merchant")
    edition = Hinterlands
    cost = 4
    desc = _("You may trash a Treasure from your hand. If you do, choose one: "
            "+2 Cards and +1 Action; or +2 Money and +1 Buy.")

    def activate_action(self, game, player):
        cards = yield SelectHandCards(game, player, cls=TreasureCard,
                    count_lower=0, count_upper=1,
                    msg=_("Select a treasure card you want to trash."))
        if cards:
            card = cards[0]
            card.trash(game, player)
            for info_player in game.following_participants(player):
                yield InfoRequest(game, info_player,
                        _("%s trashes:", (player.name, )), [card])
            actions = [("cards_action",   _("+2 Cards +1 Action")),
                       ("moneys_buy", _("+2 Money +1 Buy"))]

            answer = yield Question(game, player, _("What do you want to get?"),
                                    actions)

            for info_player in game.following_participants(player):
                yield InfoRequest(game, info_player,
                        _("%(player)s chooses '%(action)s'", {"player": player.name, "action": _(dict(actions)[answer])}), [])

            if answer == "cards_action":
                player.draw_cards(2)
                player.remaining_actions += 1
            else:
                player.virtual_money += 2
                player.remaining_deals += 1

class Stables(ActionCard):
    name = _("Stables")
    edition = Hinterlands
    cost = 5
    desc = _("You may discard a Treasure. If you do, +3 Cards and +1 Action.")

    def activate_action(self, game, player):
        cards = yield SelectHandCards(game, player, cls=TreasureCard,
                    count_lower=0, count_upper=1,
                    msg=_("Select a treasure card you want to discard."))
        if cards is not None:
            for card in cards:
                card.discard(player)
            player.draw_cards(len(cards))
            for info_player in game.participants:
                if info_player is not player:
                    yield InfoRequest(game, info_player,
                            _("%s discards these cards:", (player.name, )), cards)
            player.remaining_actions += 1
            player.draw_cards(3)

class Tunnel(VictoryCard,ReactionCard):
    name = _("Tunnel")
    edition = Hinterlands
    implemented = False #FIXME Second half of the action should be triggered when card is gained.
    cost = 3
    points = 2
    desc = _("2 (VICTORY). | When you discard this other than during a clean-up phase, "
            "you may reveal it. If you do, gain a Gold.")

class Trader(ReactionCard):
    name = _("Trader")
    edition = Hinterlands
    implemented = False #FIXME Second half of the action should be triggered when card is gained.
    cost = 4
    desc = _("Trash a card from your hand. Gain a number of Silvers equal to its cost in coins. "
            "| When you would gain a card, you may reveal this from your hand. If you do, instead, gain a silver.")

    def activate_action(self, game, player):
        cards = yield SelectHandCards(game, player, cls=TreasureCard,
                    count_lower=0, count_upper=1,
                    msg=_("Select a treasure card you want to convert to a potentially better card."))
        if cards:
            card = cards[0]
            new_cards = []
            for i in range(0, 4):
                if game.supply["Silver"]:
                    new_cards.append(game.supply["Silver"].pop())
                    for val in game.check_empty_pile("Silver"):
                        yield val
            card.trash(game, player)
            player.hand.append(new_card)
            for info_player in game.following_participants(player):
                yield InfoRequest(game, info_player,
                        _("%s trashes:", (player.name, )), [card])
                yield InfoRequest(game, info_player,
                        _("%s gains:", (player.name, )), new_cards)


from domination.cards.base import (
Cellar, Library, Moneylender, ThroneRoom, Workshop, Adventurer, Chancellor, Festival, Laboratory, Remodel)

from domination.cards.intrigue import (
Coppersmith, GreatHall, Pawn, ShantyTown, Torturer, Conspirator, Duke, Harem, Masquerade, Upgrade)

from domination.cards.seaside import (
Cutpurse, Island, Lookout, MerchantShip, Warehouse, Ambassador, Bazaar, Caravan, Embargo, Smugglers)

from domination.cards.alchemy import (
Apothecary, Apprentice, Herbalist, PhilosophersStone, Transmute, Apprentice, Familiar, Golem, University, Vineyard)

from domination.cards.prosperity import (
Bishop, Expand, Hoard, Mint, Watchtower, Bank, Monument, RoyalSeal, TradeRoute, Venture)

from domination.cards.cornucopia import (
Hamlet, HornOfPlenty, HorseTraders, Jester, Tournament, Fairgrounds, FarmingVillage, HuntingParty, Jester, Menagerie)

card_sets = [
    CardSet(_("Inroduction [H]"),
        [Cache, Crossroads, Develop, Haggler, JackOfAllTrades, Margrave, NomadCamp, Oasis, SpiceMerchant, Stables]),
    CardSet(_("Fair Trades [H]"),
        [BorderVillage, Cartographer, Develop, Duchess, Farmland, IllGottenGains, NobleBrigand, SilkRoad, Stables, Trader]),
    CardSet(_("Bargains [h]"),
        [BorderVillage, Cache, Duchess, FoolsGold, Haggler, Highway, NomadCamp, Scheme, SpiceMerchant, Trader]),
    CardSet(_("Gambits [H]"),
        [Cartographer, Crossroads, Embassy, Inn, JackOfAllTrades, Mandarin, NomadCamp, Oasis, Oracle, Tunnel]),
    CardSet(_("Highway Robbery [B&H]"),
        [Cellar, Library, Moneylender, ThroneRoom, Workshop, Highway, Inn, Margrave, NobleBrigand, Oasis]),
    CardSet(_("Adventures Abroad [B&H]"),
        [Adventurer, Chancellor, Festival, Laboratory, Remodel, Crossroads, Farmland, FoolsGold, Oracle, SpiceMerchant]),
    CardSet(_("Money for Nothing [I&H]"),
        [Coppersmith, GreatHall, Pawn, ShantyTown, Torturer, Cache, Cartographer, JackOfAllTrades, SilkRoad, Tunnel]),
    CardSet(_("The Dukes Ball [I&H]"),
        [Conspirator, Duke, Harem, Masquerade, Upgrade, Duchess, Haggler, Inn, NobleBrigand, Scheme]),
    CardSet(_("Travelers [S&H]"),
        [Cutpurse, Island, Lookout, MerchantShip, Warehouse, Cartographer, Crossroads, Farmland, SilkRoad, Stables]),
    CardSet(_("Diplomacy [S&H]"),
        [Ambassador, Bazaar, Caravan, Embargo, Smugglers, Embassy, Farmland, IllGottenGains, NobleBrigand, Trader]),
    CardSet(_("Schemes and Dreams [A&H]"),
        [Apothecary, Apprentice, Herbalist, PhilosophersStone, Transmute, Duchess, FoolsGold, IllGottenGains, JackOfAllTrades, Scheme]),
    CardSet(_("Wine Country [A&H]"),
        [Apprentice, Familiar, Golem, University, Vineyard, Crossroads, Farmland, Haggler, Highway, NomadCamp]),
    CardSet(_("Instant Gratification [P&H]"),
        [Bishop, Expand, Hoard, Mint, Watchtower, Farmland, Haggler, IllGottenGains, NobleBrigand, Trader]),
    CardSet(_("Treasure Trove [P&H]"),
        [Bank, Monument, RoyalSeal, TradeRoute, Venture, Cache, Develop, FoolsGold, IllGottenGains, Mandarin]),
    CardSet(_("Blue Harvest [C&H]"),
        [Hamlet, HornOfPlenty, HorseTraders, Jester, Tournament, FoolsGold, Mandarin, NobleBrigand, Trader, Tunnel]),
    CardSet(_("Traveling Circus [C&H]"),
        [Fairgrounds, FarmingVillage, HuntingParty, Jester, Menagerie, BorderVillage, Embassy, FoolsGold, NomadCamp, Oasis]),
    ]
