# RRS Appendix A: optional features

<!--
>>> import rrs

-->

Optional features are used by
setting items in the `'scoring-system'` dict
within a series dict:

```python
{
    'scoring-system': {
        'feature': 'value',
    },
    'races': [...],
}
```

## Long series (RRS A5.3)

!!! note "Usage"
    ```python
    'rrs-a5.3': True
    ```

Sometimes a series might run over multiple separate sessions
(e.g. every Sunday afternoon in Summer).
In a series like this it makes sense to penalise a boat that doesn't
turn up at all (DNC)
more than one that turns up but fails to finish a race (DNF).
RRS A5.3 is an optional rule
(it must be explicitly invoked in the sailing instructions)
that permits this:

-   The score for *DNC* is
    the number of boats in the series plus 1
    (as usual).

-   The score for *DNF* (and *DNS, OCS* etc.) is
    the number of boats in the _race_ plus 1.

In the series below, _B_ did not finish the second race,
and  _C_ did not come to the starting area.

```python

>>> series = {
...     'scoring-system': {
...         'rrs-a5.3': True,
...     },
...     'races': [
...         {'scores': {'A': 1, 'B': 2, 'C': 3}},
...         {'scores': {'A': 1, 'B': 'DNF'}},
...     ]
... }

```

Therefore,
_B_ scores _DNF (3)_
and _C_ scores _DNC (4)_ in the second race.

```python
>>> results = rrs.score(series)
>>> scores = results['races'][1]['scores']
>>> scores['B']
<DNF:3.0>
>>> scores['C']
<DNC:4.0>

```

