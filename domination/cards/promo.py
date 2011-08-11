from domination.cards import TreasureCard, VictoryCard, CurseCard, ActionCard, \
     AttackCard, ReactionCard, CardSet, Promo
from domination.gameengine import InfoRequest, SelectCard, SelectHandCards, \
     YesNoQuestion, Defended, SelectActionCard
from domination.tools import _
from domination.macros.__macros__ import handle_defense, generator_forward


class BlackMarket(ActionCard):
    name = _("Black Market")
    edition = Promo
    implemented = False #FIXME not implemented completely
    cost = 3
    desc = _("Reveal the top 3 cards of the Black Market deck. You may buy one of them immediately. Put the unbought cards on the bottom of the Black Market Deck in any order.")

    def activate_action(self, game, player):
        player.virtual_money += 2


class Envoy(ActionCard):
    name = _("Envoy")
    edition = Promo
    implemented = False #FIXME not implemented completely
    cost = 4
    desc = _("Reveal the top 5 cards of your deck. The player to your left chooses one for you to discard. Draw the rest.")

    def activate_action(self, game, player):
        player.draw_cards(5)
        drawn, player.hand = player.hand[-5:], player.hand[:-5]
        for info_player in game.participants:
            yield InfoRequest(game, info_player, _("%s reveals the top 5 cards of his deck:", (player.name, )), drawn)
        card_classes = [type(c) for c in drawn]
        card_cls = yield SelectCard(game, player.left(game), card_classes=card_classes,
                   msg=_("Select a card that %(playername)s should discard.",  {"playername": player.name}), show_supply_count=False)
        for info_player in game.participants:
            yield InfoRequest(game, info_player, _("%(player2name)s does not allow %(player2name)s's to buy:",
                            {"playername": player.name, "player2name": player.left(game).name}), [card_cls])


class Stash(TreasureCard):
    name = _("Stash")
    edition = Promo
    implemented = False #FIXME not implemented completely
    cost = 5
    worth = 2
    desc = _("When you shuffle, you may put this anywhere in your deck.")

