from abc import ABC, abstractmethod


class Operation(ABC):
    @abstractmethod
    def apply(self, a, b): ...


class Addition(Operation):
    def apply(self, a, b):
        return a + b


class OperationFactory:
    _registry = {"add": Addition}

    @classmethod
    def create(cls, name):
        return cls._registry[name]()


def add(a, b):
    return OperationFactory.create("add").apply(a, b)
