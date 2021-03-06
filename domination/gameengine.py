import sys
import pickle
from random import SystemRandom
from threading import Thread, local
from threading import _Condition as PristineCondition
from collections import defaultdict

from domination.tools import _, taint_filename
from domination.macros.__macros__ import generator_forward, generator_forward_ex


random = SystemRandom()
TLS = local()


class Condition(PristineCondition):
    def __getstate__(self):
        return True

    def __setstate__(self, *args):
        PristineCondition.__init__(self)


class EndOfGameException(Exception):
    pass

class PlayerKickedException(Exception):
    pass

class ActivateNextActionMultipleTimes(Exception):
    def __init__(self, times):
        self.times = times

class Defended(Exception):
    pass

class AbortBuy(Exception):
    pass

class Request(object):
    choices = NotImplemented # used for AI and testing
    wise_slice = None
    def __init__(self, game, player, msg):
        self.player = player
        self.last_error = ""
        self.game = game
        self.msg = msg
        self.req_type = type(self).__name__

    def __hash__(self):
        data = dict(player=self.player, game=self.game, msg=self.msg,
                req_type=self.req_type).items()
        return hash(tuple(sorted(data)))

    def choose_randomly(self):
        if not self.choices:
            return
        return random.choice(self.choices)

    def choose_wisely(self):
        if not self.choices:
            return
        if self.wise_slice is not None:
            return self.choices[self.wise_slice]
        return self.choose_randomly()

class Checkpoint(Request):
    def __init__(self, game):
        Request.__init__(self, game, None, None)

class MultipleChoicesRequestMixin(object):
    number_of_choices = -1
    def choose_randomly(self):
        assert self.number_of_choices != -1
        return random.sample(self.choices, self.number_of_choices)


class YesNoQuestion(Request):
    choices = (False, True)
    def __init__(self, game, player, msg):
        Request.__init__(self, game, player, msg)

class Question(Request):
    def __init__(self, game, player, msg, options):
        Request.__init__(self, game, player, msg)
        self.options = options
        self.choices = [choice for choice, _ in options]

class MultipleChoice(MultipleChoicesRequestMixin, Request):
    def __init__(self, game, player, msg, options, min_amount=1, max_amount=None):
        Request.__init__(self, game, player, msg)
        if max_amount is None:
            max_amount = len(options)
        self.min_amount = min_amount
        self.max_amount = max_amount
        self.options = options
        self.number_of_choices = max_amount
        self.choices = [choice for choice, _ in self.options]

class SelectHandCards(MultipleChoicesRequestMixin, Request):
    def __init__(self, game, player, msg, cls=None, count_lower=0, count_upper=None,
                 not_selectable=(), preselect_all=False):
        Request.__init__(self, game, player, msg)
        self.cls = cls
        self.count_lower = count_lower
        self.count_upper = count_upper
        self.not_selectable = not_selectable
        self.preselect_all = preselect_all

        count = self.count_lower
        if self.count_upper is not None:
            count = self.count_upper
        if count == 0:
            count = 2 # arbitrary
        if "trash" in msg:
            # chapel
            if (count_upper == 4 and count_lower != 4) or \
                    (count_upper == 1 and count_lower == 0): # masquerade
                count = len([c for c in player.hand if c.__name__ == 'Estate'])
        count = min(count, len(self.choices), count_upper)
        self.number_of_choices = count
        self.wise_slice = slice(0, count)

    @property
    def choices(self):
        def key(c):
            factor = 1
            functokens = c.activate_action.im_func.func_code.co_names
            if "trash" in self.msg and c.points == 1 and self.count_upper != 1:
                factor = -50
            elif "trash" in self.msg and self.count_upper == 1:
                factor = -1
            elif "want to play" in self.msg:
                if "remaining_actions" in functokens:
                    factor = -4
                elif "SelectActionCard" in functokens: # throne room
                    factor = -6
                else:
                    factor = -1
            elif "Militia" in self.msg and isinstance(c, VictoryCard):
                factor = -10
            return c.get_cost(self.game, self.player) * factor
        return sorted([c for c in self.player.hand if self.is_selectable(c)],
                key=key)

    def is_selectable(self, card):
        if card in self.not_selectable:
            return False
        if self.cls is None:
            return True
        return isinstance(card, self.cls)

    def fulfillable(self):
        return bool([c for c in self.player.hand if self.is_selectable(c)])

def SelectActionCard(game, player, msg):
    return SelectHandCards(game, player, msg, ActionCard, 0, 1)

class SelectDeal(Request):
    wise_slice = 0
    def __init__(self, game, player, msg):
        Request.__init__(self, game, player, msg)
        self.money = self.player.remaining_money
        self.potion = self.player.remaining_potion
        self.cards = CardTypeRegistry.keys2classes(self.game.supply.keys())
        self.cards.sort(key=lambda c: (c.get_cost(game, player), c.name), reverse=True)

    @property
    def choices(self):
        l = [c for c in self.cards if self.is_buyable(c) and c.points not in (-1, 1) and c.get_worth != 1]
        random.shuffle(l)
        # we want to buy the most expensive card but not the same one every time
        l.sort(key=lambda c: c.get_cost(self.game, self.player), reverse=True)
        return [c.__name__ for c in l]

    def is_buyable(self, card):
        return card.get_cost(self.game, self.player) <= self.money and card.potioncost <= self.potion and self.game.supply[card.__name__]


class SelectCard(Request):
    wise_slice = 0
    def __init__(self, game, player, msg, card_classes, show_supply_count=False):
        Request.__init__(self, game, player, msg)
        self.card_classes = card_classes
        self.show_supply_count = show_supply_count
        card_classes.sort(key=lambda x: x.get_cost(game, player), reverse=True)
        self.choices = self.card_classes

    def fulfillable(self):
        return bool(self.card_classes)

class DebugRequest(Request):
    def __init__(self, exc_info):
        self.exc_info = exc_info

class InfoRequest(Request):
    def __init__(self, game, player, msg, cards):
        Request.__init__(self, game, player, msg)
        self.cards = cards


FRESH = "Fresh"
RUNNING = "Running"
ENDED = "Ended"
STATES = [FRESH, RUNNING, ENDED]

class GameRunner(Thread):
    def __init__(self, game, owner, seqno=0, waiting_for=None, state=FRESH):
        Thread.__init__(self)
        self.game = game
        self.seqno = seqno
        self.seqno_condition = Condition()
        self.waiting_for = waiting_for
        self.owner = owner
        self.state = state
        self.do_cancel = False
        self.starting_from_checkpoint = seqno != 0

    def __getstate__(self):
        return (self.game, self.owner, self.seqno, self.waiting_for, self.state)

    def __setstate__(self, args):
        GameRunner.__init__(self, *args)

    def startable(self, player):
        return self.state is FRESH and player is self.owner and not self.is_alive()\
                and len(self.game.players) > 1

    @property
    def joinable(self):
        return self.state is FRESH

    def run(self):
        TLS.game = self.game
        try:
            self._run()
        except EndOfGameException:
            pass
        except:
            self.owner.request_queue.append(DebugRequest(sys.exc_info()))
        self.state = ENDED
        self.waiting_for = None
        self.increment_seqno()

    def increment_seqno(self):
        self.seqno_condition.acquire()
        self.seqno += 1
        self.seqno_condition.notifyAll()
        self.seqno_condition.release()

    def _run(self):
        if not self.starting_from_checkpoint:
            self.state = RUNNING
        gen = self.game.play_game(self.starting_from_checkpoint)
        reply = None
        while not self.do_cancel:
            try:
                req = gen.send(reply)
            except StopIteration:
                break
            player = req.player
            if player is not None:
                assert not getattr(player, "request_queue", None) and not player.response
            if isinstance(req, InfoRequest):
                player.info_queue.append(req)
                self.waiting_for = None
                self.increment_seqno()
                continue
            if isinstance(req, Checkpoint):
                self.waiting_for = None
                self.store()
                continue
            req.seqno = self.seqno + 1
            player.request_queue.append(req)
            self.waiting_for = player
            player.compute_response() # used for bots
            self.increment_seqno()

            player.response_condition.acquire()
            while not player.response and not self.do_cancel:
                player.response_condition.wait()
            if not self.do_cancel:
                reply = player.response[0]
            player.response = []
            if player.kicked_by:
                reply = PlayerKickedException(player)
                for participant in self.game.participants:
                    participant.info_queue.append(InfoRequest(self.game, participant, _("%(kicker)s kicked %(kickee)s.", {"kicker": player.kicked_by.name, "kickee": player.name}), []))
                player.name += " (kicked)"
            player.response_condition.release()

    def cancel(self):
        self.do_cancel = True
        if self.state is FRESH:
            self.state = ENDED
            self.increment_seqno()
        else:
            try:
                self.game.end_of_game()
            except EndOfGameException:
                pass
        for participant in self.game.participants:
            cv = participant.response_condition
            cv.acquire()
            cv.notifyAll()
            cv.release()

    def store(self):
        from domination.main import app
        path = app.game_storage_prefix + taint_filename(self.game.name
            + app.game_storage_postfix)
        if app.game_storage_path:
            path = os.path.join(app.game_storage_path, taint_filename(self.game.name
            + app.game_storage_postfix))
        f = file(path, "wb")
        pickle.dump(self, f)#, -1)
        f.close()

from domination.cards import DurationCard, Card

class Game(object):
    HOOKS = ["on_pre_buy_card", "on_end_of_game", "on_start_of_turn", "on_end_of_turn", "on_buy_card", "on_render_card_info",
            "on_gain_card", "on_setup_card", "on_render_piles"]

    def __init__(self, name, selected_cards):
        from domination.cards import CardTypeRegistry
        self.selected_cards = selected_cards
        self.players = []
        self.pending_round_players = None
        self.finished_round_players = []
        self.kibitzers = []
        self.supply = {}
        self.trash_pile = []
        self.end_of_game_reason = False
        self.round = 0
        self.name = name
        self.card_classes = CardTypeRegistry.raw_card_classes
        self.cost_delta = {}
        self.cards_to_draw = 5
        self._hooks = {}
        self.prepare_hooks(selected_cards)
        self.player_options = {}
        self.player_option_defaults = {}

    def __hash__(self):
        return hash(self.name)

    def __getstate__(self):
        d = self.__dict__.copy()
        if d.get("_hooks", None) is not None:
            del d['_hooks']
        return d

    @property
    def hooks(self):
        if not hasattr(self, "_hooks"):
            self._hooks = {}
            self.prepare_hooks(self.selected_cards)
        return self._hooks

    def prepare_hooks(self, cards):
        for hook_name in Game.HOOKS:
            self._hooks[hook_name] = []
            for card in cards + [Card]:
                if hook_name in card.__dict__:
                    self._hooks[hook_name].append(getattr(card, hook_name))

    def fire_hook(self, hook_name, *args):
        for hook in self.hooks[hook_name]:
            hookgen = hook(*args)
            generator_forward(hookgen)

    @property
    def participants(self):
        return self.players + self.kibitzers

    def add_supply(self, cls, no):
        self.supply.setdefault(cls.__name__, []).extend(cls() for _ in xrange(no))

    def play_action_card(self, player, card):
        player.activated_cards.append(card)
        try:
            gen = card.activate_action(self, player)
        except NotImplementedError:
            return
        for other_player in self.participants:
            if other_player is not player:
                yield InfoRequest(self, other_player,
                        _("%s plays:", (player.name, )), [card])

        generator_forward(gen)

    def kick(self, kicker, kickee):
        cv = kickee.response_condition
        kickee.kicked_by = kicker
        cv.acquire()
        try:
            req = kickee.request_queue.pop(0)
            response = req.choose_wisely()
            kickee.response.append(response)
            cv.notify()
        finally:
            cv.release()
        del self.players[self.players.index(kickee)]

    def play_round(self):
        from domination.cards import TreasureCard

        self.pending_round_players = players = self.players[:]
        while players:
            player = players.pop(0)
            self.finished_round_players.append(player)
            with player:
                try:
                    # duration actions from last round
                    for card in player.duration_cards:
                        duration_func = card.duration_action
                        card.durationaction_activated = False
                        gen = duration_func(self, player)
                        generator_forward(gen)
                    player.aux_cards.extend(player.duration_cards)
                    if player.duration_cards:
                        for other_player in self.participants:
                            if other_player is not player:
                                yield InfoRequest(self, other_player,
                                        _("%s had duration cards:", (player.name, )), player.duration_cards)
                    player.duration_cards = []

                    gen = self.fire_hook("on_start_of_turn", self, player)
                    generator_forward(gen)

                    # action
                    while player.remaining_actions and [c for c in player.hand
                            if isinstance(c, ActionCard)]:
                        action_cards = (yield SelectActionCard(self, player,
                            _("Which action card do you want to play? (%i actions left)", (player.remaining_actions, ))))
                        if action_cards is None:
                            break
                        player.remaining_actions -= 1
                        card = action_cards[0]
                        player.hand.remove(card)
                        if card.trash_after_playing:
                            self.trash_pile.append(card)
                        else:
                            player.aux_cards.append(card)
                        gen = self.play_action_card(player, card)
                        generator_forward(gen)

                    # select money cards
                    if not player.options["automatic_money_selection"]:
                        cards = (yield SelectHandCards(self, player, _("Which money cards do you want to play?"), TreasureCard,
                            preselect_all=True))
                        if cards is None:
                            cards = []
                    else:
                        cards = [c for c in player.hand if isinstance(c, TreasureCard)]
                    player.aux_cards.extend(cards)
                    for card in cards:
                        player.hand.remove(card)
                    player.activated_treasure_cards = cards
                    for card in cards:
                        gen = self.play_action_card(player, card)
                        generator_forward(gen)

                    # deal
                    break_selection = False
                    while player.remaining_deals and not break_selection:
                        card_key = (yield SelectDeal(self, player, _("Which card do you want to buy?")))
                        if card_key is None:
                            break_selection = True
                        else:
                            try:
                                cardcls = CardTypeRegistry.keys2classes((card_key, ))[0]
                                gen = self.fire_hook("on_pre_buy_card", self, player, cardcls)
                                generator_forward(gen)
                            except AbortBuy:
                                continue
                            player.remaining_deals -= 1
                            card = self.supply[card_key].pop()
                            for val in self.check_empty_pile(card_key):
                                yield val
                            player.used_money += card.get_cost(self, player)
                            player.used_potion += card.potioncost
                            player.discard_pile.append(card)
                            for other_player in self.participants:
                                if other_player is not player:
                                    yield InfoRequest(self, other_player,
                                            _("%s buys:", (player.name, )), [card])
                            gen = self.fire_hook("on_buy_card", self, player, card)
                            generator_forward(gen)

                        reason = self.check_end_of_game()
                        if reason:
                            self.end_of_game_reason = reason
                            self.end_of_game()
                    cards_to_draw = self.cards_to_draw
                finally:
                    # cleanup pt. 1
                    for cleanup_func in player.turn_cleanups:
                        gen = cleanup_func(player)
                        generator_forward(gen)

                # cleanup pt. 2
                for card in player.aux_cards:
                    if card.durationaction_activated:
                        player.duration_cards.append(card)
                    else:
                        player.discard_pile.append(card)
                player.aux_cards = []
                player.discard_pile.extend(player.hand)
                player.hand = []
                player.prepare_hand(cards_to_draw)
                gen = self.fire_hook("on_end_of_turn", self, player)
                generator_forward(gen)
        self.finished_round_players[:] = []

    def play_game(self, starting_from_checkpoint):
        if not starting_from_checkpoint:
            self.deal_cards()
            gen = self.fire_hook("on_setup_card", self)
            generator_forward(gen)
            for player in self.players:
                player.prepare_hand(self.cards_to_draw)
                for optionkey, optionvalue in self.player_option_defaults.items():
                    player.options[optionkey] = optionvalue
        while True:
            yield Checkpoint(self)
            self.round += 1
            gen = self.play_round()
            generator_forward_ex(gen, [PlayerKickedException])

    def deal_cards(self):
        raise NotImplementedError

    def check_end_of_game(self):
        raise NotImplementedError

    def end_of_game(self):
        list(self.fire_hook("on_end_of_game", self))
        for player in self.players:
            player.deck += player.discard_pile + player.hand + player.aux_cards + player.duration_cards
            player.discard_pile = []
            player.hand = []
            player.aux_cards = []
            player.duration_cards = []
        raise EndOfGameException

    def all_players(self, current_player):
        """ Returns all players in the correct order.
        """
        players = self.players
        return players[players.index(current_player):] + \
                players[:players.index(current_player)]

    def following_players(self, current_player):
        """ Returns all other players in the correct order.
        """
        players = self.players
        return players[players.index(current_player) + 1:] + \
                players[:players.index(current_player)]

    def following_participants(self, current_player):
        """ Returns all other players in the correct order and adds
        the kibitzers."""
        return self.following_players(current_player) + self.kibitzers

    def check_empty_pile(self, key):
        if not self.supply[key]:
            for player in self.players + self.kibitzers:
                card_name = CardTypeRegistry.keys2classes((key, ))[0].name
                yield InfoRequest(self, player, _("The pile %s is empty.", (card_name, )), [])

    @property
    def player_names(self):
        return ", ".join(p.name for p in self.players)

    @property
    def empty_pile_names(self):
        empty_batches = [card_key for card_key, cards in self.supply.items()
                if not cards]
        return u", ".join(unicode(card.name) for card in
                CardTypeRegistry.keys2classes(empty_batches))

    @property
    def empty_pile_count(self):
        empty_batches = [card_key for card_key, cards in self.supply.items()
                if not cards]
        return len(empty_batches)

    def get_additional_piles(self, player):
        return list(self.fire_hook("on_render_piles", self, player))


from domination.cards import Alchemy
from domination.cards import Prosperity

class DominationGame(Game):
    MAX_PLAYERS = 6 # maximum allowed number of players

    @property
    def selected_cards_str(self):
        return ", ".join(unicode(c.name) for c in self.selected_cards)

    @property
    def selected_cards_keys(self):
        return [c.__name__ for c in self.selected_cards]

    def deal_cards(self):
        self.deal_initial_decks()
        self.deal_supply_cards(self.selected_cards)

    def deal_supply_cards(game, selected_cards):
        no_players = len(game.players) # number of players
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

        if any([c.potioncost + (c.__name__ == "BlackMarket") for c in selected_cards]):
            game.add_supply(Potion, 16)

        if any([c.edition == Prosperity for c in selected_cards]):
            if no_players == 2:
                game.add_supply(Platinum, 8)
                game.add_supply(Colony, 8)
            elif no_players == 5:
                game.add_supply(Platinum, 12)
                game.add_supply(Colony, 12)
            elif no_players == 6:
                game.add_supply(Platinum, 12)
                game.add_supply(Colony, 12)
            else:
                game.add_supply(Platinum, 12)
                game.add_supply(Colony, 12)

        game.add_supply(Curse, curse_cards)
        game.add_supply(Estate, victory_cards)
        game.add_supply(Duchy, victory_cards)
        game.add_supply(Province, province_cards)

        # add kingdom cards
        for selected_card in selected_cards:
            amount = 10
            if selected_card in (Gardens, Vineyard): # modify for additional victory cards
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
        if not self.supply["Province"]: # check if Province supply is empty
            return True
        if "Colony" in self.supply: # check if there is a Colony supply
            if not self.supply["Colony"]: # check if Colony supply is empty
                return True
        # fill empty_batches with card keys of cards the supply of which is empty
        empty_batches = [card_key for card_key, cards in self.supply.items()
                if not cards]
        if no_players < 5:
            must_empty = 3
        else:
            must_empty = 4
        if len(empty_batches) >= must_empty:
            return True


class Kibitzer(object):
    def __init__(self, name):
        self.name = name
        self.last_seqno = -1

        self.info_queue = []
        self.response_condition = Condition()
        self.response = []


class Player(object):
    is_ai = False
    def __init__(self, name):
        self.name = name
        self.discard_pile = []
        self.deck = []
        self.hand = []
        self.activated_cards = []
        self.aux_cards = [] # cards lying on the table etc.
        self.remaining_deals = 0
        self.remaining_actions = 0
        self.used_money = 0
        self.virtual_money = 0
        self.used_potion = 0
        self.tokens = 0 # points from prosperity
        self.current = False
        self.kicked_by = None
        self.turn_cleanups = []
        self.duration_cards = [] # duration_cards from seaside
        self.options = {}
        self.activated_treasure_cards = None

        self.request_queue = []
        self.info_queue = []
        self.response_condition = Condition()
        self.response = []

    def __hash__(self):
        return hash(self.name)

    def __enter__(self):
        self.remaining_actions = 1
        self.remaining_deals = 1
        self.current = True

    def __exit__(self, exc_type, exc_value, traceback):
        self.remaining_deals = 0
        self.remaining_actions = 0
        self.virtual_money = 0
        self.used_money = 0
        self.used_potion = 0
        self.activated_cards = []
        self.current = False
        self.turn_cleanups = []
        self.activated_treasure_cards = None
        if exc_type is PlayerKickedException:
            return True

    def __repr__(self):
        return "<Player %r>" % (self.name, )

    def register_turn_cleanup(self, func):
        self.turn_cleanups.append(func)

    def compute_response(self):
        pass

    @property
    def remaining_money(self):
        return self.virtual_money + sum(card.get_worth(self) for card in self.activated_treasure_cards)\
                - self.used_money

    @property
    def remaining_potion(self):
        return sum(card.potion for card in self.aux_cards)\
                - self.used_potion

    @property
    def sorted_hand(self):
        return sorted(self.hand, key=lambda x: x.get_cost(None, self))

    @property
    def total_cards(self): # does not include activated cards
        return self.hand + self.discard_pile + self.deck + self.aux_cards

    def points(self, game):
        return sum(card.get_points(game, self) for card in self.deck) + self.tokens

    def prepare_hand(self, cards_to_draw):
        assert not self.hand
        self.draw_cards(cards_to_draw)

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

    def left(self, game):
        gp = game.players
        i = gp.index(self)
        return gp[(i + 1) % len(gp)]

    def right(self, game):
        gp = game.players
        i = gp.index(self)
        return gp[(i - 1) % len(gp)]

class AIPlayer(Player):
    is_ai = True
    def compute_response(self):
        req = self.request_queue.pop(0)
        response = req.choose_wisely()
        self.response.append(response)
        self.info_queue = []


# import necessary objects from cards here because of circular importing

from domination.cards import editions
from domination.cards import CardTypeRegistry, ActionCard, VictoryCard
from domination.cards.base import (Copper, Silver, Gold, Curse,
                                   Estate, Duchy, Province, Gardens)
from domination.cards.alchemy import Potion, Vineyard
from domination.cards.prosperity import Platinum, Colony

from domination.cards.base import card_sets as card_sets_base
from domination.cards.intrigue import card_sets as card_sets_intrigue
from domination.cards.alchemy import card_sets as card_sets_alchemy
from domination.cards.seaside import card_sets as card_sets_seaside
from domination.cards.prosperity import card_sets as card_sets_prosperity
from domination.cards.cornucopia import card_sets as card_sets_cornucopia
from domination.cards.hinterlands import card_sets as card_sets_hinterlands

card_sets = card_sets_base + card_sets_intrigue + card_sets_alchemy + card_sets_seaside + card_sets_prosperity + card_sets_cornucopia + card_sets_hinterlands
