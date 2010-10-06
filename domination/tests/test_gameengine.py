from random import SystemRandom
from werkzeug import abort # WTH fails the import of this file without this import?
from domination.gameengine import Player, DominationGame, InfoRequest, EndOfGameException, card_sets, Checkpoint
from domination.cards import CardTypeRegistry
from domination.cards.base import ThroneRoom, Smithy
from domination.cards.intrigue import Baron


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
        gen = game.play_game(False)
        record = []
        reply = None
        while True:
            try:
                req = gen.send(reply)
            except EndOfGameException:
                print game.end_of_game_reason
                break
            if isinstance(req, InfoRequest):
                iter(req.cards)
                continue
            if isinstance(req, Checkpoint):
                continue
            assert len(req.player.total_cards) >= 5, "\n".join(record)
            assert game.round < 100, "\n".join(record)
            reply = req.choose_wisely()
            record.append("%s answered %s with %s" % (req.player, req.msg, reply))
            record.append("%s has %i cards left" % (req.player, len(req.player.total_cards)))
            #print "\n".join(record); record = []
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

    def test_alchemy(self):
        from domination.cards.alchemy import Potion, Vineyard, Alchemist, Apothecary,\
                Apprentice, Familiar, Golem, Herbalist, PhilosophersStone, Possession,\
                ScryingPool, Transmute, University

        def sample_alchemy():
            return random.sample([Vineyard, Alchemist, Apothecary,
                Apprentice, Familiar, Golem, Herbalist, PhilosophersStone, Possession,
                ScryingPool, Transmute, University], 10)

        for _ in xrange(2**8):
            yield self.do_test_run, sample_alchemy()

    def test_throne_room(self):
        for _ in xrange(2**6):
            yield self.do_test_run, [ThroneRoom] * 9 + [Smithy]

    def test_baron(self):
        for _ in xrange(2**6):
            yield self.do_test_run, [Baron] * 9 + [Smithy]
