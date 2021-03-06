from domination.cards import TreasureCard, VictoryCard, CurseCard, ActionCard, \
     AttackCard, ReactionCard, PrizeCard, CardSet, Cornucopia, CardTypeRegistry
from domination.cards.base import Curse, Duchy, Province
from domination.gameengine import InfoRequest, SelectCard, SelectHandCards, \
     MultipleChoice, Question, YesNoQuestion, Defended, SelectActionCard
from domination.tools import _
from domination.macros.__macros__ import handle_defense, generator_forward, fetch_card_from_supply


class BagOfGold(PrizeCard, ActionCard):
    name = _("Bag of Gold")
    edition = Cornucopia
    cost = 0
    desc = _("+1 Action. Claim a gold, putting it on top of your deck.")

    def activate_action(self, game, player):
        player.remaining_actions += 1
        silver_cards = game.supply["Gold"]
        if silver_cards:
            player.deck.append(silver_cards.pop())
            for val in game.check_empty_pile("Gold"):
                yield val

class Diadem(PrizeCard, TreasureCard):
    name = _("Diadem")
    edition = Cornucopia
    cost = 0
    worth = 2
    desc = _("When you play this, +1 Money per unused Action you have.")

    def get_worth(self, player):
        return player.remaining_actions

class Fairgrounds(VictoryCard):
    name = _("Fairgrounds")
    edition = Cornucopia
    cost = 6
    desc = _("Worth 2 (VICTORY) for every 5 differently named cards in your deck (rounded down)")

    def get_points(self, game, player):
        assert not player.hand and not player.discard_pile
        return len(set(card.__name__ for card in player.deck)) / 5

class FarmingVillage(ActionCard):
    name = _("Farming Village")
    edition = Cornucopia
    cost = 4
    desc = _("+2 Actions. Reveal cards from the top of your deck until you reveal an Action or Treasure card. Put that card into your hand and and discard the other cards.")

    def activate_action(self, game, player):
        shuffled = 0
        found_cards = []
        to_be_discarded = []
        player.remaining_actions += 2
        while True:
            ret = player.draw_cards(1)
            if ret is None: # no cards left
                break
            shuffled += ret
            if shuffled == 2: # we shuffled our discard_pile 2 times, abort
                break
            card = player.hand.pop()
            for info_player in game.participants:
                yield InfoRequest(game, info_player, _("%s reveals:", (player.name, )), [card])
            if isinstance(card, ActionCard) or isinstance(card, TreasureCard):
                found_cards.append(card)
                break
            else:
                to_be_discarded.append(card)
        player.discard_pile.extend(to_be_discarded)
        player.hand.extend(found_cards)

class Followers(PrizeCard, AttackCard):
    name = _("Followers")
    edition = Cornucopia
    cost = 0
    desc = _("+2 Cards. Gain an Estate. Each other player gains a Curse and discards down to 3 Cards in hand.")

    def activate_action(self, game, player):
        player.draw_cards(2)
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

            count = len(other_player.hand) - 3
            if count <= 0:
                continue
            cards = yield SelectHandCards(game, other_player, count_lower=count, count_upper=count,
                    msg=_("%s played Followers. Which cards do you want to discard?", (player.name, )))
            for card in cards:
                card.discard(other_player)
            for info_player in game.participants:
                if info_player is not other_player:
                    # TODO: info players may only see one of the discarded cards
                    yield InfoRequest(game, info_player,
                            _("%s discards these cards:", (other_player.name, )), cards)

class FortuneTeller(AttackCard):
    name = _("Fortune Teller")
    edition = Cornucopia
    cost = 3
    desc = _("+2 Money. Each other player reveals cards from the top of his deck until he reveals a Victory or Curse card. He puts it on top and discards the other revealed cards.")

    def activate_action(self, game, player):
        player.virtual_money += 2
        for other_player in game.following_players(player):
            try:
                handle_defense(self, game, other_player)
            except Defended:
                continue
            found_cards = []
            to_be_discarded = []
            shuffled = 0
            while True:
                ret = other_player.draw_cards(1)
                if ret is None: # no cards left
                    break
                shuffled += ret
                if shuffled == 2: # we shuffled our discard_pile 2 times, abort
                    break
                card = other_player.hand.pop()
                if isinstance(card, VictoryCard) or isinstance(card, Curse):
                    found_cards.append(card)
                    break
                else:
                    to_be_discarded.append(card)
            for info_player in game.participants:
                yield InfoRequest(game, info_player, _("%s reveals:", (other_player.name, )), to_be_discarded+found_cards)
            other_player.discard_pile.extend(to_be_discarded)
            other_player.deck.extend(found_cards)

class Hamlet(ActionCard):
    name = _("Hamlet")
    edition = Cornucopia
    cost = 2
    desc = _("+1 Card, +1 Action. You may discard a card; if you do, +1 Action. You may discard a card; if you do, +1 Buy.")

    def activate_action(self, game, player):
        player.draw_cards(1)
        player.remaining_actions += 1
        cards = yield SelectHandCards(game, player, count_lower=0, count_upper=2,
                msg=_("Which cards do you want to discard?"))
        # discard cards
        if cards is not None:
            cardcount = len(cards)
            for card in cards:
                card.discard(player)
            for info_player in game.participants:
                if info_player is not player:
                    yield InfoRequest(game, info_player, _("%s discards these cards:", (player.name, )), cards)
            if cardcount >= 1:
                player.remaining_actions += 1
            if cardcount >= 2:
                player.remaining_deals += 1

class Harvest(ActionCard):
    name = _("Harvest")
    edition = Cornucopia
    cost = 5
    desc = _("Reveal the top 4 cards of your deck, then discard them. +1 Money per differently named card revealed.")

    def activate_action(self, game, player):
        player.draw_cards(4)
        drawn, player.hand = player.hand[-4:], player.hand[:-4]

        for info_player in game.participants:
            yield InfoRequest(game, info_player, _("%s reveals the top 4 cards of his deck:", (player.name, )), drawn)
        player.virtual_money += len(set(card.__name__ for card in drawn))
        player.discard_pile.extend(drawn)

class HornOfPlenty(TreasureCard):
    name = _("Horn of Plenty")
    edition = Cornucopia
    cost = 5
    worth = 0
    desc = _("When you play this, gain a card costing up to 1 Money per differently named card you have in play, counting this. If it's a Victory card, thrash this.")

    def activate_action(self, game, player):
        money = len(set(card.__name__ for card in player.aux_cards))
        card_cls = yield SelectCard(game, player, card_classes=[c for c in
            game.card_classes.itervalues() if c.cost <= money and
            game.supply.get(c.__name__) and c.potioncost == 0],
            msg=_("Select a card that you want to have."), show_supply_count=True)
        new_card = game.supply[card_cls.__name__].pop()
        player.discard_pile.append(new_card)
        for info_player in game.following_participants(player):
            yield InfoRequest(game, info_player,
                    _("%s gains:", (player.name, )), [new_card])
        for val in game.check_empty_pile(card_cls.__name__):
            yield val

class HorseTraders(ReactionCard):
    name = _("Horse Traders")
    edition = Cornucopia
    implemented = False #FIXME not implemented completely
    cost = 4
    desc = _("+1 Buy, +3 Money, Discard 2 Cards. | When another player plays an Attack card, you may set this aside from your hand. If you do, then at the start of your next turn, +1 Card and return this to your hand.")

    def activate_action(self, game, player):
        player.remaining_deals += 1
        player.virtual_money += 3
        cards = yield SelectHandCards(game, player, count_lower=2, count_upper=2,
                msg=_("Which two cards do you want to discard?"))
        # discard cards
        if cards is not None:
            for card in cards:
                card.discard(player)
            for info_player in game.participants:
                if info_player is not player:
                    yield InfoRequest(game, info_player,
                            _("%s discards these cards:", (player.name, )), cards)

    def defend_action(self, game, player, card):
        pass

class HuntingParty(ActionCard):
    name = _("Hunting Party")
    edition = Cornucopia
    cost = 5
    desc = _("+1 Card, +1 Action. Reveal your hand. Reveal cards from your deck until you reveal a card that isn't a duplicate of one in your hand. Put it into your hand and discard the rest.")

    def activate_action(self, game, player):
        to_be_discarded = []
        found = []
        player.draw_cards(1)
        player.remaining_actions += 1
        if player.hand:
            for info_player in game.participants:
                yield InfoRequest(game, info_player, _("%s reveals his hand:", (player.name, )), player.hand)
            card_classes = [type(c) for c in player.hand]
            while True:
                ret = player.draw_cards(1)
                if ret is None: # no cards left
                    break
                card = player.hand.pop()
                if type(card) in card_classes:
                    to_be_discarded.append(card)
                else:
                    found.append(card)
                    break
            if to_be_discarded + found:
                for info_player in game.participants:
                    yield InfoRequest(game, info_player, _("%s reveals:", (player.name, )), to_be_discarded + found)
            player.discard_pile.extend(to_be_discarded)
        player.hand.extend(found)


class Jester(AttackCard):
    name = _("Jester")
    edition = Cornucopia
    cost = 5
    desc = _("+2 Money. Each other player discards the top card of his deck. If it's a Victory card he gains a Curse. Otherwise either he gains a copy of the discarded or you do, your choice.")

    def activate_action(self, game, player):
        player.virtual_money += 2
        for other_player in game.following_players(player):
            try:
                handle_defense(self, game, other_player)
            except Defended:
                continue
            ret = other_player.draw_cards(1)
            if ret is None: # no cards left
                break
            card = other_player.hand.pop()
            for info_player in game.participants:
                if info_player is not player:
                    yield InfoRequest(game, info_player,
                            _("%s discards:", (other_player.name, )), [card])
            if isinstance(card, VictoryCard):
                curse_cards = game.supply["Curse"]
                other_player.discard_pile.append(curse_cards.pop())
                yield InfoRequest(game, other_player,
                        _("%s curses you. You gain a curse card.", (player.name, )), [])
                for val in game.check_empty_pile("Curse"):
                    yield val
            else:
                other_player.draw_cards(1)
                cards = other_player.hand.pop()
                yield InfoRequest(game, player, _("%s discards the top card of his deck:",
                        (other_player.name, )), [card])
                other_player.discard_pile.extend([card])

                actions = [("give", _("Give another copy of it to him")),
                           ("take", _("Take a copy for yourself"))]

                answer = yield Question(game, player, _("What do you want to do?"),
                                        actions)

                for info_player in game.following_participants(player):
                    yield InfoRequest(game, info_player,
                            _("%(player)s chooses '%(action)s'", {"player": player.name, "action": _(dict(actions)[answer])}), [])
                if game.supply[card.__name__]:
                    new_card = game.supply[card.__name__].pop()
                    if answer == "give":
                        other_player.discard_pile.append(new_card)
                        yield InfoRequest(game, info_player,
                                _("%s gains:", (other_player.name, )), [new_card])
                    if answer == "take":
                        player.discard_pile.append(new_card)
                        yield InfoRequest(game, info_player,
                                _("%s gains:", (player.name, )), [new_card])
                    for val in game.check_empty_pile(card.__name__):
                        yield val

class Menagerie(ActionCard):
    name = _("Menagerie")
    edition = Cornucopia
    cost = 3
    desc = _("+1 Action. Reveal your hand, If there are no duplicate cards in it. +3 Cards. Otherwise, +1 Card.")

    def activate_action(self, game, player):
        player.remaining_actions += 1
        if (len(set(card.__name__ for card in player.deck)) == len(player.deck)):
            player.draw_cards(3)
        else:
            player.draw_cards(1)

class Princess(PrizeCard, ActionCard):
    name = _("Princess")
    edition = Cornucopia
    cost = 0
    desc = _("+1 Buy | While this is in play, Cards cost 2 Money less, but not less than 0 Money.")

    def activate_action(self, game, player):
        player.remaining_deals += 1
        decreased_for_cards = []
        for card in game.card_classes.itervalues():
            if card.cost >= 2:
                card.cost -= 2
                decreased_for_cards.append(card)
        def restore_cards(player):
            for card in decreased_for_cards:
                card.cost += 2
        player.register_turn_cleanup(restore_cards)

class Remake(ActionCard):
    name = _("Remake")
    edition = Cornucopia
    cost = 5
    desc = _("Do this twice: Trash a card from your hand, then gain a card costing exactly 1 Money more than the trashed card.")

    def activate_action(self, game, player):
        for i in range(0,2):
            cards = yield SelectHandCards(game, player,
                        count_lower=1, count_upper=1,
                        msg=_("Select a card you want to trash."))
            if cards:
                card = cards[0]
                card_classes = [c for c in game.card_classes.itervalues()
                                if c.cost == card.cost + 1 and
                                game.supply.get(c.__name__) and
                                c.potioncost == card.potioncost]

                card.trash(game, player)
                if card_classes:
                    card_cls = yield SelectCard(game, player, card_classes=card_classes,
                        msg=_("Select a treasure card that you want to have."), show_supply_count=True)
                    new_card = game.supply[card_cls.__name__].pop()
                    player.hand.append(new_card)
                    for info_player in game.following_participants(player):
                        yield InfoRequest(game, info_player,
                                _("%s trashes:", (player.name, )), [card])
                        yield InfoRequest(game, info_player,
                                _("%s gains:", (player.name, )), [new_card])
                    for val in game.check_empty_pile(card_cls.__name__):
                        yield val

class Tournament(ActionCard):
    name = _("Tournament")
    edition = Cornucopia
    cost = 4
    desc = _("+1 Action. Each player may reveal a Province from his hand. If you do, discard it and gain a Prize (from the Prize pile) or a Duchy, putting it on top of your deck. If no-one else does, +1 Card, +1 Money.")

    def activate_action(self, game, player):
        player.remaining_actions += 1
        others_revealed = False
        player_revealed = False
        for other_player in game.all_players(player):
            province_cards = [c for c in other_player.hand if isinstance(c, Province)]
            if province_cards:
                card = province_cards[0]
                reply = (yield YesNoQuestion(game, other_player,
                    _("Do you want to reveal a Province card from your hand?")))
                if reply:
                    if other_player is player:
                        player_revealed = True
                        card.discard(player)
                        card_cls = (yield SelectCard(game, player, _("Which prize card do you want to gain?"),
                            [type(c) for c in game.tournament_cards] + [Duchy]))
                        if card_cls is Duchy:
                            with fetch_card_from_supply(game, card_cls) as new_card:
                                card = new_card
                        else:
                            card = [c for c in game.tournament_cards if isinstance(c, card_cls)][0]
                            game.tournament_cards.remove(card)
                        player.deck.append(card)
                    else:
                        others_revealed = True
                    for info_player in game.following_participants(other_player):
                        yield InfoRequest(game, info_player, _("%s reveals a card:", (other_player.name, )), [card])
        if not others_revealed:
            player.virtual_money += 1
            player.draw_cards(1)

    @classmethod
    def on_setup_card(self, game):
        game.tournament_cards = [c() for c in CardTypeRegistry.raw_card_classes.values() if issubclass(c, PrizeCard)]

    @classmethod
    def on_render_piles(self, game, player):
        yield (_('Available prize cards'), True, game.tournament_cards)


class TrustySteed(PrizeCard, ActionCard):
    name = _("Trusty Steed")
    edition = Cornucopia
    implemented = False # XXX comment block/notification
    cost = 0
    desc = _("Choose two: +2 Cards, +2 Actions, +2 Money, gain 4 Silvers and put your deck into the discard pile (the choices must be different.)")

    def activate_action(self, game, player):
        actions = [("cards", _("+2 Cards")),
                   ("actions", _("+2 Actions")),
                   ("money", _("+2 Money")),
                   ("silverdiscard", _("Gain 4 Silvers and discard Hand"))]

        while True:
            answers = yield MultipleChoice(game, player, _("What do you want to do?"), actions, min_amount=2, max_amount=2)
            if len(answers) == 2:
                break

#        for info_player in game.following_participants(player):
#            yield InfoRequest(game, info_player,
#                    _("%(player)s chooses '%(action1)s' and '%(action2)s'", {"player": player.name, "action1": _(dict(actions)[answer[0]]), "action2": _(dict(actions)[answer[1]]}), [])
        if "cards" in answers:
            player.draw_cards(2)
        if "actions" in answers:
            player.remaining_actions += 2
        if "money" in answers:
            player.virtual_money += 2
        if "silverdiscard" in answers:
            silver_cards = game.supply["Silver"]
            if silver_cards:
                player.hand.append(silver_cards.pop())
                for val in game.check_empty_pile("Silver"):
                    yield val
            silver_cards = game.supply["Silver"]
            if silver_cards:
                player.hand.append(silver_cards.pop())
                for val in game.check_empty_pile("Silver"):
                    yield val
            player.discard_pile.extend(player.deck)
            player.deck = []

class YoungWitch(AttackCard):
    name = _("Young Witch")
    edition = Cornucopia
    implemented = False #FIXME not implemented completely
    cost = 4
    desc = _("+2 Cards. Discard 2 cards. Each other player may reveal a Bane cards from his hand. If he doesn't he gets a Curse.")

    def activate_action(self, game, player):
        player.draw_cards(2)
        cards = yield SelectHandCards(game, player, count_lower=2, count_upper=2,
                msg=_("Which two cards do you want to discard?"))
        # discard cards
        if cards is not None:
            for card in cards:
                card.discard(player)
            for info_player in game.participants:
                if info_player is not player:
                    yield InfoRequest(game, info_player,
                            _("%s discards these cards:", (player.name, )), cards)


from domination.cards.base import (
    Adventurer, Bureaucrat, Cellar, Feast, Festival, Laboratory, Market, Militia, Moneylender, Remodel, Spy, Smithy, ThroneRoom, Workshop)
from domination.cards.intrigue import (
    Conspirator, Coppersmith, Courtyard, Duke, GreatHall, Harem, MiningVillage, Nobles, Minion, Pawn, Swindler, Steward, Tribute)

card_sets = [
    CardSet(_("Bounty of the Hunt [B&C]"),
        [Harvest, HornOfPlenty, Menagerie, HuntingParty, Tournament, Moneylender, Festival, Cellar, Militia, Smithy]),
    CardSet(_("Bad Omens [B&C]"),
        [HornOfPlenty, Jester, Remake, FortuneTeller, Hamlet, Adventurer, Bureaucrat, Laboratory, Spy, ThroneRoom]),
    CardSet(_("The Jester's Workshop [B&C]"),
        [FarmingVillage, Fairgrounds, Jester, YoungWitch, HorseTraders, Feast, Laboratory, Market, Remodel, Workshop]),
    CardSet(_("Last Laughs [I&C]"),
        [FarmingVillage, Harvest, Jester, HorseTraders, HuntingParty, Nobles, Pawn, Minion, Swindler, Steward]),
    CardSet(_("The Spice of Life [I&C]"),
        [Fairgrounds, HornOfPlenty, YoungWitch, Remake, Tournament, MiningVillage, Courtyard, GreatHall, Coppersmith, Tribute]),
    CardSet(_("Small Victories [I&C]"),
        [Remake, HuntingParty, Tournament, FortuneTeller, Hamlet, GreatHall, Pawn, Harem, Duke, Conspirator]),
] # Bei Wanderzirkus: Kanzler im Bannstapel, bei Würze des Lebens: Wunschbrunnen im Bannstapel
