class Account:
    def __init__(self, balance):
        self.balance = balance
        self.history = []

    def withdraw_and_get_balance(self, amount):
        self.balance -= amount
        self.history.append(-amount)
        return self.balance
