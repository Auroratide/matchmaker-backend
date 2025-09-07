# Decision Log

Log of why we made some of the decisions we did. If something major changes, please add a new section with a date and be sure to include the rationale behind the decision.

## Base Architecture

**Date**: 07 Sep 2025

**Coda**: Low-code web builder that greatly accelerates development at the cost of total flexibility. Most of what we need (database, form, triggers) can be accomplished in Coda very quickly, and it's used for many other AISafety.com projects.

**Gemini for Embedding**: The Gems Coda Pack allows integration with Gemini.

**Brevo for Emails**: Allows for email templates, generous 300 emails per day, has a Coda Pack available.

**Pinecone Vector DB**: Mature vector storage solution. Provides lots of things out of the box should we need it, notably ANN search (the matchmaking algorithm runs in O(n^2 log n) for dense graphs, so quite expensive if we eval _every_ edge).

**Digital Ocean**: The matchmaking algorithm is sufficiently complex that we must take it out of Coda. A linux cron job doing python is a good choice for this.

**Python**: Generally AI's preferred ecosystem.
