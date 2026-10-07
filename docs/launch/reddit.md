# Reddit

*Draft. The post must stand on its own — remove the link and it should still be a worthwhile discussion. Post as a text post; link in the last line; reply to every comment in the first two hours. Check each subreddit's self-promotion rules first.*

---

**Title:** I tried to find Bruno Fernandes' replacement using 10 years of European football data — here's what happened

**Body:**

**Why I started.** I wanted to know how much of a player's output is really his, and how much belongs to the context — home or away, the opponent, the league. Then I wanted to use that to answer a real recruitment question: who plays like Bruno Fernandes?

**What I built.** Every player-match in the Premier League, La Liga, Serie A, Bundesliga and Ligue 1 from 2015/16 to 2024/25 — about 525,000 of them. xG, xA, shots, key passes, xGChain, xGBuildup, with opponent strength measured from pre-match betting odds (never from the result).

**What I expected:** some players who are reliably great at home, some "big-game players", and a clean list of Bruno lookalikes.

**What the data showed:**

- Everyone produces more at home — about +27% xG per minute for the *same* player. But 0 of 4,665 players had a reliable *personal* home edge once you account for noise.
- Everyone produces less against strong teams — about −14% xG per step up in opponent strength. 0 of 23,022 player-level estimates showed real "big-game" resistance.

**The Bruno result.** After adjusting every profile for opponents, venue and league, the closest Serie A profiles were Samardžić, Dybala and Chukwueze. But Bruno's chance creation is 3.6 standard deviations above his role average — the best in Serie A was 1.9. There's no like-for-like Bruno there; just players who share parts of his game.

**The surprising failure.** I assumed that if a player resembles players who did well after a move, he'd do well too. Tested on real league moves, that idea added *nothing* to the forecast. A model using only the player's own history, age and the two clubs/leagues did clearly better than "he'll do what he did" (typical error 0.096 vs 0.129 xG+xA per 90 on 142 moves it never saw). Similarity is great for finding candidates and useless for forecasting them.

**One real test:** standing on 1 June 2024, the model had Zirkzee at 0.46 xG+xA/90 at United (he did 0.47) — and badly missed Ugarte (0.02 vs 0.14), whose value is mostly defensive and invisible to this data.

**Caveats:** observational data; attacking output only (no defending, pace, injuries, fees, fit).

**What I'm curious about:** which players would you test first — and what would you want a model like this to see that it currently can't?

Everything is interactive here (you can run any player): https://iyush.dev/football/tools/similarity?player=bruno-fernandes&league=serie-a&seasons=3

---

**Prepared answers**

- *"xG is flawed"* → agreed it's a model; I use it because goals are rare and noisy. Goals are tested too and tell the same story with wider intervals.
- *"Why not defensive stats?"* → the data source doesn't have them; the site says so on every model output.
- *"Code?"* → the site's build is public (github.com/Spyyy004/iyush.dev, `football/README.md`); the research code isn't published yet.
