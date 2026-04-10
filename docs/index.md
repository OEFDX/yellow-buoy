# RRS Sailing Scoring Library

RRS is a library for scoring sailing events.

## Installation

Copy `rrs.py` into the right place
and use a relative import :(.

```python
>>> import rrs

```

In a sailing event,
the competition consists Boats sailing a Series of Races.
The sailing instructions may change how scoring is done,
so the scoring system is a property of the series.
The default scoring system is RRS Appendix A ('RRS-A')

```python
>>> series = {
...     'races': [],
...     'options': {
...         'scoring-system': 'RRS-A'    # This is the default.
...     }
... }

```

The scoring system has three distinctive features:

-   the lowest score wins

-   scoring codes (other racing sports have these
    but sailing has special ones of its own)

-   discards (also not unique to sailing, but uncommon)


## Discards (RRS A2.1)

Discards mean that in a series with one race and one boat 'A':

```python
>>> series = {
...     'races': [
...         {'scores': {'A': 1}}
...     ]
... }

```

When the scores are calculated, the worst score is excluded
*even if there was only one race*.

```python
>>> results = rrs.score(series)
>>> race_1_boat_A = results['races'][0]['scores']['A']
>>> race_1_boat_A['score']
1
>>> race_1_boat_A['include']
False
>>> results['boats']['A']['score']
0

```

If a boat has two identical worst scores, the first one is excluded.

```python
>>> results = rrs.score({
...     'races': [
...         {'scores': {'A': 1}},
...         {'scores': {'A': 1}},
...     ]
... })
>>> [r['scores']['A']['include'] for r in results['races']]
[False, True]

```

## Low-points system (RRS A2.1, A4)

In a more realistic series, with two boats,
when the scores are calculated,
the boat with the lowest score also has the best (lowest) rank.

```python
>>> series = {'races': [{'scores': {'A': 1, 'B': 2}}]}
>>> results = rrs.score(series)
>>> {results['boats'][boat]['rank']: boat for boat in results['boats']}
{1: 'A', 2: 'B'}

```

## Scoring codes (RRS A10)
Scoring codes are commonly used for a variety of reasons.
Most scoring codes produce the same number of points:
the number of boats in the series, plus one.
This is the case for the most obvious code: ‘DNF’ (Did Not Finish).

```python
>>> series = {'races': [{'scores': {'A': 1, 'B': 'DNF'}}]}
>>> results = rrs.score(series)
>>> results['races'][0]['scores']['B']['code']
'DNF'
>>> results['races'][0]['scores']['B']['score']
3

```
