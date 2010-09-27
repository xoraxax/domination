from karnickel import macro

@macro
def handle_defense(self, game, player):
    from domination.gameengine import Defended
    if player in game.kibitzers:
        raise Defended
    gen = self.defends_check(game, player)
    item = None
    while True:
        try:
            item = (yield gen.send(item))
        except StopIteration:
            break

