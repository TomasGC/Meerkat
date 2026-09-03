# KNOWN VIOLATIONS: CompositionOverInheritance (depth >= 4)


class Animal:
    pass


class Mammal(Animal):
    pass


class Dog(Mammal):
    pass


class Labrador(Dog):
    pass


class GoldenRetriever(Labrador):
    # depth=4 (> 3 threshold) → violation
    pass
