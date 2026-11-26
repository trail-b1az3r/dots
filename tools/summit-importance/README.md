# Summit's notification importance model

Which notifications are worth the banner under Summit's clock, decided on the computer: a logistic regression over
hashed words and word pairs of a notification's app, title and body, plus its urgency, whether it has buttons, a code
and a time "in N minutes". The features are `dots/.config/quickshell/Summit/services/importance.js`, which Summit runs
and which training runs too (in node), so the two always agree.

```sh
python3 make_data.py > data.jsonl   # the 2,000 training examples, from templates (seeded: always the same file)
python3 train.py                    # fit, report, write Summit/assets/model/importance.json
python3 train.py --check            # what the tests run: does the shipped model match the training?
```

Needs numpy and node. `holdout.jsonl` is 32 notifications written by hand that are never trained on; `train.py`
reports how many it gets right (and the tests ask for at least 90%). Add examples to `make_data.py`'s templates
rather than to the holdout, so it stays a fair test.
