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

## Series score tie-breaking (RRS A8)

There are two stages to tie-breaking in the RRS Appendix A scoring system.
Both of these tie-breaking procedures are used automatically if necessary.



### Tie-breaking by best scores (RRS A8.1)

Order the tied boats’ scores best to worst
and break the tie at the first point where there is a difference.
Excluded scores are not used.

Take the following example:

```python
>>> series = {
...     'races': [
...         {'scores': {'A': 1, 'B': 2, 'C': 'DNC'}},
...         {'scores': {'A': 1, 'B': 2, 'C': 3}},
...         {'scores': {'A': 3, 'B': 'DNF', 'C': 1}},
...     ]
... }

```

- *A* discards a 3, leaving two 1’s for a total of 2.
- *B* discards a *DNF (4)* leaving two 2’s for a total of 4.
- *C* discards a *DNC (4)* leaving a 3 and a 1 for a total of 4.

```python
>>> result = rrs.score(series)
>>> result['boats']['A']['score']
2
>>> result['boats']['B']['score']
4
>>> result['boats']['C']['score']
4

```

This leaves *B* and *C* tied on points.
The scores in order of best to worst are:

- *B*: 2, 2
- *C*: 1, 3

*C’s* best score (1) is better than *B’s* best score (2)
so the tie is broken in favour of *C*
and the final ranking is *A, C, B*.


```python
>>> sorted(
...     (result['boats'][boat]['rank'], boat)
...     for boat in result['boats']
... )
[(1, 'A'), (2, 'C'), (3, 'B')]

```

### Tie breaking by count-back (RRS A8.2)

If, after applying RRS A8.1, the boats are still tied,
order their scores from most recent to least recent
and break the tie at the first point where there is a difference.
Excluded scores *are* used at this stage.

Take the following example:

```python
>>> series = {
...     'races': [
...         {'scores': {'A': 1, 'B': 2}},
...         {'scores': {'A': 2, 'B': 1}},
...         # And a race they both discard, so they scores above all count.
...         {'scores': {'A': 'DNF', 'B': 'DNF'}},
...     ]
... }

```

Both boats score 3 points after discarding their *DNFs*.
Furthermore, they each have one 1 and one 2,
so their best scores are equal
and their next-best scores are equal,
which means that RRS 8.1 does not break the tie.

```python
>>> result = rrs.score(series)
>>> result['boats']['A']['score']
3
>>> result['boats']['B']['score']
3

```

It falls to the ‘count-back’ rule to break the tie.

1.  In the last race, both boats scored *DNF (3)*.
2.  In the second-last race, *B* scored 1, while *A* scored 2.
    Therefore *B* wins.

```python
>>> sorted(
...     (result['boats'][boat]['rank'], boat)
...     for boat in result['boats']
... )
[(1, 'B'), (2, 'A')]

```
