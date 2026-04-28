"""
Library for scoring sailing events.
"""

import abc
import decimal
import functools
import sys

# Scores are always rounded to the nearest
# 0.1 points after calculation.
_SCORE_CTX = decimal.Context(rounding=decimal.ROUND_HALF_UP)
_SCORE_PREC = decimal.Decimal('0.1')

def _pt(value):
    """Get a Decimal number of points, quantised to nearest 0.1."""
    return (
        decimal.Decimal(value, context=_SCORE_CTX)
        .quantize(_SCORE_PREC)
    )


def score(series):
    result = Series(series.get('scoring-system', {}))

    result.add_races(series['races'])
    result.score_boats()
    result.rank_boats()

    return {'races': result.races, 'boats': result.boats}


class Series:
    def __init__(self, scoring_system=None):
        self.scoring_system = scoring_system if scoring_system else {}
        self.boats = {}
        self._series_context = SeriesContext(self.boats)

        self.races = []
        self._current_race_context = None

    def add_races(self, races):
        """Add races and give unseen boats DNC scores in other races."""
        self._add_unseen_boats(races)

        for race in races:
            race_result = {'scores': {}}
            self.races.append(race_result)
            self._current_race_context = RaceContext(race_result['scores'])

            for boat in self.boats:
                race_result['scores'][boat] = self.parse_score(
                    race['scores'].get(boat, 'DNC')
                )

    def parse_score(self, text):
        """Parse a score from a string."""
        try:
            return Finish(text)
        except ValueError:
            code = text

        if code == 'DNC':
            # The context for a DNC is always the series.
            return DNC(self._series_context)

        if code == "DNE":
            return DNE(self._current_race_context)

        if code == "DNF":
            return DNF(self._current_race_context)

        if code.endswith("+SCP"):
            parts = code.split("+")
            place = parts[0]
            scp_count = parts.count("SCP")
            return (
                SCP(self._current_race_context, place)
                .for_infringements(scp_count)
            )

        raise ValueError(f"unknown scoring code {code!r}")

    def score_boats(self):
        """Score the series."""
        for boat in self.boats:
            self._realise_scores(boat)
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

    def _realise_scores(self, boat):
        for race in self.races:
            race['scores'][boat].realise()

    def _exclude_worst_scores(self, boat):
        """Apply the RRS Appendix A exclusion rule.

        Appendix A states that the worst result is excluded
        unless the SIs make some other provision.
        """
        scores = [
            race['scores'][boat]
            for race in self.races
            # Only consider excludable scores.
            if race['scores'][boat].excludable
        ]

        # The max() function returns the earliest of any equal maxima.
        # This is consistent with the RRS, which says the earliest of
        # equal worst scores shall be discarded.
        worst_score = max(scores, key=lambda s: s['score'])
        worst_score.exclude()

    def _calculate_series_scores(self, boat):
        # Pass through _pt() because
        # if there are no included results
        # (which can happen after the first race of a series)
        # then sum() returns an int instead of a Decimal.
        self.boats[boat]['score'] = _pt(sum(
            race['scores'][boat]['score']
            for race in self.races
            if race['scores'][boat]['include']
        ))


class ScoringContext(abc.ABC):
    """Abstract base class. Provides the context for a score.

    For example, a DNF may depend on
    the number of boats entered in the series,
    or the number of boats entered in the race,
    depending on the scoring system being used.
    """

    @property
    @abc.abstractmethod
    def entry_count(self):
        raise NotImplementedError


class SeriesContext(ScoringContext):
    def __init__(self, boats):
        self._boats = boats

    @property
    def entry_count(self):
        # TODO: number of boats that have entered one or more races?
        return len(self._boats)


class RaceContext(ScoringContext):
    def __init__(self, scores):
        # N.B. we do not 'own' this dict,
        # we expect it to change over the context's lifetime.
        self._scores = scores

    @property
    def entry_count(self):
        return len([
            None
            for score in self._scores.values()
            if score["code"] != "DNC"
        ])


@functools.total_ordering
class Score(abc.ABC):
    code = ""
    excludable = True

    def __init__(self, context, value=None):
        self._context = context
        self._value = value
        self._include = True

    # TODO: should be temporary
    def __getitem__(self, item):
        if item == "code":
            return self.code

        if item == "score":
            return self._value

        if item == "include":
            return self._include

        raise KeyError

    def get(self, item, default=None):
        try:
            return self[item]
        except KeyError:
            return default

    # TODO: should non-excludable scores even have an exclude() method?
    def exclude(self):
        if not self.excludable:
            raise Exception(f"{self.code} score is not excludable")

        self._include = False


    @abc.abstractmethod
    def realise(self):
        """Calculate the points value.

        Subclasses overriding this method should set self._value.
        """
        raise NotImplementedError

    def __eq__(self, other):
        return self._value == other._value

    def __lt__(self, other):
        return self._value == other._value

    def __repr__(self):
        _repr = f"{self.code}({self._value})"
        if self._include:
            return _repr

        return f"({_repr})"


class Finish(Score):
    code = ""

    def __init__(self, place):
        # A Finish does not need a context
        # because it does not depend on any properties
        # of the series or the race.
        try:
            value = _pt(place)
        except decimal.InvalidOperation:
            raise ValueError("invalid finish score {place!r}")

        super().__init__(None, value)

    def realise(self):
        # Do nothing because the value was set directly.
        pass

    def __repr__(self):
        return str(self._value)

class NonFinish(Score):
    def realise(self):
        entries = self._context.entry_count
        self._value = _pt(entries + 1)

class DNC(NonFinish):
    """Did Not Come to the starting area."""
    code = "DNC"


class DNF(NonFinish):
    """Did Not Finish"""
    code = "DNF"


class DNE(NonFinish):
    """Disqualification Not Excludable"""
    code = "DNE"
    excludable = False


class SCP(Finish):
    """Scoring Penalty imposed."""
    code = "SCP"

    def __init__(self, context, place):
        super().__init__(place)

        # A Finish does not have a context,
        # but an SCP needs a context to know how many points
        # the penalty is worth.
        self._context = context
        self._no_penalty_value = self._value
        self._infringements = 0

    def for_infringements(self, n):
        self._infringements = n
        return self

    def realise(self):
        # TODO: use penalty value from scoring system info.
        dnf = self._dnf_score()
        penalty = dnf * decimal.Decimal("0.2")
        total_penalty = _pt(self._infringements * penalty)

        self._value = min(
            self._no_penalty_value + total_penalty,
            dnf
        )

    def _dnf_score(self):
        dnf = DNF(self._context)
        dnf.realise()
        return dnf['score']


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
