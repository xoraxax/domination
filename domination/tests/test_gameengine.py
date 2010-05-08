from random import SystemRandom
from domination.gameengine import Player, DominationGame, InfoRequest, EndOfGameException, card_sets
from domination.cards import CardTypeRegistry


random = SystemRandom()

def doesnt_raise(card):
    try:
        card.activate_action(None, None)
    except NotImplementedError:
        return False
    except:
        pass
    return True

class TestRandomRunner(object):
    def test_random_run(self):
        card_classes = random.sample([c for c in
            CardTypeRegistry.card_classes.values() if c.optional
            and doesnt_raise(c())], 10)
        print "Chose ", card_classes
        self.do_test_run(card_classes)

    def test_intrigue_test_run(self):
        card_classes = dict(((x.name, x.card_classes) for x in card_sets))['Intrigue Test']
        card_classes += random.sample([c for c in
            CardTypeRegistry.card_classes.values() if c.optional
            and doesnt_raise(c())], 10 - len(card_classes))
        print "Chose ", card_classes
        self.do_test_run(card_classes)

    def do_test_run(self, card_classes):
        game = DominationGame("test", card_classes)
        game.players.append(Player("CPU0"))
        game.players.append(Player("CPU1"))
        gen = game.play_game()
        record = []
        reply = None
        while True:
            try:
                req = gen.send(reply)
                assert len(req.player.total_cards) >= 5, "\n".join(record)
            except EndOfGameException:
                print game.end_of_game_reason
                break
            if isinstance(req, InfoRequest):
                continue
            reply = req.choose_wisely()
            record.append("%s answered %s with %s" % (req.player, req.msg, reply))
            record.append("%s has %i cards left" % (req.player, len(req.player.total_cards)))
        for player in game.players:
            print player.name + ":", player.points(game)
        if min(player.points(game) for player in game.players) < 15:
            print "\n".join(record)

    def test_multiple_runs(self):
        for _ in xrange(2**8):
            yield self.test_random_run

    def test_multiple_runs_intrigue_test(self):
        for _ in xrange(2**8):
            yield self.test_intrigue_test_run

