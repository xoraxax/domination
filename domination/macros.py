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

@macro
def generator_forward(gen):
    if gen is not None:
        reply = None
        # generic generator forwarding pattern
        while True:
            try:
                reply = (yield gen.send(reply))
            except StopIteration:
                break

@macro
def generator_forward_ex(gen, excs):
    if gen is not None:
        reply = None
        # generic generator forwarding pattern
        while True:
            try:
                reply = (yield gen.send(reply))
                if isinstance(reply, tuple(excs)):
                    reply = (yield gen.throw(reply))
            except StopIteration:
                break

@macro
def fetch_card_from_supply(game, t):
    cards = game.supply[t.__name__]
    if cards:
        new_card = cards.pop()
        for val in game.check_empty_pile(t.__name__):
            yield val
        __body__
