from domination.cards import TreasureCard, VictoryCard, CurseCard, ActionCard, \
     AttackCard, ReactionCard, BaseGame, CardTypeRegistry, CardSet
from domination.gameengine import InfoRequest, SelectCard, SelectHandCards, \
     YesNoQuestion, ActivateNextActionMultipleTimes
from domination.tools import _


class Copper(TreasureCard):
    name = _("Copper")
    cost = 0
    worth = 1

class Silver(TreasureCard):
    name = _("Silver")
    cost = 3
    worth = 2

class Gold(TreasureCard):
    name = _("Gold")
    cost = 6
    worth = 3

class Estate(VictoryCard):
    name = _("Estate")
    cost = 2
    points = 1

class Duchy(VictoryCard):
    name = _("Duchy")
    cost = 5
    points = 3

class Province(VictoryCard):
    name = _("Province")
    cost = 8
    points = 6

class Curse(CurseCard):
    name = _("Curse")
    cost = 0
    points = -1

class Gardens(VictoryCard):
    name = _("Gardens")
    cost = 4
    desc = _("Worth one point for every ten cards in your deck (rounded down)")
    optional = True
    edition = BaseGame
    points = 0

    def get_points(self, game, player):
        assert not player.hand and not player.discard_pile
        return len(player.deck) / 10

class Chapel(ActionCard):
    name = _("Chapel")
    cost = 2
    desc = _("Trash up to four cards from your hand.")
    edition = BaseGame

    def activate_action(self, game, player):
        if player.hand:
            cards = yield SelectHandCards(game, player, count_lower=1, count_upper=4,
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

class Cellar(ActionCard):
    name = _("Cellar")
    cost = 2
    desc = _("+1 Action, Discard any number of cards. +1 Card per card discarded.")
    edition = BaseGame

    def activate_action(self, game, player):
        player.remaining_actions += 1
        cards = yield SelectHandCards(game, player, count_lower=0, count_upper=None,
                msg=_("Which cards do you want to discard?"))
        # discard cards
        if cards is not None:
            for card in cards:
                card.discard(player)
            player.draw_cards(len(cards))
            for other_player in game.players:
                if other_player is not player:
                    yield InfoRequest(game, other_player,
                            _("%s discards these cards:") % (player.name, ), cards)

class Market(ActionCard):
    name = _("Market")
    cost = 5
    desc = _("+1 Card, +1 Action, +1 Buy, +1 Money")
    edition = BaseGame

    def activate_action(self, game, player):
        player.remaining_actions += 1
        player.remaining_deals += 1
        player.draw_cards(1)
        player.virtual_money += 1

class Militia(AttackCard):
    name = _("Militia")
    cost = 4
    desc = _("+2 Money, Each other player discards down to three cards in his hand.")
    edition = BaseGame

    def activate_action(self, game, player):
        player.virtual_money += 2
        for other_player in game.following_players(player):
            defends = False
            for item in self.defends_check(game, other_player,
                    _("%s defends against the Militia with:")):
                defends = True
                yield item
            if defends:
                continue
            count = len(other_player.hand) - 3
            if count <= 0:
                continue
            cards = yield SelectHandCards(game, other_player, count_lower=count, count_upper=count,
                    msg=_("%s played Militia. Which cards do you want to discard?") % (player.name, ))
            for card in cards:
                card.discard(other_player)
            for info_player in game.players:
                if info_player is not other_player:
                    # TODO: info players may only see one of the discarded cards
                    yield InfoRequest(game, info_player,
                            _("%s discards these cards:") % (other_player.name, ), cards)

class Mine(ActionCard):
    name = _("Mine")
    cost = 5
    desc = _("Trash a treasure card in your hand. Gain a treasure card costing"
            " up to three money more, put it in your hand.")
    edition = BaseGame

    def activate_action(self, game, player):
        cards = yield SelectHandCards(game, player, cls=TreasureCard,
                    count_lower=0, count_upper=1,
                    msg=_("Select a treasure card you want to convert to a potentially better card."))
        if cards:
            card = cards[0]
            card_classes = [c for c in CardTypeRegistry.card_classes.itervalues()
                            if c.cost <= card.cost + 3 and
                            game.supply.get(c.__name__) and
                            issubclass(c, TreasureCard)]
            card_cls = yield SelectCard(game, player, card_classes=card_classes,
                msg=_("Select a treasure card that you want to have."), show_supply_count=True)
            card.trash(game, player)
            new_card = game.supply[card_cls.__name__].pop(-1)
            player.hand.append(new_card)
            for info_player in game.players:
                if info_player is not player:
                    yield InfoRequest(game, info_player,
                            _("%s trashes:") % (player.name, ), [card])
                    yield InfoRequest(game, info_player,
                            _("%s gains:") % (player.name, ), [new_card])

class Moat(ReactionCard):
    name = _("Moat")
    cost = 2
    desc = _("+2 Cards, When another player plays an attack card, you may"
            " reveal this from your hand. If you do, you are unaffected by"
            " the attack.")
    edition = BaseGame

    def activate_action(self, game, player):
        player.draw_cards(2)

    def defends(self, game, player, card):
        return True

class Remodel(ActionCard):
    name = _("Remodel")
    cost = 4
    desc = _("Trash a card from your hand. Gain a card costing up to 2 Money"
            " more than the trashed card.")
    edition = BaseGame

    def activate_action(self, game, player):
        if not player.hand:
            return
        cards = yield SelectHandCards(game, player,
                    count_lower=0, count_upper=1,
                    msg=_("Select a card you want to trash."))
        if cards:
            card = cards[0]
            card_cls = yield SelectCard(game, player, card_classes=[c for c in
                CardTypeRegistry.card_classes.itervalues()
                if c.cost <= card.cost + 2 and game.supply.get(c.__name__)],
                msg=_("Select a card that you want to have."), show_supply_count=True)
            card.trash(game, player)
            new_card = game.supply[card_cls.__name__].pop(-1)
            player.discard_pile.append(new_card)

            for info_player in game.players:
                if info_player is not player:
                    yield InfoRequest(game, info_player,
                            _("%s trashes:") % (player.name, ), [card])
                    yield InfoRequest(game, info_player,
                            _("%s gains:") % (player.name, ), [new_card])

class Smithy(ActionCard):
    name = _("Smithy")
    cost = 4
    desc = _("+3 Cards")
    edition = BaseGame

    def activate_action(self, game, player):
        player.draw_cards(3)

class Village(ActionCard):
    name = _("Village")
    cost = 3
    desc = _("+1 Card, +2 Actions")
    edition = BaseGame

    def activate_action(self, game, player):
        player.draw_cards(1)
        player.remaining_actions += 2

class Adventurer(ActionCard):
    name = _("Adventurer")
    cost = 6
    desc = _("Reveal cards from your deck until you reveal 2 Treasure cards."
            " Put those Treasure cards into your hand and discard the other revealed cards.")
    edition = BaseGame

    def activate_action(self, game, player):
        treasure_cards_found = 0
        shuffled = 0
        while True:
            ret = player.draw_cards(1)
            if ret is None: # no cards left
                break
            shuffled += ret
            if shuffled == 2: # we shuffled our discard_pile 2 times, abort
                break
            card = player.hand.pop()
            for info_player in game.players:
                yield InfoRequest(game, info_player, _("%s reveals:") % (player.name, ), [card])
            if isinstance(card, TreasureCard):
                player.hand.append(card)
                treasure_cards_found += 1
                if treasure_cards_found == 2:
                    break
            else:
                player.discard_pile.append(card)

class Bureaucrat(AttackCard):
    name = _("Bureaucrat")
    cost = 4
    desc = _("Gain a Silver card; put it on top of your deck. Each other player"
            " reveals a Victory card from his hand and puts it on his deck (or"
            " reveals a hand with no Victory cards).")
    edition = BaseGame

    def activate_action(self, game, player):
        silver_cards = game.supply["Silver"]
        if silver_cards:
            player.deck.append(silver_cards.pop(-1))
        for other_player in game.following_players(player):
            defends = False
            for item in self.defends_check(game, other_player,
                    _("%s defends against the Bureaucrat with:")):
                defends = True
                yield item
            if defends:
                continue
            victory_cards = [c for c in other_player.hand if isinstance(c, VictoryCard)]
            if victory_cards:
                card = (yield SelectHandCards(game, other_player,
                    _("Select a Victory card you want to reveal"), VictoryCard, 1, 1))[0]
                other_player.deck.append(card)
                other_player.hand.remove(card)
                for info_player in game.following_players(other_player):
                    yield InfoRequest(game, info_player, _("%s reveals a card:") % (other_player.name, ), [card])
            else:
                for info_player in game.following_players(other_player):
                    yield InfoRequest(game, info_player, _("%s reveals his hand:") % \
                            (other_player.name, ), other_player.hand)

class Chancellor(ActionCard):
    name = _("Chancellor")
    cost = 3
    desc = _("+2 Money, You may immediately put your deck into your discard pile.")
    edition = BaseGame

    def activate_action(self, game, player):
        player.virtual_money += 2
        if (yield YesNoQuestion(game, player, _("Do you want to put your deck"
            " into your discard pile?"))):
            player.discard_pile.extend(player.deck)
            player.deck = []

class CouncilRoom(ActionCard):
    name = _("Council Room")
    cost = 5
    desc = _("+4 cards, +1 buy, Each other player draws a card.")
    edition = BaseGame

    def activate_action(self, game, player):
        player.draw_cards(4)
        player.remaining_deals += 1
        for other_player in game.following_players(player):
            other_player.draw_cards(1)

class Feast(ActionCard):
    name = _("Feast")
    cost = 4
    trash_after_playing = True
    desc = _("Trash this card, gain a card costing up to 5.")
    edition = BaseGame

    def activate_action(self, game, player):
        card_cls = yield SelectCard(game, player, card_classes=[c for c in
            CardTypeRegistry.card_classes.itervalues() if c.cost <= 5 and
            game.supply.get(c.__name__)],
            msg=_("Select a card that you want to have."), show_supply_count=True)
        new_card = game.supply[card_cls.__name__].pop(-1)
        player.discard_pile.append(new_card)
        for info_player in game.following_players(player):
            yield InfoRequest(game, info_player,
                    _("%s gains:") % (player.name, ), [new_card])

class Festival(ActionCard):
    name = _("Festival")
    cost = 5
    desc = _("+2 Actions, +1 Buy, +2 Money")
    edition = BaseGame

    def activate_action(self, game, player):
        player.remaining_actions += 2
        player.remaining_deals += 1
        player.virtual_money += 2

class Laboratory(ActionCard):
    name = _("Laboratory")
    cost = 5
    desc = _("+2 Cards, +1 Action")
    edition = BaseGame

    def activate_action(self, game, player):
        player.draw_cards(2)
        player.remaining_actions += 1

class Library(ActionCard):
    name = _("Library")
    cost = 5
    desc = _("Draw until you have 7 cards in your hand. You may set aside any"
            " action cards drawn this way, as you draw them; discard the set"
            " aside cards after you finish drawing.")
    edition = BaseGame

    def activate_action(self, game, player):
        set_aside_cards = []
        while len(player.hand) != 7 and (player.discard_pile or player.deck):
            player.draw_cards(1)
            drawn_card = player.hand[-1]
            if isinstance(drawn_card, ActionCard) and (yield YesNoQuestion(game,
                player, _("Do you want to set aside"
                " the card '%s'?") % (drawn_card.name, ))):
                player.hand.pop(-1)
                set_aside_cards.append(drawn_card)
        player.discard_pile.extend(set_aside_cards)

class Moneylender(ActionCard):
    name = _("Moneylender")
    cost = 4
    desc = _("Trash a Copper card from your hand. If you do, +3 Money.")
    edition = BaseGame

    def activate_action(self, game, player):
        copper_cards = [c for c in player.hand if isinstance(c, Copper)]
        if copper_cards:
            player.virtual_money += 3
            card = copper_cards[0]
            card.trash(game, player)
            for info_player in game.following_players(player):
                yield InfoRequest(game, info_player,
                        _("%s trashes:") % (player.name, ), [card])

class Spy(AttackCard):
    name = _("Spy")
    cost = 4
    desc = _("+1 Card, +1 Action, Each player (including you) reveals the top"
            " card of his deck and either discards it or puts it back,"
            " your choice.")
    edition = BaseGame

    def activate_action(self, game, player):
        player.draw_cards(1)
        player.remaining_actions += 1
        for other_player in game.players:
            defends = False
            for item in self.defends_check(game, other_player,
                    _("%s defends against the Spy with:")):
                defends = True
                yield item
            if defends:
                continue
            other_player.draw_cards(1)
            card = other_player.hand.pop()
            for info_player in game.players:
                yield InfoRequest(game, info_player, _("%s reveals the top card of his deck:") %
                        (other_player.name, ), [card])
            if (yield YesNoQuestion(game, player,
                _("Do you want to discard %(name)s's card '%(cardname)s'?") %
                {"cardname": card.name, "name": other_player.name})):
                other_player.discard_pile.append(card)
                for info_player in game.following_players(player):
                    yield InfoRequest(game, info_player,
                            _("%(playername)s discarded %(player2name)s's card:") %
                            {"playername": player.name, "player2name": other_player.name},
                            [card])
            else:
                other_player.deck.append(card)

class Thief(AttackCard):
    name = _("Thief")
    cost = 4
    desc = _("Each other player reveals the top 2 cards of his deck."
            " If they revealed any Treasure cards, they trash one of them that"
            " you choose. You may gain any or all of these trashed cards. They"
            " discard the other revealed cards.")
    edition = BaseGame

    def activate_action(self, game, player):
        trashed = []
        for other_player in game.following_players(player):
            defends = False
            for item in self.defends_check(game, other_player,
                    _("%s defends against the Thief with:")):
                defends = True
                yield item
            if defends:
                continue
            cards = []
            other_player.draw_cards(2)
            cards.append(other_player.hand.pop())
            cards.append(other_player.hand.pop())
            for info_player in game.players:
                yield InfoRequest(game, info_player, _("%s reveals the top 2 cards of his deck:") %
                        (other_player.name, ), cards[:])
            treasure_cards = [c for c in cards if isinstance(c, TreasureCard)]
            treasure_card_classes = list(set([type(c) for c in treasure_cards]))
            if treasure_cards:
                card_cls = (yield SelectCard(game, player,
                    _("Which card of the player %s do you want to trash?") %
                    (other_player.name, ), card_classes=treasure_card_classes))
                card = [c for c in treasure_cards if isinstance(c, card_cls)][0]
                trashed.append(card)
                cards.remove(card)
                for info_player in game.following_players(player):
                    yield InfoRequest(game, info_player, _("%s trashes:") %
                            (player.name, ), [card])
            other_player.discard_pile.extend(cards)
        for card in trashed:
            if (yield YesNoQuestion(game, player,
                _("Do you want to have the card '%s'?") % (card.name, ))):
                player.discard_pile.append(card)
                for info_player in game.following_players(player):
                    yield InfoRequest(game, info_player, _("%s picks up this card from trash:") %
                            (player.name, ), [card])
            else:
                game.trash_pile.append(card)

class ThroneRoom(ActionCard):
    name = _("Throne Room")
    cost = 4
    desc = _("Choose an action card in your hand. Play it twice.")
    edition = BaseGame

    def activate_action(self, game, player):
        player.remaining_actions += 1
        raise ActivateNextActionMultipleTimes(2)

class Witch(AttackCard):
    name = _("Witch")
    cost = 5
    desc = _("+2 Cards, Each other player gains a Curse card.")
    edition = BaseGame

    def activate_action(self, game, player):
        player.draw_cards(2)
        curse_cards = game.supply["Curse"]
        for other_player in game.following_players(player):
            if curse_cards:
                defends = False
                for item in self.defends_check(game, other_player,
                        _("%s defends against the Witch with:")):
                    defends = True
                    yield item
                if defends:
                    continue
                other_player.discard_pile.append(curse_cards.pop())
                yield InfoRequest(game, other_player,
                        _("%s curses you. You gain a curse card.") % (player.name, ), [])

class Woodcutter(ActionCard):
    name = _("Woodcutter")
    cost = 3
    desc = _("+1 Buy, +2 Money")
    edition = BaseGame

    def activate_action(self, game, player):
        player.remaining_deals += 1
        player.virtual_money += 2

class Workshop(ActionCard):
    name = _("Workshop")
    cost = 3
    desc = _("Gain a card costing up to 4.")
    edition = BaseGame

    def activate_action(self, game, player):
        card_cls = yield SelectCard(game, player, card_classes=[c for c in
            CardTypeRegistry.card_classes.itervalues() if c.cost <= 4 and
            game.supply.get(c.__name__)],
            msg=_("Select a card that you want to have."), show_supply_count=True)
        new_card = game.supply[card_cls.__name__].pop(-1)
        player.discard_pile.append(new_card)
        for info_player in game.following_players(player):
            yield InfoRequest(game, info_player,
                    _("%s gains:") % (player.name, ), [new_card])


card_sets = [
    CardSet(_('First Game'),
            [Cellar, Market, Militia, Mine, Moat, Remodel, Smithy,
             Village, Woodcutter, Workshop]),
    CardSet(_('Big Money'),
            [Adventurer, Bureaucrat, Chancellor, Chapel, Feast,
             Laboratory, Market, Mine, Moneylender, ThroneRoom]),
    CardSet(_('Interaction'),
            [Bureaucrat, Chancellor, CouncilRoom, Festival, Library,
             Militia, Moat, Spy, Thief, Village]),
    CardSet(_('Size Distortion'),
            [Cellar, Chapel, Feast, Gardens, Laboratory, Thief, Village,
             Witch, Woodcutter, Workshop]),
    CardSet(_('Village Square'),
            [Bureaucrat, Cellar, Festival, Library, Market, Remodel,
             Smithy, ThroneRoom, Village, Woodcutter]),
]
