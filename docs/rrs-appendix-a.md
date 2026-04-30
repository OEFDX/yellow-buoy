# Implementation of RRS Appendix A

<!--
>>> import rrs

-->

The RRS Appendix A scoring system has three distinctive features:

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
Decimal('1.0')
>>> race_1_boat_A['include']
False
>>> results['boats']['A']['score']
Decimal('0.0')

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
Any result that is not a simple ‘finish’ is recorded using a code.

### Did Not Come to the starting area (DNC)

_DNC_ is the default score for any boat that is not recorded in a race,
but is recorded in one or more other races in the series.
Although a boat _may_ explicitly be scored DNC,
it is not necessary;
it can simply be omitted from the input.
The score for _DNC_ is the number of boats in the series, plus 1.

```python
>>> series = {
...     'races': [
...         {'scores': {'A': 1, 'B': 2}},
...         {'scores': {'A': 1}},
...     ]
... }
>>> results = rrs.score(series)
>>> results['races'][1]['scores']['B']
<DNC:3.0>

```

### Did Not Finish (DNF) etc.

Most scoring codes are worth equal points to a _DNC_.
This is the case for _DNF_ as shown below.
Here, in a series with 3 boats, B’s _DNF_ is worth 4 points,
the same as C’s implicit _DNC_.

```python
>>> series = {'races': [
...     {'scores': {'A': 1, 'B': 2, 'C': 3}},
...     {'scores': {'A': 1, 'B': 'DNF'}},
... ]}
>>> results = rrs.score(series)
>>> results['races'][1]['scores']['B']
<DNF:4.0>
>>> results['races'][1]['scores']['C']
<DNC:4.0>

```

### Disqualification Not Excludable (DNE)

The _DNE_ scoring code stands for _Disqualification Not Excludable_
and is only used in very limited circumstances.
It is worth the same number of points as any other disqualification
(_DSQ, OCS_ etc),
but as the name implies, a _DNE_ score is never excluded from a boat’s
series score.

```python
>>> series = {
...     'races': [
...         {'scores': {'A': 'DNE'}},
...         {'scores': {'A': 1}},
...     ]
... }
>>> results = rrs.score(series)

```

In the example above, boat _A_ received a _DNE_ in the first race
and a _1_ in the second.
The _DNE_ cannot be excluded,
so the _1_ is excluded instead
and the series score is 2 points for the _DNE_
(because there is only one boat).

```python
>>> results['races'][0]['scores']['A']['include']
True
>>> results['races'][1]['scores']['A']['include']
False
>>> results['boats']['A']['score']
Decimal('2.0')

```

### Scoring Penalty (SCP)

The _SCP_ scoring code stands for _Scoring Penalty imposed_
and is only used if the Notice of Race or the Sailing Instructions
state that it is available.
The default penalty is for 20% of the score for _DNF_ to be added
to the boat's score (to the nearest 0.1 points),
except that the final score shall not be greater than _DNF_.

For example, in a series with 5 boats,
the DNF score is `6`,
so the scoring penalty is `6 × 20% = 1.2` additional points.
If a boat takes a scoring penalty but finishes first,
its score is `2.2` points.

```python
>>> series = {
...     'races': [{'scores': {
...         'A': '1+SCP',
...         'B': 2,
...         'C': 3,
...         'D': 4,
...         'E': 5,
...     }}]
... }
>>> results = rrs.score(series)
>>> results['races'][0]['scores']['A']['score']
Decimal('2.2')

```

However, if a boat takes a scoring penalty and finishes fifth,
the score with a penalty would be `6.2`.
This is greater than the score for _DNF_ so the final score
is capped at `6` points:

```python
>>> series['races'][0]['scores']['E'] = '5+SCP'
>>> results = rrs.score(series)
>>> results['races'][0]['scores']['E']['score']
Decimal('6.0')

```

The rules do not specify explicitly
what happens when a boat takes scoring penalties
in separate incidents.
This library assumes that multiple penalties can be applied,
always subject to the maximum of _DNF_:

```python
>>> series['races'][0]['scores']['A'] = '1+SCP+SCP'
>>> results = rrs.score(series)
>>> results['races'][0]['scores']['A']['score']
Decimal('3.4')

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
Decimal('2.0')
>>> result['boats']['B']['score']
Decimal('4.0')
>>> result['boats']['C']['score']
Decimal('4.0')

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
Decimal('3.0')
>>> result['boats']['B']['score']
Decimal('3.0')

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

