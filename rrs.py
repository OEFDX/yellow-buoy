"""
Library for scoring sailing events.
"""

import abc
import decimal
import functools
import re
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
    result = Series(ScoringSystem(None))

    result.add_races(series['races'])
    result.score_and_rank()

    return {'races': result.races, 'boats': result.boats}


class Series:
    def __init__(self, scoring_system):
        self._scoring_system = scoring_system

        self.boats = {}
        self._scoring_system.set_series_context(SeriesContext(self.boats))

        self.races = []
        self._current_race_context = None

    @property
    def current_race_context(self):
        return self._current_race_context

    def add_races(self, races):
        """Add races and give unseen boats DNC scores in other races."""
        self._add_unseen_boats(races)

        for race in races:
            race_result = {'scores': {}}
            self.races.append(race_result)
            self._scoring_system.set_race_context(
                RaceContext(race_result['scores'])
            )

            for boat in self.boats:
                race_result['scores'][boat] = self.parse_score(
                    race['scores'].get(boat, 'DNC')
                )

    def _add_unseen_boats(self, races):
        for race in races:
            for boat in race['scores']:
                self.boats.setdefault(boat, {})

    def parse_score(self, text):
        """Parse a score from a string."""
        place_or_code, *penalties = str(text).split("+")

        if re.match(r"\d(\.\d+)?", place_or_code):
            if penalties:
                # TODO: this does not permit mixing codes,
                #       so won't work for a boat that receives
                #       SCP and ZFP in the same race (x+SCP+ZFP)
                return (
                    self._scoring_system
                    .get_score_for_code(penalties[0])
                    .for_place(place_or_code)
                    .for_infringements(len(penalties))
                )

            return (
                self._scoring_system
                .get_score_for_code("")
                .for_place(place_or_code)
            )

        return self._scoring_system.get_score_for_code(place_or_code)

    def score_and_rank(self):
        """Score the series."""
        self._scoring_system.score_series(self)


class ScoringSystem:
    def __init__(self, properties):
        self._properties = properties
        self._series = None

        self._series_context = None
        self._race_context = None

    def set_series_context(self, ctx):
        self._series_context = ctx

    def set_race_context(self, ctx):
        self._race_context = ctx

    def get_score_for_code(self, code):
        if code == "":
            return Finish()

        if code == "DNC":
            return DNC(self._series_context)

        context = self._race_context

        if code == "DNE":
            return DNE(context)

        if code == "DNF":
            return DNF(context)

        if code == "SCP":
            return SCP(context)

        raise ValueError(f"unknown scoring code {code!r}")

    def score_series(self, series):
        """Calculate scores and ranking for the series."""
        self._series = series
        self._score_boats()
        self._rank_boats()

    def _score_boats(self):
        for boat in self._series.boats:
            self._realise_scores(boat)
            self._exclude_worst_scores(boat)
            self._calculate_series_scores(boat)

    def _realise_scores(self, boat):
        """Calculate the points value of each score."""
        for race in self._series.races:
            race['scores'][boat].realise()

    def _exclude_worst_scores(self, boat):
        """Apply the RRS Appendix A exclusion rule.

        Appendix A states that the worst result is excluded
        unless the SIs make some other provision.
        """
        scores = [
            race['scores'][boat]
            for race in self._series.races
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
        self._series.boats[boat]['score'] = _pt(sum(
            race['scores'][boat]['score']
            for race in self._series.races
            if race['scores'][boat]['include']
        ))

    def _rank_boats(self):
        """Rank the boats, breaking any ties in scores according to RRS A8."""
        ranked_boats = sorted(
            self._series.boats,
            key=self._ranking_key
        )

        for rank, boat in enumerate(ranked_boats, start=1):
            self._series.boats[boat]['rank'] = rank

    def _ranking_key(self, boat):
        # TODO: make this ranking lazy
        #       so the best result key
        #       and the count-back key
        #       are only computed if there is a tie.
        score_key = self._series.boats[boat]['score']

        # This implements RRS A8.1
        # (tie breaking by best results)
        best_result_key = sorted(
            race['scores'][boat]['score']
            for race in self._series.races
            if race['scores'][boat]['include']
        )

        # This implements RRS A8.2
        # (tie breaking by count-back)
        countback_key = [
            race['scores'][boat]['score']
            for race in self._series.races[::-1]
            # N.B. the rules say excluded scores are _included_ here.
        ]

        return (score_key, best_result_key, countback_key)


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

    def __init__(self):
        # A Finish does not need a context
        # because it does not depend on any properties
        # of the series or the race.
        super().__init__(None)

    def for_place(self, place):
        try:
            self._value = _pt(place)
        except decimal.InvalidOperation:
            raise ValueError("invalid finish score {place!r}")

        return self

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

    def __init__(self, context):
        super().__init__()

        # A Finish does not have a context,
        # but an SCP needs a context to know how many points
        # the penalty is worth.
        self._context = context
        self._infringements = 0

    def for_place(self, place):
        super().for_place(place)
        self._no_penalty_value = self._value
        return self

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
