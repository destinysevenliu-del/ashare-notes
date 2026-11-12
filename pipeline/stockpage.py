"""Individual-stock entrypoint: three decisions, no node scores or score history."""
import stock_decisions

def build(ctx):
    return stock_decisions.build(ctx)
