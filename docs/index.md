# RRS Sailing Scoring Library

RRS is a library for scoring sailing events.

## Installation

Copy `rrs.py` into the right place
and use a relative import :(.

```python
>>> import rrs

```

## Basic usage
In a sailing event,
_boats_ compete in _races_:

```python
>>> race_1 = {
...     'scores': {
...         'Boat A': 1,
...         'Boat B': 2,
...     }
... }

```

The races typically form a _series_.

```python
>>> series = {
...     'races': [race_1],
... }

```

A series is scored (boats awarded points)
and ranked (boats ordered best to worst according to their scores)
using the `score()` function:

```python
>>> results = rrs.score(series)

```

The results are a moderately complicated `dict`
containing scoring and ranking information for both
for the boats and the races.

```python
>>> results

```

The sailing instructions may change how scoring is done,
so the scoring system is a property of the series.
The default scoring system is [RRS Appendix A](rrs-appendix-a.md).
