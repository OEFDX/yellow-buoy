"""
Library for scoring sailing events.

In a sailing event,
the competition consists Boats sailing a Series of Races.
The sailing instructions may change how scoring is done,
so the scoring system is a property of the series.
The default scoring system is RRS Appendix A ('RRS-A')

>>> series = {
...     'races': [],
...     'options': {
...         'scoring-system': 'RRS-A'    # This is the default.
...     }
... }

The scoring system has three distinctive features:

-   the lowest score wins

-   scoring codes (other racing sports have these
    but sailing has special ones of its own)

-   discards (also not unique to sailing, but uncommon)

Discards mean that in a series with one race and one boat 'A':

>>> series = {
...     'races': [
...         {'scores': {'A': 1}}
...     ]
... }

When the scores are calculated, the worst score is excluded
*even if there was only one race*.

>>> results = score(series)
>>> results['races'][0]['scores']['A']
{'score': 1, 'include': False}
>>> results['boats']['A']['score']
0

If a boat has two identical worst scores, the first one is excluded.

>>> results = score({
...     'races': [
...         {'scores': {'A': 1}},
...         {'scores': {'A': 1}},
...     ]
... })
>>> [r['scores']['A']['include'] for r in results['races']]
[False, True]


In a more realistic series, with two boats,
when the scores are calculated,
the boat with the lowest score also has the best (lowest) rank.

>>> series = {'races': [{'scores': {'A': 1, 'B': 2}}]}
>>> results = score(series)
>>> {results['boats'][boat]['rank']: boat for boat in results['boats']}
{1: 'A', 2: 'B'}

"""


def score(series):
    result = Series()

    result.add_races(series['races'])
    result.score_boats()
    result.rank_boats()

    return {'races': result.races, 'boats': result.boats}


class Series:
    def __init__(self):
        self.boats = {}
        self.races = []

    def add_races(self, races):
        """Add races and give unseen boats DNC scores in other races."""
        self._add_unseen_boats(races)

        for race in races:
            race_result = {'scores': {}}
            self.races.append(race_result)

            for boat in self.boats:
                boat_race_score = race['scores'].get(boat, self.dnc_score())
                # A score has a number of points
                # and a flag that says whether it should be included in scoring.
                # All races are included for now,
                # but this will change later.
                race_result['scores'][boat] = {
                    'score': boat_race_score,
                    'include': True,
                }

    def dnc_score(self):
        return len(self.boats) + 1

    def score_boats(self):
        """Score the series."""
        for boat in self.boats:
            self._exclude_worst_scores(boat)
            self._calculate_series_scores(boat)

    def rank_boats(self):
        """Rank the boats, breaking any ties in scores according to RRS A."""
        ranked_boats = sorted(
            self.boats,
            key=lambda boat: self.boats[boat]['score']
        )

        for rank, boat in enumerate(ranked_boats, start=1):
            self.boats[boat]['rank'] = rank

    def _add_unseen_boats(self, races):
        for race in races:
            for boat in race['scores']:
                self.boats.setdefault(boat, {})

    def _exclude_worst_scores(self, boat):
        """Apply the RRS Appendix A exclusion rule.

        Appendix A states that the worst result is excluded
        unless the SIs make some other provision.
        """
        scores = [race['scores'][boat] for race in self.races]

        # The max() function returns the earliest of any equal maxima.
        # This is consistent with the RRS, which says the earliest of
        # equal worst scores shall be discarded.
        worst_score = max(scores, key=lambda s: s['score'])
        worst_score['include'] = False

    def _calculate_series_scores(self, boat):
        self.boats[boat]['score'] = sum(
            race['scores'][boat]['score']
            for race in self.races
            if race['scores'][boat]['include']
        )


if __name__ == "__main__":
    import doctest
    doctest.testmod(
        optionflags=(
            doctest.NORMALIZE_WHITESPACE
            | doctest.ELLIPSIS
            | doctest.REPORT_CDIFF
        ),
    )
