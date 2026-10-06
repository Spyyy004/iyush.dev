/* Glossary terms (M0 §18). One source for inline popovers and the /football/glossary page.
   short   = Fan-mode one-liner (popover)        analyst = Analyst-mode one-liner (popover)
   plain   = "In plain English"                  why     = "Why we use it"
   example = drawn only from the Final Summary   used    = study numbers
   cat: METRICS | STATISTICS | MODELLING | RECRUITMENT */
window.FB_GLOSSARY = {
  /* ---------------- METRICS ---------------- */
  xg: {
    term: "xG", full: "Expected goals (xG)", cat: "METRICS", used: [1, 2, 3, 4, 5],
    short: "How likely a shot was to become a goal, based on thousands of similar shots.",
    analyst: "Understat's shot-level probability of scoring given location, situation, body part and the action before the shot; summed per player-match.",
    plain: "Every shot gets a score between 0 and 1. A tap-in from a yard out might be 0.8; a hopeful strike from 35 yards might be 0.02. Add them up and you get how many goals a player 'should' have scored from the chances he got.",
    why: "Goals are rare and noisy. xG measures the quality and quantity of chances, which is far more stable from match to match, so it lets small effects (like playing at home) show up.",
    example: "At home, the same player produces about 27% more xG per minute than away (Study 2)."
  },
  xa: {
    term: "xA", full: "Expected assists (xA)", cat: "METRICS", used: [2, 3, 4, 5],
    short: "The xG of the shots a player set up with his passes.",
    analyst: "Sum of the xG of shots directly assisted by the player's pass, regardless of whether the shot was scored.",
    plain: "If you put a teammate through on goal and he misses, you still created a great chance. xA gives you credit for the chance, not the finish.",
    why: "It measures chance creation without depending on a teammate's finishing — the core of a creative player's job.",
    example: "Bruno Fernandes's xA per 90 in 2022/23 was 0.467 raw and 0.460 after adjusting for opponents — the 99.6th percentile (Study 3)."
  },
  npxg: {
    term: "npxG", full: "Non-penalty xG", cat: "METRICS", used: [4],
    short: "xG with penalties removed.",
    analyst: "xG excluding penalty attempts, so penalty-taking duties don't inflate a profile.",
    plain: "Penalties are worth a lot of xG but say little about how a player plays — whoever takes them gets the boost. Removing them makes players comparable.",
    why: "The similarity profile should describe a playing style, not who is on penalties.",
    example: "Non-penalty xG is one of the nine metrics in each Study 4 similarity profile."
  },
  "key-passes": {
    term: "Key passes", full: "Key passes", cat: "METRICS", used: [2, 3, 4],
    short: "Passes that lead directly to a shot.",
    analyst: "Count of passes immediately followed by a teammate's shot (Understat definition).",
    plain: "Any pass that sets up a shot, whether the shot is good or bad.",
    why: "It measures how often a player creates, alongside xA, which measures how good those chances were.",
    example: "Per +1 SD of opponent strength, key passes fall 11.4% (Study 3)."
  },
  xgchain: {
    term: "xGChain", full: "xGChain", cat: "METRICS", used: [4, 5],
    short: "The xG of every attack a player was involved in.",
    analyst: "Total xG of every possession that ends in a shot in which the player was involved, credited in full to each player in the chain.",
    plain: "If you were part of a move that ended in a shot, you share the credit — even if you just played a simple pass early on.",
    why: "It captures involvement in dangerous attacks, not just the last two touches.",
    example: "xGChain is used as an alternative target in Study 5's robustness checks."
  },
  xgbuildup: {
    term: "xGBuildup", full: "xGBuildup", cat: "METRICS", used: [4],
    short: "Like xGChain, but ignoring the shot and the final pass.",
    analyst: "xGChain excluding possessions where the player took the shot or made the key pass — isolates build-up contribution.",
    plain: "Credit for helping build attacks before the final ball.",
    why: "It distinguishes deep playmakers from players who only appear at the end of moves.",
    example: "xGBuildup is part of the 'involvement' group in the Study 4 profile."
  },
  per90: {
    term: "Per 90", full: "Per 90 minutes", cat: "METRICS", used: [2, 3, 4, 5],
    short: "A stat scaled to a full match, so players with different minutes compare fairly.",
    analyst: "Total ÷ minutes × 90. The studies model per-minute rates directly with minutes as exposure.",
    plain: "A sub who plays 30 minutes and a starter who plays 90 can't be compared on totals. Per 90 puts them on the same footing.",
    why: "Every comparison in the series is about rates, not totals.",
    example: "Zirkzee was predicted 0.46 xG + xA per 90 at United; he produced 0.47 (case study)."
  },

  "xg-per-shot": {
    term: "xG / shot", full: "xG per shot", cat: "METRICS", used: [4],
    short: "The average quality of a player's shots.",
    analyst: "Total xG divided by shots: a shot-quality measure, independent of how many shots he takes.",
    plain: "Two strikers can both take three shots a game. One takes them from six yards, the other from thirty. xG per shot tells them apart.",
    why: "Volume and quality are different styles. The similarity profile needs both to tell a poacher from a long-range shooter.",
    example: "One of the nine metrics in the Study 4 similarity profile, alongside shots per 90 and non-penalty xG (Study 4)."
  },
  /* ---------------- STATISTICS ---------------- */
  "home-advantage": {
    term: "Home advantage", full: "Home advantage", cat: "STATISTICS", used: [1, 2],
    short: "How much more a player produces at home than away.",
    analyst: "Home ÷ away ratio of per-minute output for the same player, team and season, from a PPML model with fixed effects.",
    plain: "Compare a player with himself: same club, same season, home games versus away games.",
    why: "It separates what belongs to the venue (and the crowd) from what belongs to the player.",
    example: "+27% xG per minute at home; behind closed doors that fell to about +8–14% (Study 2)."
  },
  "opponent-strength": {
    term: "Opponent strength", full: "Opponent strength (market rating)", cat: "STATISTICS", used: [3, 5],
    short: "How good the opponent was, measured from pre-match betting odds.",
    analyst: "A sequential rating built only from pre-match Pinnacle odds; each match uses only earlier matches. Checked against an xG rating, Elo, opening odds and points per game.",
    plain: "Bookmakers' odds before kick-off are a very good summary of how strong a team is. We turn them into a rating that never peeks at results after the match.",
    why: "Using only pre-match information means the rating can't leak the result it is trying to explain.",
    example: "Per +1 SD of opponent strength, a player's xG falls about 14% (Study 3)."
  },
  sd: {
    term: "SD", full: "Standard deviation (SD)", cat: "STATISTICS", used: [3, 4],
    short: "A standard unit for 'how far from average' something is.",
    analyst: "Standard deviation; effects are reported per +1 SD of the opponent rating, and profiles are z-scored within role.",
    plain: "Roughly, one SD up in opponent strength is the jump from an average side to a clearly strong one.",
    why: "It puts very different scales (odds, xA, shots) on a common footing.",
    example: "Bruno's chance creation is 3.6 SD above his role average; Serie A's best is 1.9 SD (Study 4)."
  },
  "z-score": {
    term: "z-score", full: "z-score", cat: "STATISTICS", used: [4],
    short: "How many SDs a number sits above or below the average.",
    analyst: "(value − role mean) ÷ role SD; computed within role so a full-back is compared with full-backs.",
    plain: "0 means exactly average for the position; +2 means far above it.",
    why: "It lets nine different metrics be combined into one profile without one dominating.",
    example: "Study 4 profiles are z-scored within each of seven data-derived roles."
  },
  interval: {
    term: "95% interval", full: "Confidence interval (95%)", cat: "STATISTICS", used: [1, 2, 3, 5],
    short: "The range the true value plausibly sits in, given the data.",
    analyst: "95% confidence interval from match-clustered standard errors (or bootstrap where stated).",
    plain: "A single number hides uncertainty. The interval shows how sure we are: narrow means confident, wide means 'early days'.",
    why: "Live-season figures early in a season have wide intervals — the interval tells you not to over-read them.",
    example: "Early in a live season the home-edge interval is wide; it narrows as each weekend's matches are added (live tracker)."
  },
  "regression-to-the-mean": {
    term: "Regression to the mean", full: "Regression to the mean", cat: "STATISTICS", used: [2, 3, 5],
    short: "Extreme results tend to be followed by more ordinary ones.",
    analyst: "When a measurement is part signal, part noise, the most extreme observations are disproportionately noise, so they shrink toward the average on re-measurement.",
    plain: "The player who looked brilliant at home last season was partly lucky. Next season the luck evens out and he looks more ordinary.",
    why: "It explains why so many 'special' players disappear when you check them again.",
    example: "The 2015–19 'top 10 home players' were exactly average in 2022–25; correlation between periods 0.018 (Study 2)."
  },
  "signal-noise": {
    term: "Signal vs noise", full: "Signal vs noise", cat: "STATISTICS", used: [2, 3],
    short: "How much of a difference is real, and how much is chance.",
    analyst: "Share of observed between-player variance that is true variance, from calibrated standard errors and DerSimonian–Laird estimates.",
    plain: "If you flip a coin 20 times, some 'players' get 14 heads. That doesn't make them better at flipping. Most individual splits in football are like that.",
    why: "Without separating the two, you crown players for luck.",
    example: "A player's home/away split is only 5–8% signal (Study 2)."
  },
  shrinkage: {
    term: "Shrinkage", full: "Empirical-Bayes shrinkage", cat: "STATISTICS", used: [2, 3],
    short: "Pulling noisy individual estimates toward the average by how unreliable they are.",
    analyst: "Empirical-Bayes posterior means: each player's estimate is weighted against the population mean by its precision relative to the between-player variance (τ²).",
    plain: "A player with a tiny sample gets pulled most of the way back to average; a player with lots of data keeps more of his own number.",
    why: "It gives the fairest single guess for each player and stops small samples dominating rankings.",
    example: "After shrinkage, 0 of 4,665 players have a reliable personal home edge (Study 2)."
  },
  "multiple-testing": {
    term: "Multiple testing", full: "Multiple-testing correction", cat: "STATISTICS", used: [1, 2, 3],
    short: "Adjusting for the fact that testing many things guarantees some flukes.",
    analyst: "Benjamini–Hochberg false-discovery-rate correction plus permutation tests.",
    plain: "Test 20 weather effects and one will look 'significant' by chance. The correction raises the bar to account for that.",
    why: "With thousands of players and metrics, flukes are certain unless corrected.",
    example: "0 of 23,022 player × metric opposition estimates survive the correction (Study 3)."
  },
  "destination-league": {
    term: "Destination league", full: "Why destination league matters", cat: "MODELLING", used: [4],
    short: "Player output varies with league context. The similarity model adjusts for league differences before comparing profiles.",
    analyst: "Profiles are adjusted for opponent, venue and league environment, then compared only with players in the same data-derived role in the chosen league.",
    plain: "Asking for Serie A means: which Serie A players have profiles that resemble this player once league, opponents and venue are taken out?",
    why: "A raw stat line carries its league with it. Comparing across leagues without adjusting would mostly match players by league, not by style.",
    example: "Bruno Fernandes → Serie A: the robust matches are Samardžić, Dybala and Chukwueze (Study 4)."
  },
  "permutation-test": {
    term: "Permutation test", full: "Permutation test", cat: "STATISTICS", used: [1, 2, 3],
    short: "Shuffling the data many times to see how often chance alone produces a result this big.",
    analyst: "Builds the null distribution by randomly permuting labels (e.g. home/away within a player's own matches) and comparing the real statistic against it.",
    plain: "If you shuffle which matches were 'home' and still see the same pattern, the pattern wasn't about home at all.",
    why: "It checks headline effects without leaning on textbook assumptions about the data.",
    example: "Benjamini–Hochberg corrections and permutation tests were run for every headline effect (Final Summary, key methods)."
  },
  placebo: {
    term: "Placebo test", full: "Placebo test", cat: "STATISTICS", used: [1, 2],
    short: "Re-running an analysis on fake dates to check the effect isn't an artefact.",
    analyst: "E.g. shifting the closed-doors dates 2–4 years earlier; a real crowd effect should vanish on the placebo dates.",
    plain: "If 'no fans' really caused the drop, pretending the fans left in a different year should show nothing.",
    why: "It rules out the effect being a quirk of the method or the calendar.",
    example: "Moving the closed-doors period 2–4 years earlier found nothing beyond chance (Study 2)."
  },
  "behind-closed-doors": {
    term: "Behind closed doors", full: "Behind closed doors", cat: "STATISTICS", used: [1, 2, 3],
    short: "Matches played without fans during COVID-19 restrictions.",
    analyst: "Dated per-league crowd-restriction calendars; mostly one season, so per-player crowd estimates are noisy.",
    plain: "A natural experiment: the same teams and players, suddenly without a crowd.",
    why: "It shows how much of home advantage is the crowd itself.",
    example: "Without fans the xG home edge fell from +28% to +12%, then came back to +25% (Study 2)."
  },

  /* ---------------- MODELLING ---------------- */
  "fixed-effects": {
    term: "Fixed effects", full: "Player × team × season fixed effects", cat: "MODELLING", used: [2, 3],
    short: "Comparing each player only with himself.",
    analyst: "A separate intercept for every player × team × season, so identification comes only from within-player variation; errors clustered by match.",
    plain: "Instead of comparing Haaland with a full-back, the model only asks: how did this player, at this club, this season, do in one situation versus another?",
    why: "It removes differences in ability, team and season, leaving the context effect.",
    example: "All headline Study 2 and 3 effects are 'same player, team and season'."
  },
  ppml: {
    term: "PPML", full: "Poisson pseudo-likelihood (PPML)", cat: "MODELLING", used: [2, 3],
    short: "A model for counts and rates that reads results as percentage changes.",
    analyst: "Poisson pseudo-maximum-likelihood on per-minute output with minutes as exposure and high-dimensional fixed effects; robust to non-Poisson variance.",
    plain: "A standard tool for modelling things like 'shots per minute' that handles lots of zeros well.",
    why: "It gives effects as clean percentages (e.g. +27%) and stays valid when the data aren't perfectly Poisson.",
    example: "The +27% home xG edge is a PPML estimate."
  },
  leakage: {
    term: "Leakage", full: "Leakage", cat: "MODELLING", used: [3, 5],
    short: "When a model accidentally uses information it wouldn't have had at the time.",
    analyst: "Any use of post-decision information in features or ratings; tested by scrambling later results and checking nothing earlier changes.",
    plain: "Like predicting a match using the final score. It looks brilliant and is useless.",
    why: "Every prediction here must be one you could actually have made on the day.",
    example: "0 changed ratings in 155,282 leakage checks; Understat's post-match 'forecast' was never used."
  },
  "locked-test": {
    term: "Locked test seasons", full: "Locked test seasons", cat: "MODELLING", used: [5],
    short: "Seasons the model never saw until it was finished — scored once.",
    analyst: "The final model was fixed before 2023/24–2025/26 moves were opened, then scored once on 142 unseen moves.",
    plain: "Like sealing an exam paper until the student has stopped studying.",
    why: "It's the honest test of whether a model works on the future, not just the past.",
    example: "On the locked seasons the final model's error was 0.096 vs 0.129 for 'he'll do what he did' (Study 5)."
  },
  mae: {
    term: "MAE", full: "Mean absolute error (MAE)", cat: "MODELLING", used: [5],
    short: "The average size of a prediction's miss.",
    analyst: "Mean |actual − predicted| in xG + xA per 90 on the test moves.",
    plain: "If MAE is 0.10, predictions are off by about 0.10 xG + xA per 90 on average.",
    why: "It's the headline measure for comparing transfer models.",
    example: "Adding similarity changed the error by 0.000 (Study 5)."
  },
  "r-squared": {
    term: "R²", full: "R² (variance explained)", cat: "MODELLING", used: [5],
    short: "How much of the variation in outcomes a model explains (0 to 1).",
    analyst: "1 − SSE/SST on the locked test moves.",
    plain: "0.76 means the model accounts for about three-quarters of the differences between players' post-move output.",
    why: "It complements MAE by showing how much of the spread is captured.",
    example: "Final model R² 0.76 vs 0.58 for the naive baseline (Study 5)."
  },
  auc: {
    term: "AUC", full: "AUC", cat: "MODELLING", used: [5],
    short: "How well a model ranks players who succeed above those who don't (0.5 = coin flip, 1 = perfect).",
    analyst: "Area under the ROC curve for P(retention ≥ 75%).",
    plain: "Pick one mover who kept his output and one who didn't. AUC is how often the model ranks them the right way round.",
    why: "It measures ranking quality independent of any cut-off.",
    example: "The chance of keeping ≥ 75% ranks players with AUC 0.80 (Study 5)."
  },
  brier: {
    term: "Brier score", full: "Brier score", cat: "MODELLING", used: [5],
    short: "How accurate probability forecasts are (lower is better).",
    analyst: "Mean squared error of predicted probabilities against 0/1 outcomes.",
    plain: "Saying '90%' and being wrong is punished more than saying '60%' and being wrong.",
    why: "It checks the probabilities themselves, not just the ranking.",
    example: "Brier 0.179 vs 0.224 for a same-for-everyone base rate (Study 5)."
  },
  calibration: {
    term: "Calibration", full: "Calibration", cat: "MODELLING", used: [5],
    short: "Whether '70% likely' really happens about 70% of the time.",
    analyst: "Observed frequency vs mean predicted probability in bins; the ≥75% threshold is calibrated at the top, lower thresholds were not and are not used.",
    plain: "A forecaster who says 'rain: 70%' should see rain on about 7 of every 10 such days.",
    why: "An uncalibrated probability looks precise but misleads.",
    example: "The 50% and 60% retention thresholds were not well calibrated, so the site only shows ≥75%."
  },
  "range-80": {
    term: "80% range", full: "80% prediction range", cat: "MODELLING", used: [5],
    short: "Where the player's output should land 4 times out of 5.",
    analyst: "10th–90th percentile of a log-normal predictive distribution with role-group bias and SD from out-of-sample errors.",
    plain: "Not a guarantee: one move in five should land outside it.",
    why: "Individual forecasts are uncertain; the range shows how much.",
    example: "A typical 80% range is ±0.2 xG + xA per 90; strikers 4 of 4 and midfielders 5 of 6 landed inside it in the case study."
  },
  "cosine-similarity": {
    term: "Cosine similarity", full: "Cosine similarity", cat: "MODELLING", used: [4],
    short: "How alike two players' profiles are in shape, ignoring overall size.",
    analyst: "1 − cosine distance between z-scored adjusted profile vectors; checked against Euclidean distance across four profile windows.",
    plain: "Two players who do the same things in the same proportions score high, even if one does more of everything.",
    why: "It finds players with the same style rather than just the same volume.",
    example: "Bruno → Serie A: Samardžić, Dybala and Chukwueze are the robust matches (Study 4)."
  },
  role: {
    term: "Role", full: "Role (data-derived)", cat: "MODELLING", used: [4, 5],
    short: "A position group defined by what players actually produce, not their listed position.",
    analyst: "Ward clustering of Understat's granular positions on per-90 output gives seven roles.",
    plain: "A central attacking midfielder turns out to produce like a wide forward, so they're compared in the same pool.",
    why: "Comparing like with like matters more than the name on the team sheet.",
    example: "Bruno's comparison pool includes inside forwards (Study 4)."
  },
  "profile-window": {
    term: "Profile window", full: "Profile window", cat: "MODELLING", used: [4],
    short: "How much of a player's history the similarity profile uses.",
    analyst: "Windows: last three seasons (w3), two seasons (w2), most recent 2,500 minutes, one season (w1). Single seasons are noisy.",
    plain: "One season can be a fluke; three seasons is a steadier picture.",
    why: "Results that hold across several windows are more trustworthy.",
    example: "Three-season profiles find the same player in the top 9% of the destination pool after a move (Study 4)."
  },
  "self-retrieval": {
    term: "Self-retrieval", full: "Self-retrieval validation", cat: "MODELLING", used: [4],
    short: "Testing similarity by checking it can find the same player again after he moves league.",
    analyst: "Profile before a move is matched against the destination league's role pool after it; the player's own post-move profile should rank near the top.",
    plain: "If the method is any good, it should recognise a player in his new league.",
    why: "It validates the method without relying on anyone's opinion of who is 'similar'.",
    example: "Three-season profiles find the same player in the top 9% after a league move (Study 4)."
  },

  /* ---------------- RECRUITMENT ---------------- */
  retention: {
    term: "Retention", full: "Retention", cat: "RECRUITMENT", used: [5],
    short: "How much of his output a player keeps after a move.",
    analyst: "Output after ÷ output before (xG + xA per 90), also compared with matched stayers to remove regression to the mean.",
    plain: "100% means he produced exactly as much in the new league; 80% means he lost a fifth.",
    why: "It's the direct answer to 'will his game travel?'.",
    example: "Into the Premier League players keep 82%; out of it, 116% (Study 5)."
  },
  stayers: {
    term: "Comparable stayers", full: "Comparable stayers", cat: "RECRUITMENT", used: [5],
    short: "Players who didn't move but had the same role, output and age — the fair comparison.",
    analyst: "Matched control group at the same club and role with similar pre-period output and age, to net out regression to the mean.",
    plain: "Players often move after a great season, and great seasons are usually followed by worse ones anyway. Stayers show what would have happened without the move.",
    why: "Without them, every move looks costly.",
    example: "Movers keep 97% (CI 93–101%) of output relative to comparable stayers (Study 5)."
  },
  "league-ladder": {
    term: "League-difficulty ladder", full: "League-difficulty ladder", cat: "RECRUITMENT", used: [5],
    short: "One ranking of how hard each league is to produce in.",
    analyst: "A single league effect per league explains all 20 move directions; pair-specific effects add nothing (p = 0.91).",
    plain: "Premier League hardest, Serie A and La Liga in the middle, Bundesliga and Ligue 1 easiest. Moving down the ladder boosts numbers; moving up costs them.",
    why: "It means you don't need a separate rule for every pair of leagues.",
    example: "Serie A → Premier League keeps ~80%; Premier League → Serie A ~114% (Study 5)."
  },
  "naive-baseline": {
    term: "Naive baseline", full: "Naive baseline", cat: "RECRUITMENT", used: [5],
    short: "The simplest forecast: 'he'll do what he did before'.",
    analyst: "Post-move output predicted as equal to pre-move output.",
    plain: "Any model worth using has to beat this.",
    why: "It's the honest benchmark for a transfer model.",
    example: "Naive MAE 0.129 vs final model 0.096 on locked seasons (Study 5)."
  },
  comparables: {
    term: "Comparables", full: "Comparable players", cat: "RECRUITMENT", used: [4, 5],
    short: "Statistically similar players, used to find candidates.",
    analyst: "The top-ranked players by context-adjusted profile similarity in a destination league.",
    plain: "A shortlist of players who play like someone you know.",
    why: "Good for discovery — but they don't forecast how a player will do after a move.",
    example: "Comparables alone were worse than the player's own history at predicting post-move output (Study 5)."
  },
  "club-strength": {
    term: "Club strength", full: "Destination club strength", cat: "RECRUITMENT", used: [5],
    short: "How strong the team a player joins is.",
    analyst: "The destination club's market-implied rating at the decision date; promoted clubs get an additional term.",
    plain: "Joining a better team usually means more of the ball and better chances.",
    why: "It matters as much as the league.",
    example: "Weakest third of destination clubs: 79% retention; strongest third: 106% (Study 5)."
  }
};
