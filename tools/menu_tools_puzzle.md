# Menu Outils (ui/app/menu/)

Dans **AppActions**, ajouter une action (même style que boîte / nesting) :

```python
self.action_puzzle = QAction(tr("menu.tools.puzzle"), parent)
self.action_puzzle.triggered.connect(lambda: window.open_puzzle_generator())
# ou signal puzzle_requested si découplé
```

Dans le **menu Outils** :

```python
menu.addAction(actions.action_puzzle)
```
