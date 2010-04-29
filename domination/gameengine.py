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

class Defended(Exception):
    pass

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

class Question(Request):
    def __init__(self, game, player, msg, options):
        Request.__init__(self, game, player, msg)
        self.options = options

class MultipleChoice(Request):
    def __init__(self, game, player, msg, options):
        Request.__init__(self, game, player, msg)
        self.options = options

class SelectHandCards(Request):
    def __init__(self, game, player, msg, cls=None, count_lower=0, count_upper=None,
                 not_selectable=()):
        Request.__init__(self, game, player, msg)
        self.cls = cls
        self.count_lower = count_lower
        self.count_upper = count_upper
        self.not_selectable = not_selectable

    def is_selectable(self, card):
        if card in self.not_selectable:
            return False
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
                        _("Which action card do you want to play? (%i actions left)")
                            % (player.remaining_actions, )))
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
                        card = self.supply[card_key].pop()
                        for val in self.check_empty_pile(card_key):
                            yield val
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

    def check_empty_pile(self, key):
        if not self.supply[key]:
            for player in self.players:
                card_name = CardTypeRegistry.keys2classes((key, ))[0].name
                yield InfoRequest(self, player, _("The pile %s is empty.") % (card_name, ), [])


class DominationGame(Game):
    MAX_PLAYERS = 6 # maximum allowed number of players
    def __init__(self, name, selected_cards):
        Game.__init__(self, name)
        self.selected_cards = selected_cards # cards chosen for the game

    def deal_cards(self):
        self.deal_initial_decks()
        self.deal_supply_cards(self.selected_cards)

    def deal_supply_cards(game, selected_cards):
        no_players = len(game.players) # number of players
        # debug check that there are 10 kinds of kingdom cards in selected_cards
        assert len(selected_cards) == 10

        # add treasure cards
        if no_players > 4:
            game.add_supply(Copper, 120)
            game.add_supply(Silver, 80)
            game.add_supply(Gold, 60)
        else:
            game.add_supply(Copper, 60)
            game.add_supply(Silver, 40)
            game.add_supply(Gold, 30)

        # add victory cards (except victory kingdom cards)
        if no_players == 2:
            victory_cards = 8
            province_cards = 8
        elif no_players == 5:
            victory_cards = 12
            province_cards = 15
        elif no_players == 6:
            victory_cards = 12
            province_cards = 18
        else:
            victory_cards = 12
        province_cards = 12
        curse_cards = (no_players - 1) * 10

        game.add_supply(Curse, curse_cards)
        game.add_supply(Estate, victory_cards)
        game.add_supply(Duchy, victory_cards)
        game.add_supply(Province, province_cards)

        # add kingdom cards
        for selected_card in selected_cards:
            amount = 10
            if selected_card is Gardens: # modify for additional victory cards
                amount = victory_cards
            game.add_supply(selected_card, amount)

    def deal_initial_decks(game): # deal the starting hands
        for player in game.players: # every player...
            assert not player.deck # ...does not have a deck...
            player.deck.extend(Copper() for _ in xrange(7)) # ...gets 7 Copper
            player.deck.extend(Estate() for _ in xrange(3)) # ...and 3 Estates.
            random.shuffle(player.deck) # then his deck is shuffled

    def check_end_of_game(self):
        no_players = len(self.players) # number of players
        if not self.supply["Province"]: # check if province supply is empty
            return _("Province supply is empty.")
        # fill empty_batches with card keys of cards the supply of which is empty
        empty_batches = [card_key for card_key, cards in self.supply.items()
                if not cards]
        if no_players < 5:
            must_empty = 3
        else:
            must_empty = 4
        # check if at least must_empty supply piles are empty
        if len(empty_batches) >= must_empty:
            return _("The following supplies are empty:") + " " + \
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


# import necessary objects from cards here because of circular importing

from domination.cards import editions
from domination.cards import CardTypeRegistry, ActionCard
from domination.cards.base import (Copper, Silver, Gold, Curse,
                                   Estate, Duchy, Province, Gardens)

from domination.cards.base import card_sets as card_sets_base
from domination.cards.intrigue import card_sets as card_sets_intrigue

card_sets = card_sets_base + card_sets_intrigue
