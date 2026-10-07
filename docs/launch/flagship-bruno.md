# I tried to find Bruno Fernandes's replacement. The data said something more interesting.

*Draft · flagship piece · ~900 words · link at the end, not the start*

---

Every summer someone asks the same question about a creative midfielder: who's the next one? I wanted to answer it properly for one player — Bruno Fernandes — and see how far data could take the question.

**1. I built the dataset first.** Every player in every match of the Premier League, La Liga, Serie A, the Bundesliga and Ligue 1 from 2015/16 to 2024/25: 18,011 matches, 8,348 players, 525,328 player-matches. Expected goals and assists, shots, key passes, involvement in build-up.

**2. Then I took the context out.** Raw numbers carry their circumstances with them. The same player produces about 27% more xG per minute at home than away, and about 14% less for every step up in opponent strength. And when I looked for players who are reliably better at home, or reliably better in big games, the answer was none — 0 of 4,665 players had a reliable personal home edge; 0 of 23,022 player-level estimates showed real "big-game" resistance. Context is shared by everyone; it isn't a player trait.

So before comparing anyone, every profile was adjusted for opponents, venue and league — nine attacking metrics, compared only with players in the same data-derived role.

**3. Then I looked for Bruno in Serie A.** The robust matches — the ones that held up across different time windows and distance measures — were Lazar Samardžić, Paulo Dybala and Samuel Chukwueze.

**4. But none of them is Bruno.** Bruno's chance creation sits 3.6 standard deviations above the average attacking midfielder. The highest in Serie A's pool was 1.9, and Dybala 1.8. Every shortlisted player shares part of his profile — shooting volume from distance, involvement in build-up — at a lower creative level. Statistically, there is no like-for-like Bruno in Serie A.

**5. So I asked a harder question: does similarity predict anything?** If a player looks like players who succeeded after a move, will he succeed too? I tested it on hundreds of real league moves.

**6. It didn't.** A forecast built from a player's most similar comparables did no better than "he'll do what he did last season". Adding similarity to a model of the player's own history changed its error by nothing detectable.

**7. Player history did better.** A model of the player's own three-season output, age, both clubs and both leagues — fixed before its test seasons were opened and scored once on 142 unseen moves — cut the typical error from 0.129 to 0.096 xG + xA per 90.

**The lesson:** similarity is a good way to *find* candidates. It is not a way to *forecast* them.

**8. Then I tested it on a real window.** Standing at 1 June 2024 with only what was known then, the model predicted Joshua Zirkzee at 0.46 xG + xA per 90 at Manchester United; he produced 0.47. It also missed Manuel Ugarte badly (0.02 predicted, 0.14 actual) — on a weakness the research had already documented, and on a player bought for defensive work this data can't see.

---

The whole system is interactive: search any player's closest profiles in any of the five leagues, run the transfer model, and see whether the findings still hold on this season's matches.

→ **Bruno → Serie A:** https://iyush.dev/football/tools/similarity?player=bruno-fernandes&league=serie-a&seasons=3
→ **The research:** https://iyush.dev/football

*Observational data; effects are associations within matched comparisons. Attacking output only — no defending, injuries, fees or fit.*
