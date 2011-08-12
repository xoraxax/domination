from domination.cards import TreasureCard, VictoryCard, CurseCard, ActionCard, \
     DurationCard, AttackCard, ReactionCard, CardSet, Prosperity
from domination.cards.base import Duchy, Estate, Copper, Province, Curse
from domination.gameengine import SelectHandCards, Question, MultipleChoice, \
     InfoRequest, SelectCard, Defended, YesNoQuestion, \
     SelectActionCard
from domination.tools import _
from domination.macros.__macros__ import handle_defense, generator_forward,\
        fetch_card_from_supply


class Platinum(TreasureCard):
    name = _("Platinum")
    edition = Prosperity
    cost = 9
    worth = 5

class Colony(VictoryCard):
    name = _("Colony")
    edition = Prosperity
    cost = 11
    points = 10

class TradeRoute(ActionCard):
    name = _("Trade Route")
    edition = Prosperity
    cost = 3
    desc = _("+1 Buy, +1 Money per token on the Trade Route mat. Trash a card from your hand.| Setup: Put a token on each Victory card Supply pile. When a card is gained from that pile, move the token to the Trade Route mat.")
    implemented=False

    def activate_action(self, game, player):
        player.remaining_deals += 1
        player.virtual_money += 1 #FIXME

class Loan(TreasureCard):
    name = _("Loan")
    edition = Prosperity
    cost = 3
    worth = 2
    desc = _("When you play this, reveal cards from your deck until you reveal a treasure. Discard it or trash it. Discard the other cards.")

    def activate_action(self, game, player):
        found_treasure = []
        to_be_discarded = []
        while True:
            ret = player.draw_cards(1)
            if ret is None: # no cards left
                break
            card = player.hand.pop()
            for info_player in game.participants:
                yield InfoRequest(game, info_player, _("%s reveals:", (player.name, )), [card])
            if isinstance(card, TreasureCard):
                found_treasure.append(card)
                break
            else:
                to_be_discarded.append(card)
        player.discard_pile.extend(to_be_discarded)
        if (yield YesNoQuestion(game, player,
            _("Do you want to trash your Treasure?"))): #FIXME show which treasure was found, and ask trash/discard instead of yes/no
            found_treasure.trash(game, player)
        else:
            player.discard_pile.extend(to_be_discarded)

class Watchtower(ReactionCard):
    name = _("Watchtower")
    edition = Prosperity
    cost = 3
    desc = _("Draw until you have 6 cards in hand.| When you gain a card, you may reveal this from your hand. If you do, either trash that card, or put it on top of your deck.")
    implemented=False

    def activate_action(self, game, player):
        pass

class WorkersVillage(ActionCard):
    name = _("Worker's Village")
    edition = Prosperity
    cost = 4
    desc = _("+1 Card, +2 Actions, +1 Buy")

    def activate_action(self, game, player):
        player.remaining_actions += 2
        player.remaining_deals += 1
        player.draw_cards(1)

class Bishop(ActionCard):
    name = _("Bishop")
    edition = Prosperity
    cost = 4
    desc = _("+1 Money, +1 Token. Trash a card from your hand. +Tokens equal to half its costs in coins, rounded down. Each other player may trash a card from his hands.")

    def activate_action(self, game, player):
        player.virtual_money += 1
        player.tokens += 1
        if player.hand:
            cards = yield SelectHandCards(game, player,
                        count_lower=0, count_upper=1,
                        msg=_("Select a card you want to trash."))
            if cards:
                card = cards[0]
                player.tokens += card.cost / 2
                card.trash(game, player)
                for info_player in game.following_participants(player):
                    yield InfoRequest(game, info_player,
                            _("%s trashes:", (player.name, )), [card])
        for other_player in game.following_players(player):
            cards = yield SelectHandCards(game, other_player, count_lower=0, count_upper=1,
                    msg=_("%s played Bishop. You may trash a card:?", (player.name, )))
            if cards:
                for card in cards:
                    card.trash(game, other_player)
                    for info_player in game.following_participants(other_player):
                        yield InfoRequest(game, info_player,
                            _("%s trashes:", (other_player.name, )), cards)

class Monument(ActionCard):
    name = _("Monument")
    edition = Prosperity
    cost = 4
    desc = _("+2 Money, +1 Token")

    def activate_action(self, game, player):
        player.virtual_money += 2
        player.tokens += 1

class Quarry(TreasureCard):
    name = _("Quarry")
    edition = Prosperity
    cost = 4
    worth = 1
    desc = _("|While this is in play, Action cards cost 2 Money less, but no less than 0.")

    def activate_action(self, game, player):
        decreased_for_cards = []
        action_card_classes  = [cls for cls in game.card_classes.itervalues()
                    if isinstance(cls, ActionCard)]
        for card in action_card_classes:
            if card.cost >= 1:
                card.cost -= 1
                decreased_for_cards.append(card)
            if card.cost >= 1:
                card.cost -= 1
                decreased_for_cards.append(card)
        def restore_cards(player):
            for card in decreased_for_cards:
                card.cost += 1
        player.register_turn_cleanup(restore_cards)

class Talisman(TreasureCard):
    name = _("Talisman")
    edition = Prosperity
    cost = 4
    worth = 1
    desc = _("While this is in play, when you buy a card costing 4 Money or less that is not a Victory card, gain a copy of it.")

    def activate_action(self, game, player):
        pass

    @classmethod
    def on_buy_card(cls, game, player, card):
        for c in player.aux_cards:
            if isinstance(c, Talisman):
                if not isinstance(card, VictoryCard) and card.cost <= 4:
                    with fetch_card_from_supply(game, type(card)) as new_card:
                        player.discard_pile.append(new_card)
                        for info_player in game.participants:
                            yield InfoRequest(game, info_player, _("%s gains another card (because of Talisman):", (player.name, )), [new_card])


class Venture(TreasureCard):
    name = _("Venture")
    edition = Prosperity
    cost = 5
    worth = 1
    desc = _("When you play this, you reveal cards from your deck until you reveal a Treasure. Discard the other cards. Play that Treasure.")

    def activate_action(self, game, player):
        found_treasure = []
        to_be_discarded = []
        while True:
            ret = player.draw_cards(1)
            if ret is None: # no cards left
                break
            card = player.hand.pop()
            for info_player in game.participants:
                yield InfoRequest(game, info_player, _("%s reveals:", (player.name, )), [card])
            if isinstance(card, TreasureCard):
                found_treasure.append(card)
                break
            else:
                to_be_discarded.append(card)
        player.discard_pile.extend(to_be_discarded)
        found_treasure.activate_action(game, player)

class Rabble(AttackCard):
    name = _("Rabble")
    edition = Prosperity
    cost = 5
    desc = _("+3 Cards. Each other player reveals the top 3 cards of his deck, discards the revealed Actions and Treasures, and puts the rest back on top in any order he chooses.")

    def activate_action(self, game, player):
        player.draw_cards(3)
        to_be_discarded = []
        for other_player in game.following_players(player):
            try:
                handle_defense(self, game, other_player)
            except Defended:
                continue
            other_player.draw_cards(3)
            cards = []
            cards.append(other_player.hand.pop())
            cards.append(other_player.hand.pop())
            cards.append(other_player.hand.pop())
            for info_player in game.participants:
                yield InfoRequest(game, info_player, _("%s reveals the top card of his deck:",
                        (other_player.name, )), cards)
            for card in cards:
                if isinstance(card, TreasureCard) or isinstance(card, ActionCard):
                    to_be_discarded.append(card)
            for info_player in game.participants:
                yield InfoRequest(game, info_player, _("%s discards:",
                        (other_player.name, )), to_be_discarded)
            player.discard_pile.extend(to_be_discarded)

class Vault(ActionCard):
    name = _("Vault")
    edition = Prosperity
    cost = 5
    desc = _("+2 Cards. Discard any number of Cards. +1 Money per Card discarded. Each other player may discard 2 cards. If he does, he draws a card.")

    def activate_action(self, game, player):
        player.draw_cards(2)
        cards = yield SelectHandCards(game, player, count_lower=0, count_upper=None,
                msg=_("Which cards do you want to discard?"))
        # discard cards
        if cards is not None:
            for card in cards:
                card.discard(player)
            player.virtual_money += len(cards)
        for other_player in game.following_players(player):
            cards = yield SelectHandCards(game, other_player, count_lower=0, count_upper=2,
                    msg=_("%s played Vault. Which cards do you want to discard?", (player.name, )))
            if cards is not None:
                for card in cards:
                    card.discard(other_player)
                for info_player in game.participants:
                    if info_player is not other_player:
                        # TODO: info players may only see one of the discarded cards
                        yield InfoRequest(game, info_player,
                                _("%s discards these cards:", (other_player.name, )), cards)
                if len(cards)==2:
                    other_player.draw_cards(1)

class RoyalSeal(TreasureCard):
    name = _("Royal Seal")
    edition = Prosperity
    cost = 5
    worth = 2
    desc = _("While this card is in play, when you gain a card, you may put that card on top of your deck.")
    implemented=False

    def activate_action(self, game, player):
        pass

class CountingHouse(ActionCard):
    name = _("Counting House")
    edition = Prosperity
    cost = 5
    desc = _("Look through your discard pile, reveal any number of Copper cards from it and put them into your hand.")
    implemented=False

    def activate_action(self, game, player):
        pass

class Mint(ActionCard):
    name = _("Mint")
    edition = Prosperity
    cost = 5
    desc = _("You may reveal a Treasure card from your hand. Gain a copy of it.| When you buy this, trash all Treasures you have in play.")
    implemented=False

    def activate_action(self, game, player):
        pass

class Mountebank(AttackCard):
    name = _("Mountebank")
    edition = Prosperity
    cost = 5
    desc = _("+2 Money. Each other player may discard a Curse. If he doesn't, he gains a Curse and a Copper.")

    def activate_action(self, game, player):
        player.virtual_money += 2
        for other_player in game.following_players(player):
            try:
                handle_defense(self, game, other_player)
            except Defended:
                continue
            original_hand = other_player.hand[:]
            curse_discarded = False
            new_cards = []
            for card in original_hand:
                if isinstance(card, CurseCard):
                    for info_player in game.participants:
                         yield InfoRequest(game, info_player,
                                _("%(playername)s discards a curse:",
                                {"playername": player.name}),
                                [card])
                    card.discard(other_player)
                    curse_discarded = True
                    break
            if not curse_discarded:
                with fetch_card_from_supply(game, Curse) as new_card:
                    new_cards.append(new_card)
                with fetch_card_from_supply(game, Copper) as new_card:
                    new_cards.append(new_card)
                for info_player in game.participants:
                     yield InfoRequest(game, info_player,
                             _("%(playername)s played Mountebank: %(player2name)s's gains:",
                            {"playername": player.name, "player2name": other_player.name}),
                            new_cards)
                for val in game.check_empty_pile("Curse"):
                    yield val
                other_player.discard_pile.extend(new_cards)



class Contraband(TreasureCard):
    name = _("Contraband")
    edition = Prosperity
    cost = 5
    worth = 3
    desc = _("+1 Buy. When you play this, the player to your left names a card. You can't buy this card this turn.")
    implemented=False

    def activate_action(self, game, player):
        player.remaining_deals += 1
        card_cls = yield SelectCard(game, player.left(game), card_classes=game.card_classes,
                   msg=_("Select a card that %(playername)s shouldn't buy.",  {"playername": player.name}), show_supply_count=True)
        for info_player in game.participants:
            yield InfoRequest(game, info_player, _("%(player2name)s does not allow %(player2name)s's to buy:",
                            {"playername": player.name, "player2name": player.left(game).name}), [card_cls])

class City(ActionCard):
    name = _("City")
    edition = Prosperity
    cost = 5
    desc = _("+1 Card, +2 Actions. If there are one or more empty Supply piles, +1 Card. If there are two or more, +1 Money and +1 Buy")

    def activate_action(self, game, player):
        if game.empty_pile_count == 0:
            player.remaining_actions += 2
            player.draw_cards(1)
        if game.empty_pile_count == 1:
            player.remaining_actions += 2
            player.draw_cards(2)
        if game.empty_pile_count >= 2:
            player.remaining_actions += 2
            player.draw_cards(2)
            player.remaining_deals += 1
            player.virtual_money += 1

class GrandMarket(ActionCard):
    name = _("Grand Market")
    edition = Prosperity
    cost = 6
    desc = _("+1 Card, +1 Action, +1 Buy.| You can't buy this if you have any Copper in play.")
    implemented=False

    def activate_action(self, game, player):
        player.remaining_actions += 1
        player.remaining_deals += 1
        player.draw_cards(1)

class Goons(ActionCard):
    name = _("Goons")
    edition = Prosperity
    cost = 6
    desc = _("+1 Buy, +2 Money. Each other player discards down to 3 cards in hand.| While this is in play, when you buy a card, +1 token.")

    def activate_action(self, game, player):
        player.remaining_deals += 1
        player.virtual_money += 2
        for other_player in game.following_players(player):
            try:
                handle_defense(self, game, other_player)
            except Defended:
                continue
            count = len(other_player.hand) - 3
            if count <= 0:
                continue
            cards = yield SelectHandCards(game, other_player, count_lower=count, count_upper=count,
                    msg=_("%s played Goons. Which cards do you want to discard?", (player.name, )))
            for card in cards:
                card.discard(other_player)
            for info_player in game.following_participants(player):
                # TODO: info players may only see one of the discarded cards
                yield InfoRequest(game, info_player,
                        _("%s discards these cards:", (other_player.name, )), cards)

    @classmethod
    def on_buy_card(cls, game, player, card):
        for c in player.aux_cards:
            if isinstance(c, Goons):
                player.tokens += 1


class Hoard(TreasureCard):
    name = _("Hoard")
    edition = Prosperity
    cost = 6
    worth = 2
    desc = _("While this is in play, when you buy a Victory card, gain a Gold.")
    implemented=False

class Expand(ActionCard):
    name = _("Expand")
    edition = Prosperity
    cost = 7
    desc = _("Trash a card from you hand. Gain a card costing up to 3 money more than the trashed card.")

    def activate_action(self, game, player):
        if not player.hand:
            return
        cards = yield SelectHandCards(game, player,
                    count_lower=0, count_upper=1,
                    msg=_("Select a card you want to trash."))
        if cards:
            card = cards[0]
            card_cls = yield SelectCard(game, player, card_classes=[c for c in
                game.card_classes.itervalues()
                if c.cost <= card.cost + 3 and game.supply.get(c.__name__)
                and c.potioncost == card.potioncost],
                msg=_("Select a card that you want to have."), show_supply_count=True)
            card.trash(game, player)
            new_card = game.supply[card_cls.__name__].pop()
            player.discard_pile.append(new_card)

            for info_player in game.following_participants(player):
                yield InfoRequest(game, info_player,
                        _("%s trashes:", (player.name, )), [card])
                yield InfoRequest(game, info_player,
                        _("%s gains:", (player.name, )), [new_card])
            for val in game.check_empty_pile(card_cls.__name__):
                yield val

class Bank(TreasureCard):
    name = _("Bank")
    edition = Prosperity
    cost = 6
    desc = _("When you play this, it's worth 1 Money per Treasure card you have in play (counting this).")

    def get_worth(self, player):
        worth = 0
        for card in player.aux_cards:
            if isinstance(card, TreasureCard):
                worth +=1
        return worth

class KingsCourt(ActionCard):
    name = _("King's Court")
    edition = Prosperity
    cost = 7
    desc = _("You may choose an Action card in your hand. You may play it three times.")

    def activate_action(self, game, player):
        if not [c for c in player.hand if isinstance(c, ActionCard)]:
            return
        action_cards = (yield SelectActionCard(self, player,
            _("Which action card do you want to play on the kings court? (%i actions left)",
               (player.remaining_actions, ))))
        if action_cards:
            card = action_cards[0]
            player.hand.remove(card)
            gen = game.play_action_card(player, card)
            generator_forward(gen)
            if card.trash_after_playing and not card.throne_room_duplicates:
                game.trash_pile.append(card)
            else:
                player.aux_cards.append(card)
                gen = game.play_action_card(player, card)
                generator_forward(gen)
                if card.trash_after_playing and not card.throne_room_duplicates:
                    game.trash_pile.append(card)
                else:
                    player.aux_cards.append(card)
                    gen = game.play_action_card(player, card)
                    generator_forward(gen)
                    if card.trash_after_playing:
                        player.aux_cards.remove(card)
                        game.trash_pile.append(card)

class Forge(ActionCard):
    name = _("Forge")
    edition = Prosperity
    cost = 7
    desc = _("Trash any number of cards from your hand. Gain a card with cost exactly equal to the the total cost in coins of the trashed cards.")

    def activate_action(self, game, player):
        Forge_money = 0
        if player.hand:
            cards = yield SelectHandCards(game, player,
                    msg=_("Which cards do you want to trash?"))
        # trash cards
        if cards:
            for card in cards:
                Forge_money += card.cost
                card.trash(game, player)
        card_cls = yield SelectCard(game, player, card_classes=[c for c in
            game.card_classes.itervalues()
            if c.cost == Forge_money and game.supply.get(c.__name__)
            and c.potioncost == 0],
            msg=_("Select a card that you want to have."), show_supply_count=True)
        if card_cls is not None:
            new_card = game.supply[card_cls.__name__].pop()
            player.discard_pile.append(new_card)
            new_cards = [new_card]
        else:
            new_cards = []

        for info_player in game.following_participants(player):
            yield InfoRequest(game, info_player,
                    _("%s trashes:", (player.name, )), cards or [])
            yield InfoRequest(game, info_player,
                    _("%s gains:", (player.name, )), new_cards)
        if card_cls:
            for val in game.check_empty_pile(card_cls.__name__):
                yield val

class Peddler(ActionCard):
    name = _("Peddler")
    edition = Prosperity
    cost = 8
    desc = _("+1 Card, +1 Action, +1 Money. During the Buy phase, this costs 2 Money less per Action card you have in play, but no less than 0.")

    def activate_action(self, game, player):
        player.remaining_actions += 1
        player.draw_cards(1)
        player.virtual_money += 1

    @classmethod
    def get_cost(self, game=None, player=None):
        if player is None:
            return 8
        return max(0, 8 - 2 * len(c for c in player.aux_cards if isinstance(c, ActionCard)))


from domination.cards.base import \
    Cellar, CouncilRoom, Mine, Adventurer, Spy, Village, Chancellor, Moneylender, Laboratory, Bureaucrat, Moat, Gardens, Chancellor

from domination.cards.intrigue import \
    Upgrade, ShantyTown, Baron, Pawn, Harem, MiningVillage, Bridge, GreatHall, Torturer, Bridge, GreatHall, Coppersmith, Tribute, Swindler, WishingWell

card_sets = [
    CardSet(u" Anfänger [P]",
        [Venture, WorkersVillage, Expand, Bank, Monument, Rabble, Goons, RoyalSeal, CountingHouse, Watchtower]),
    CardSet(u" Freundliche Interaktion [P]",
        [WorkersVillage, Bishop, Vault, TradeRoute, Peddler, Hoard, RoyalSeal, Forge, Contraband, City]),
    CardSet(u" Grosse Aktionen [P]",
        [Expand, Rabble, Vault, GrandMarket, KingsCourt, Loan, Mint, City, Quarry, Talisman]),
    CardSet(u" Haufenweise Geld [P+B]",
        [Venture, Bank, GrandMarket, RoyalSeal, Mint, Adventurer, Moneylender, Laboratory, Mine, Spy]),
    CardSet(u" Die Armee des Königs [P+B]",
        [Expand, Rabble, Vault, Pawn, KingsCourt, Bureaucrat, Moat, Village, CouncilRoom, Spy]),
    CardSet(u" Ein gutes Leben [P+B]",
        [Monument, Hoard, CountingHouse, Mountebank, Contraband, Bureaucrat, Village, Gardens, Chancellor, Cellar]),
    CardSet(u" Pfade zum Sieg [P+I]",
        [Bishop, Monument, Goons, Peddler, CountingHouse, Upgrade, ShantyTown, Baron, Pawn, Harem]),
    CardSet(u" All along the Watchtowe [P+I]",
        [Vault, TradeRoute, Hoard, Talisman, Watchtower, MiningVillage, Bridge, GreatHall, Pawn, Torturer]),
    CardSet(u" Glücksritter [P+I]",
        [Expand, Bank, Vault, KingsCourt, Forge, Bridge, Coppersmith, Tribute, Swindler, WishingWell]),
]
