My project is building a machine learning system that forcasts realized volatility across multiple horizons - next day, next week and next month.

The core idea is that if you can predict where realzied vol will land relative to where implied vol is pricing it, you know whether the market is overpricing or underpricing risk. That tells you whether to be long or short vol in your hedges, and that edge compounds into real P&L improvement on a delta hedged strategy.

The end goal would be to package this into a tradeable index.

And on the engineering side, I've built an agentic workflow to accelerate the research. An agent keeps an expanding knowledge graph of every experiment I've run and a structured research journal of what worked, what failed, and why. It never re-explores dead ends - it proposes the next experiment based on the accumulated evidence. This project endeavors to build a framework for the evolution of models within STS, providing an AI-paired development flow where Copilot eases the execution experiments to improve and evolve the training of the model.