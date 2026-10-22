class Account:
    def __init__(self, balance):
        self._balance = balance
        self._history = []

    def withdraw(self, amount):
        self._balance -= amount
        self._history.append(-amount)

    @property
    def balance(self):
        return self._balance
