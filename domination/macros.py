from karnickel import macro

@macro
def handle_defense(self, game, player):
    gen = self.defends_check(game, player)
    item = None
    while True:
        try:
            item = (yield gen.send(item))
        except StopIteration:
            break

