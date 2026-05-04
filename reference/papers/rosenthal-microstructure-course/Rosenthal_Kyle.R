# This code does a single simulation of the multi-period
# Kyle (1985) model. Using Cardano's formula provides a
# significant speed gain over using a root-finding optimizer.
#
# (c) Copyright Dale W.R. Rosenthal, 7 October 2008.
# This software may be used in an academic context with
# attribution. It may not be used otherwise nor distributed
# without express permission. dale.rosenthal@gmail.com

# Cardano's formula for three real roots (returned in sorted order)
cardano <- function(a,b,c,d) {
  p <- b^2/(3*a^2) - c/a
  q <- 2*b^3/(27*a^3) - b*c/(3*a^2) + d/a
  Q <- as.complex(p/3)
  R <- as.complex(q/2)
  theta <- acos(R/sqrt(Q^3))
  #D <- as.complex((p/3)^3 + (q/2)^2)
  #u <- (-q/2 + sqrt(D))^(1/3)
  #v <- (-q/2 - sqrt(D))^(1/3)
  #root.1 <- as.numeric(u+v)
  #root.2 <- as.numeric(-(u+v)/2 + (u-v)*sqrt(3)*1i/2)
  #root.3 <- as.numeric(-(u+v)/2 - (u-v)*sqrt(3)*1i/2)
  root.1 <- as.numeric(-2*sqrt(Q)*cos(theta/3) - b/(3*a))
  root.2 <- as.numeric(-2*sqrt(Q)*cos((theta+2*pi)/3) - b/(3*a))
  root.3 <- as.numeric(-2*sqrt(Q)*cos((theta-2*pi)/3) - b/(3*a))
  roots <- c(root.1, root.2, root.3)
  return(sort(roots))
}

numsteps <- 50
sigma.u <- .5
Sigma.0 <- 0.4
kyle.sim <- function(Sigma.N) {
  if (Sigma.N <= 0) {
    return(list(sqdiff=99e99))
  }
  delta.t <- 1/numsteps  # could also be vector if irregularly-spaced trades
  Sigma  <- numeric(numsteps+1)
  alpha  <- numeric(numsteps+1)
  delta  <- numeric(numsteps+1)
  lambda <- numeric(numsteps+1)
  beta   <- numeric(numsteps+1)

  Sigma[numsteps+1] <- Sigma.N
  alpha[numsteps+1] <- 0
  delta[numsteps+1] <- 0
  lambda[numsteps+1] <- sqrt(Sigma[numsteps+1])/(sigma.u*sqrt(2*delta.t))

  for (i in numsteps:1) {
    beta[i+1] <- (1-2*alpha[i+1]*lambda[i+1])/
      (2*lambda[i+1]*(1-alpha[i+1]*lambda[i+1])*delta.t)
    Sigma[i] <- Sigma[i+1]/(1-beta[i+1]*lambda[i+1]*delta.t)
    alpha[i] <- 1/(4*lambda[i+1]*(1-alpha[i+1]*lambda[i+1]))
    delta[i] <- delta[i+1] + alpha[i+1]*lambda[i+1]^2*sigma.u^2*delta.t
    a <- alpha[i]*sigma.u^2*delta.t/Sigma[i]
    b <- -sigma.u^2*delta.t/Sigma[i]
    c <- -alpha[i]
    d <- 1/2
    # solve lambda cubic -- which has three real roots
    lambda[i] <- (cardano(a, b, c, d))[2]  # pick the middle root
  }
  beta[1] <- (1-2*alpha[1]*lambda[1])/
    (2*lambda[1]*(1-alpha[1]*lambda[1])*delta.t)
  return(list(sqdiff=(Sigma[1] - Sigma.0)^2,
              Sigma=Sigma,alpha=alpha,delta=delta,
              lambda=lambda,beta=beta))
}

# the wrapper function stores the various vectors we want
# (Sigma, delta, alpha, lambda, beta) when we move closer
# to the target Sigma.0 -- while passing the squared
# divergence back to the optimizer.  Devious!
kyle.sim.wrapper <- function(...) {
  parent.env(environment())
  results <- kyle.sim(...)
  if (results$sqdiff < minsqdiff) {
    assign("minsqdiff", results$sqdiff, inherits=TRUE)
    assign("Sigma",  results$Sigma, inherits=TRUE)
    assign("alpha",  results$alpha, inherits=TRUE)
    assign("delta",  results$delta, inherits=TRUE)
    assign("lambda", results$lambda, inherits=TRUE)
    assign("beta",   results$beta, inherits=TRUE)
  }
  return(results$sqdiff)
}

minsqdiff <- 99e99
Sigma.N.start <- 0.3
optim.out <- optim(Sigma.N.start, kyle.sim.wrapper,, method="BFGS")

delta.p <- numeric(numsteps)
p <- numeric(numsteps+1)
p[1] <- 2
v <- rnorm(1, p[1], Sigma.0)
delta.u <- rnorm(numsteps, 0, sigma.u/sqrt(numsteps))
delta.x <- numeric(numsteps)
for (i in 1:numsteps) {
  delta.x[i] <- beta[i]*(v-p[i])/numsteps
  delta.p[i] <- lambda[i]*(delta.x[i]+delta.u[i])
  p[i+1] <- p[i]+delta.p[i]
}

plot(0:numsteps, Sigma, xlim=c(0, numsteps), xlab="Time",
     ylab="Sigma", type='p')

plot(0:numsteps, lambda, xlim=c(0, numsteps), xlab="Time",
     ylab="lambda", type='p')

plot(0:numsteps, delta, xlim=c(0, numsteps), xlab="Time",
     ylab="delta", type='p')

plot(0:numsteps, alpha, xlim=c(0, numsteps), xlab="Time",
     ylab="alpha", type='p')

plot(0:numsteps, beta, xlim=c(0, numsteps), xlab="Time",
     ylab="beta", type='p')

plot(1:numsteps, delta.u, xlim=c(0, numsteps), xlab="Time",
     ylab="Orders", type='p', pch="u")
points(1:numsteps, delta.x, pch="i")
abline(h=0)

plot(0:numsteps, p, xlab="Time", ylab="Trade Prices",
     xlim=c(0, numsteps), ylim=c(p[1], max(p[numsteps+1],v)),
     type='l')
points(0:numsteps, p, pch=".")
abline(h=v, lty=3)
text(10, v, "True Price")
