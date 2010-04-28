import sys
from random import SystemRandom
from threading import Thread, Condition

from domination.tools import _


random = SystemRandom()


class EndOfGameException(Exception):
    pass

class ActivateNextActionMultipleTimes(Exception):
    def __init__(self, times):
        self.times = times

class Request(object):
    def __init__(self, game, player, msg):
        self.player = player
        self.last_error = ""
        self.game = game
        self.msg = msg
        self.req_type = type(self).__name__

class YesNoQuestion(Request):
    def __init__(self, game, player, msg):
        Request.__init__(self, game, player, msg)

class SelectHandCards(Request):
    def __init__(self, game, player, msg, cls=None, count_lower=0, count_upper=None):
        Request.__init__(self, game, player, msg)
        self.cls = cls
        self.count_lower = count_lower
        self.count_upper = count_upper

    def is_selectable(self, card):
        if self.cls is None:
            return True
        return isinstance(card, self.cls)

def SelectActionCard(game, player, msg):
    return SelectHandCards(game, player, msg, ActionCard, 0, 1)

class SelectDeal(Request):
    def __init__(self, game, player, msg):
        Request.__init__(self, game, player, msg)
        self.money = self.player.remaining_money
        self.cards = CardTypeRegistry.keys2classes(self.game.supply.keys())
        self.cards.sort(key=lambda c: (c.cost, c.name), reverse=True)

    def is_buyable(self, card):
        return card.cost <= self.money and self.game.supply[card.__name__]


class SelectCard(Request):
    def __init__(self, game, player, msg, card_classes, show_supply_count=False):
        Request.__init__(self, game, player, msg)
        self.card_classes = card_classes
        self.show_supply_count = show_supply_count
        card_classes.sort(key=lambda x: x.cost, reverse=True)

class DebugRequest(Request):
    def __init__(self, exc_info):
        self.exc_info = exc_info

class InfoRequest(Request):
    def __init__(self, game, player, msg, cards):
        Request.__init__(self, game, player, msg)
        self.cards = cards

class EndOfGameRequest(InfoRequest):
    def __init__(self, game, player, reason):
        assert not player.discard_pile and not player.hand
        InfoRequest.__init__(self, game, player, _("The game has ended.")
                + " " + reason, player.deck)


class GameRunner(Thread):
    def __init__(self, game, owner):
        Thread.__init__(self)
        self.game = game
        self.seqno = 0
        self.seqno_condition = Condition()
        self.waiting_for = None
        self.owner = owner
        self.fresh = True

    def startable(self, player):
        return self.fresh and player is self.owner and not self.is_alive()\
                and len(self.game.players) > 1

    @property
    def joinable(self):
        return self.fresh

    def run(self):
        try:
            self._run()
        except EndOfGameException:
            pass
        except:
            self.owner.request_queue.append(DebugRequest(sys.exc_info()))
            self.increment_seqno()

    def increment_seqno(self):
        self.seqno_condition.acquire()
        self.seqno += 1
        self.seqno_condition.notifyAll()
        self.seqno_condition.release()

    def _run(self):
        self.fresh = False
        gen = self.game.play_game()
        reply = None
        while True:
            try:
                req = gen.send(reply)
            except StopIteration:
                break
            player = req.player
            assert not player.request_queue and not player.response
            if isinstance(req, InfoRequest):
                player.info_queue.append(req)
                self.waiting_for = None
                self.increment_seqno()
                continue
            player.request_queue.append(req)
            self.waiting_for = player
            self.increment_seqno()

            player.response_condition.acquire()
            while not player.response:
                player.response_condition.wait()
            reply = player.response[0]
            player.response = []
            player.response_condition.release()


class Game(object):
    def __init__(self, name):
        self.players = []
        self.supply = {}
        self.trash_pile = []
        self.name = name

    def add_supply(self, cls, no):
        self.supply.setdefault(cls.__name__, []).extend(cls() for _ in xrange(no))

    def play_round(self):
        for player in self.players:
            with player:
                discarded_cards = []
                # action
                break_selection = False
                next_times = None
                while player.remaining_actions and [c for c in player.hand
                        if isinstance(c, ActionCard)] and not break_selection:
                    action_cards = (yield SelectActionCard(self, player,
                        _("Which action card do you want to play?")))
                    if action_cards is None:
                        break_selection = True
                    else:
                        player.remaining_actions -= 1
                        card = action_cards[0]
                        for other_player in self.players:
                            if other_player is not player:
                                yield InfoRequest(self, other_player,
                                        _("%s plays:") % (player.name, ), [card])
                        player.hand.remove(card)
                        if card.trash_after_playing:
                            self.trash_pile.append(card)
                        else:
                            discarded_cards.append(card)

                        if next_times is not None:
                            times = next_times
                            next_times = None
                        else:
                            times = 1

                        while times > 0:
                            times -= 1
                            player.activated_cards.append(card)
                            try:
                                gen = card.activate_action(self, player)
                            except ActivateNextActionMultipleTimes, e:
                                if next_times is None:
                                    next_times = 0
                                next_times += e.times
                                continue
                            if gen is not None:
                                reply = None
                                # generic generator forwarding pattern
                                while True:
                                    try:
                                        reply = (yield gen.send(reply))
                                    except StopIteration:
                                        break
                            next_times = None
                # deal
                break_selection = False
                while player.remaining_deals and not break_selection:
                    card_key = (yield SelectDeal(self, player, _("Which card do you want to buy?")))
                    if card_key is None:
                        break_selection = True
                    else:
                        player.remaining_deals -= 1
                        cards = self.supply[card_key]
                        card, cards[:] = cards[-1], cards[:-1]
                        player.used_money += card.cost
                        player.discard_pile.append(card)
                        for other_player in self.players:
                            if other_player is not player:
                                yield InfoRequest(self, other_player,
                                        _("%s buys:") % (player.name, ), [card])

                # cleanup
                player.discard_pile.extend(discarded_cards)
                player.discard_pile.extend(player.hand)
                player.hand = []
                player.prepare_hand()
            reason = self.check_end_of_game()
            if reason:
                for req in self.end_of_game(reason):
                    yield req

    def play_game(self):
        self.deal_cards()
        for player in self.players:
            player.prepare_hand()
        while True:
            gen = self.play_round()
            # generic generator forwarding pattern
            reply = None
            while True:
                try:
                    reply = (yield gen.send(reply))
                except StopIteration:
                    break

    def deal_cards(self):
        raise NotImplementedError

    def check_end_of_game(self):
        raise NotImplementedError

    def end_of_game(game, reason):
        for player in game.players:
            player.deck += player.discard_pile + player.hand
            player.discard_pile = []
            player.hand = []
        for player in game.players:
            yield EndOfGameRequest(game, player, reason)
        raise EndOfGameException

    def following_players(self, current_player):
        players = self.players
        return players[players.index(current_player) + 1:] + \
                players[:players.index(current_player)]


class DominationGame(Game):
    MAX_PLAYERS = 4
    def __init__(self, name, selected_cards):
        Game.__init__(self, name)
        self.selected_cards = selected_cards

    def deal_cards(self):
        self.deal_initial_decks()
        self.deal_supply_cards(self.selected_cards)

    def deal_supply_cards(game, selected_cards):
        no_players = len(game.players)
        assert len(selected_cards) == 10
        game.add_supply(Copper, 60)
        game.add_supply(Silver, 40)
        game.add_supply(Gold, 30)
        if no_players == 2:
            victory_cards = 8
            curse_cards = 10
        else:
            victory_cards = 12
            if no_players == 3:
                curse_cards = 20
            else:
                curse_cards = 30

        game.add_supply(Curse, curse_cards)
        game.add_supply(Estate, victory_cards)
        game.add_supply(Duchy, victory_cards)
        game.add_supply(Province, victory_cards)
        for selected_card in selected_cards:
            amount = 10
            if selected_card is Gardens:
                amount = victory_cards
            game.add_supply(selected_card, amount)

    def deal_initial_decks(game):
        for player in game.players:
            assert not player.deck
            player.deck.extend(Copper() for _ in xrange(7))
            player.deck.extend(Estate() for _ in xrange(3))
            random.shuffle(player.deck)

    def check_end_of_game(self):
        if not self.supply["Province"]:
            return _("No provinces in supply left.")
        empty_batches = [card_key for card_key, cards in self.supply.items()
                if not cards]
        if len(empty_batches) > 2:
            return _("The following piles are empty:") + " " + \
                    ", ".join(card.name for card in
                            CardTypeRegistry.keys2classes(empty_batches))


class Player(object):
    def __init__(self, name):
        self.name = name
        self.discard_pile = []
        self.deck = []
        self.hand = []
        self.activated_cards = []
        self.remaining_deals = 0
        self.remaining_actions = 0
        self.used_money = 0
        self.virtual_money = 0
        self.current = False

        self.request_queue = []
        self.info_queue = []
        self.response_condition = Condition()
        self.response = []

    def __enter__(self):
        self.remaining_actions = 1
        self.remaining_deals = 1
        self.current = True

    def __exit__(self, exc_type, exc_value, traceback):
        self.remaining_deals = 0
        self.remaining_actions = 0
        self.virtual_money = 0
        self.used_money = 0
        self.activated_cards = []
        self.current = False

    @property
    def remaining_money(self):
        return self.virtual_money + sum(card.worth for card in self.hand)\
                - self.used_money

    @property
    def sorted_hand(self):
        return sorted(self.hand, key=lambda x: x.cost)

    def points(self, game):
        assert not self.discard_pile and not self.hand
        return sum(card.get_points(game, self) for card in self.deck)

    def prepare_hand(self):
        assert not self.hand
        self.draw_cards(5)

    def draw_cards(self, count):
        shuffled = False
        for _ in xrange(count):
            if not self.deck:
                self.deck, self.discard_pile = self.discard_pile, self.deck
                random.shuffle(self.deck)
                shuffled = True
            if self.deck:
                choice = self.deck.pop()
                self.hand.append(choice)
            else:
                return None
        return shuffled


class CardTypeRegistry(type):
    card_classes = []

    def __new__(cls, name, bases, d):
        abstract = d.pop("abstract", False)
        if not abstract:
            d['card_type'] = bases[0].__name__
        kls = type.__new__(cls, name, bases, d)
        if not abstract:
            CardTypeRegistry.card_classes.append(kls)
        return kls

    @staticmethod
    def keys2classes(keys):
        classes = []
        for key in keys:
            cls = globals()[key]
            if cls not in CardTypeRegistry.card_classes:
                raise KeyError
            classes.append(cls)
        return classes


class Card(object):
    __metaclass__ = CardTypeRegistry
    name = "UNKNOWN"
    cost = None
    points = 0
    worth = 0
    optional = False
    abstract = True
    trash_after_playing = False
    __slots__ = ()

    def __init__(self):
        self.__name__ = type(self).__name__
        assert self.name != "UNKNOWN"
        assert self.cost is not None
        assert self.points is not None
        assert self.worth is not None

    def activate_action(self, game, player):
        raise NotImplementedError

    def get_points(self, game, player):
        return self.points

    def discard(self, player):
        player.hand.remove(self)
        player.discard_pile.append(self)

    def trash(self, game, player):
        player.hand.remove(self)
        game.trash_pile.append(self)

    def defends(self, game, player, card):
        return False

class ActionCard(Card):
    optional = True
    abstract = True

class AttackCard(ActionCard):
    abstract = True

    def defends_check(self, game, other_player, msg):
        for card in other_player.hand:
            if card.defends(game, other_player, self):
                for info_player in game.following_players(other_player):
                    yield InfoRequest(game, info_player,
                        _(msg) % (other_player.name, ), [card])
                break

class ReactionCard(ActionCard):
    abstract = True

class VictoryCard(Card):
    abstract = True
    points = None

class TreasureCard(Card):
    abstract = True
    worth = None

class CurseCard(Card):
    abstract = True
    points = None

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
    points = 0

    def get_points(self, game, player):
        assert not player.hand and not player.discard_pile
        return len(player.deck) / 10

class Chapel(ActionCard):
    name = _("Chapel")
    cost = 2
    desc = _("Trash up to four cards from your hand.")

    def activate_action(self, game, player):
        cards = yield SelectHandCards(game, player, count_lower=0, count_upper=4,
                msg=_("Which cards do you want to trash?"))
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

    def activate_action(self, game, player):
        player.remaining_actions += 1
        player.remaining_deals += 1
        player.draw_cards(1)
        player.virtual_money += 1

class Militia(AttackCard):
    name = _("Militia")
    cost = 4
    desc = _("+2 Money, Each other player discards down to three cards in his hand.")

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
                    yield InfoRequest(game, info_player,
                            _("%s discards these cards:") % (other_player.name, ), cards)

class Mine(ActionCard):
    name = _("Mine")
    cost = 5
    desc = _("Trash a treasure card in your hand. Gain a treasure card costing"
            " up to three money more, put it in your hand.")

    def activate_action(self, game, player):
        cards = yield SelectHandCards(game, player, cls=TreasureCard,
                    count_lower=0, count_upper=1,
                    msg=_("Select a treasure card you want to convert to a potentially better card."))
        if cards:
            card = cards[0]
            card_classes = [c for c in
                CardTypeRegistry.card_classes if c.cost <= card.cost + 3 and
                game.supply.get(c.__name__) and issubclass(c, TreasureCard)]
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

    def activate_action(self, game, player):
        player.draw_cards(2)

    def defends(self, game, player, card):
        return True

class Remodel(ActionCard):
    name = _("Remodel")
    cost = 4
    desc = _("Trash a card from your hand. Gain a card costing up to 2 Money"
            " more than the trashed card.")

    def activate_action(self, game, player):
        cards = yield SelectHandCards(game, player,
                    count_lower=0, count_upper=1,
                    msg=_("Select a card you want to trash."))
        if cards:
            card = cards[0]
            card_cls = yield SelectCard(game, player, card_classes=[c for c in
                CardTypeRegistry.card_classes if c.cost <= card.cost + 2 and
                game.supply.get(c.__name__)],
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

    def activate_action(self, game, player):
        player.draw_cards(3)

class Village(ActionCard):
    name = _("Village")
    cost = 3
    desc = _("+1 Card, +2 Actions")

    def activate_action(self, game, player):
        player.draw_cards(1)
        player.remaining_actions += 2

class Adventurer(ActionCard):
    name = _("Adventurer")
    cost = 6
    desc = _("Reveal cards from your deck until you reveal 2 Treasure cards."
            " Put those Treasure cards into your hand and discard the other revealed cards.")

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

    def activate_action(self, game, player):
        card_cls = yield SelectCard(game, player, card_classes=[c for c in
            CardTypeRegistry.card_classes if c.cost <= 5 and
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

    def activate_action(self, game, player):
        player.remaining_actions += 2
        player.remaining_deals += 1
        player.virtual_money += 2

class Laboratory(ActionCard):
    name = _("Laboratory")
    cost = 5
    desc = _("+2 Cards, +1 Action")

    def activate_action(self, game, player):
        player.draw_cards(2)
        player.remaining_actions += 1

class Library(ActionCard):
    name = _("Library")
    cost = 5
    desc = _("Draw until you have 7 cards in your hand. You may set aside any"
            " action cards drawn this way, as you draw them; discard the set"
            " aside cards after you finish drawing.")

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

    def activate_action(self, game, player):
        player.remaining_actions += 1
        raise ActivateNextActionMultipleTimes(2)

class Witch(AttackCard):
    name = _("Witch")
    cost = 5
    desc = _("+2 Cards, Each other player gains a Curse card.")

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

    def activate_action(self, game, player):
        player.remaining_deals += 1
        player.virtual_money += 2

class Workshop(ActionCard):
    name = _("Workshop")
    cost = 3
    desc = _("Gain a card costing up to 4.")

    def activate_action(self, game, player):
        card_cls = yield SelectCard(game, player, card_classes=[c for c in
            CardTypeRegistry.card_classes if c.cost <= 4 and
            game.supply.get(c.__name__)],
            msg=_("Select a card that you want to have."), show_supply_count=True)
        new_card = game.supply[card_cls.__name__].pop(-1)
        player.discard_pile.append(new_card)
        for info_player in game.following_players(player):
            yield InfoRequest(game, info_player,
                    _("%s gains:") % (player.name, ), [new_card])

card_sets = {
    _('First game'): (Cellar, Market, Militia, Mine, Moat, Remodel, Smithy, Village,
        Woodcutter, Workshop),
    _('Big Money'): (Adventurer, Bureaucrat, Chancellor, Chapel, Feast, Laboratory,
        Market, Mine, Moneylender, ThroneRoom),
    _('Interaction'): (Bureaucrat, Chancellor, CouncilRoom, Festival, Library,
        Militia, Moat, Spy, Thief, Village),
    _('Size Distortion'): (Cellar, Chapel, Feast, Gardens, Laboratory, Thief, Village,
        Witch, Woodcutter, Workshop),
    _('Village Square'): (Bureaucrat, Cellar, Festival, Library, Market, Remodel,
        Smithy, ThroneRoom, Village, Woodcutter),
    "Test": (Workshop, Woodcutter, Witch, ThroneRoom, Thief),
}

