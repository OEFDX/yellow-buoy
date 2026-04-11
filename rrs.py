"""
Library for scoring sailing events.
"""


def score(series):
    result = Series(series.get('scoring-system'))

    result.add_races(series['races'])
    result.score_boats()
    result.rank_boats()

    return {'races': result.races, 'boats': result.boats}


class Series:
    def __init__(self, scoring_system=None):
        self.scoring_system = scoring_system if scoring_system else {}
        self.boats = {}
        self.races = []

    def add_races(self, races):
        """Add races and give unseen boats DNC scores in other races."""
        self._add_unseen_boats(races)

        for race in races:
            race_result = {'scores': {}}
            self.races.append(race_result)

            for boat in self.boats:
                boat_race_score = race['scores'].get(boat, 'DNC')

                # A score has:
                #   -   a number of points
                #   -   an optional code
                #   -   a flag that says whether it should be included
                #       in scoring.
                #
                # All races are initially marked as included,
                # but may be excluded when the series is scored.

                try:
                    code = ''
                    # TODO: should be to nearest 0.1 points
                    points = int(boat_race_score)
                except ValueError:
                    code = boat_race_score
                    if code == 'DNC':
                        points = self.dnc_score()
                    else:
                        points = self.dnf_score(race)

                race_result['scores'][boat] = {
                    'code': code,
                    'score': points,
                    'include': True,
                }

    def dnc_score(self):
        return len(self.boats) + 1

    def dnf_score(self, race):
        if self.scoring_system.get('rrs-a5.3'):
            return len(race['scores']) + 1

        return self.dnc_score()

    def score_boats(self):
        """Score the series."""
        for boat in self.boats:
            self._exclude_worst_scores(boat)
            self._calculate_series_scores(boat)

    def rank_boats(self):
        """Rank the boats, breaking any ties in scores according to RRS A8."""
        ranked_boats = sorted(
            self.boats,
            key=self._ranking_key
        )

        for rank, boat in enumerate(ranked_boats, start=1):
            self.boats[boat]['rank'] = rank

    # TODO: make this ranking lazy
    #       so the best result key
    #       and the count-back key
    #       are only computed if there is a tie.
    def _ranking_key(self, boat):
        score_key = self.boats[boat]['score']

        # This implements RRS A8.1
        # (tie breaking by best results)
        best_result_key = sorted(
            race['scores'][boat]['score']
            for race in self.races
            if race['scores'][boat]['include']
        )

        # This implements RRS A8.2
        # (tie breaking by count-back)
        countback_key = [
            race['scores'][boat]['score']
            for race in self.races[::-1]
            # N.B. the rules say excluded scores are _included_ here.
        ]

        return (score_key, best_result_key, countback_key)

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

    test_paths = [
        # "docs/index.md",
        "docs/rrs-appendix-a.md",
        "docs/rrs-appendix-a-options.md",
    ]

    for path in test_paths:
        doctest.testfile(
            path,
            optionflags=(
                doctest.NORMALIZE_WHITESPACE
                | doctest.ELLIPSIS
                | doctest.REPORT_CDIFF
            ),
        )
