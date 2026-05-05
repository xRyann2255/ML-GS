# This code can do one or multiple simulations of the
# Glosten and Milgrom (1985) model.  If multiple
# simulations are run, the plot shows the average bid
# and ask.
#
# (c) Copyright Dale W.R. Rosenthal, 29 September 2008
# This software may be used in an academic context with
# attribution. It may not be used otherwise nor distributed
# without express permission. dale.rosenthal@gmail.com

numsims <- 1
numsteps <- 50
v.max <- 2
v.min <- 1
mu <- 0.3
delta <- 0.5

asks <- numeric(numsteps+1)
bids <- numeric(numsteps+1)
for (i in 1:numsims) {
  informeds <- c(0, rbinom(numsteps, 1, mu))
  buys <- c(0, rbinom(numsteps, 1, 1/2))
  # assume v = v.max; hence informeds only buy
  buys[informeds == 1] <- 1
  n.buys <- cumsum(buys)
  n.sells <- 0:numsteps - n.buys
  askz <- (v.min*delta*(1-mu)**(n.buys+1)*(1+mu)**n.sells +
           v.max*(1-delta)*(1+mu)**(n.buys+1)*(1-mu)**n.sells)/
             (delta*(1-mu)**(n.buys+1)*(1+mu)**n.sells +
              (1-delta)*(1+mu)**(n.buys+1)*(1-mu)**n.sells)
  bidz <- (v.min*delta*(1-mu)**n.buys*(1+mu)**(n.sells+1) +
           v.max*(1-delta)*(1+mu)**n.buys*(1-mu)**(n.sells+1))/
             (delta*(1-mu)**n.buys*(1+mu)**(n.sells+1) +
              (1-delta)*(1+mu)**n.buys*(1-mu)**(n.sells+1))
  asks <- asks + askz
  bids <- bids + bidz
}
asks <- asks/numsims
bids <- bids/numsims
spread <- asks - bids

plot(0:numsteps, asks, xlim=c(0, numsteps), ylim=c(1.25, 2.0),
     xlab="Time", ylab="Price", type='l')
lines(0:numsteps, bids)
# only print this for a single-run plot
points(1:numsteps-0.5, rep(1.6, numsteps),
       pch=c("S", "B")[buys[2:(numsteps+1)]+1])
