from __future__ import annotations

from typing import Any, ClassVar, Literal, Mapping, TypedDict, overload

import pytest

from pymidantic import Migratable, migrate


class Car(Migratable):
    """
    ChangeLog:
        - 3.0.0
            Add colour
        - 2.0.0
            Add engine type
    """

    _version: ClassVar[str] = "3.0.0"

    name: str
    engine_type: str
    colour: str = "blue"


@migrate(Car, "3.0.0", "2.0.0")
def remove_colour(attrs: dict[str, Any], additional_data: dict[str, Any]) -> None:
    attrs.pop("colour", None)


@migrate(Car, "2.0.0", "1.0.0")
def remove_engine_type(attrs: dict[str, Any], additional_data: dict[str, Any]) -> None:
    attrs.pop("engine_type", None)


def test_simple_car_migrate():
    car = Car(name="Model 3", engine_type="electric")

    output = car.dump_version("1.0.0")
    assert output == {"name": "Model 3"}


def test_no_path_migrate():
    car = Car(name="Model 3", engine_type="electric")

    with pytest.raises(ValueError, match="no path"):
        car.dump_version("0.0.0")


class Cat(Migratable):
    """An example cat that we've updated

    ChangeLog:
        - 7.0.0
            Add eyes to Animals

        - 6.0.0
            Add legs

        - 5.0.1:
            Fix typo. `nane` -> `name`

        - 5.0.0:
            Allow names for cats

        - 4.0.0:
            Removed weight after some cats complained about this info being shared

        - 3.1.0:
            Switched to using ints for heights and weights, no one needs precision on these fields

        - 3.0.0:
            Added height and weight info to cats

        - 2.0.0:
            Customers wanted the ability for the cat to make multilingual sounds, so we renamed `sound` -> `sounds`
            and made it a `list[str]`
    """

    _version: ClassVar[str] = "7.0.0"

    name: str
    eyes: int = 2
    legs: int = 4

    sounds: list[str] = ["meow", "miau"]
    height: int

    @overload
    def dump_version(
        self,
        version: Literal["7.0.0", "6.0.0", "5.0.0", "5.0.1", "4.0.0"],
        additional_data: None = ...,
        **kwargs,
    ) -> dict[str, Any]: ...

    class CatWeight(TypedDict):
        weight: int

    @overload
    def dump_version(
        self, version: Literal["3.1.0", "3.0.0"], additional_data: CatWeight, **kwargs
    ) -> dict[str, Any]: ...

    @overload
    def dump_version(
        self,
        version: Literal["1.0.0", "2.0.0", "3.0.0"],
        additional_data: None = ...,
        **kwargs,
    ) -> dict[str, Any]: ...

    def dump_version(
        self,
        version: str,
        additional_data: Mapping[str, Any] | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        return super().dump_version(version, additional_data, **kwargs)


@migrate(Cat, "7.0.0", "6.0.0")
def remove_eyes(attrs: dict, additional_data: dict) -> None:
    attrs.pop("eyes", None)


@migrate(Cat, "6.0.0", "5.0.1")
def remove_legs(attrs: dict, additional_data: dict) -> None:
    attrs.pop("legs", None)


@migrate(Cat, "5.0.1", "5.0.0")
def unfix_name_spelling(attrs: dict, additional_data: dict) -> None:
    attrs["nane"] = attrs["name"]
    attrs.pop("name", None)


@migrate(Cat, "5.0.0", "4.0.0")
def remove_name_and_weight_and_height(attrs: dict, additional_data: dict) -> None:
    attrs.pop("nane", None)


@migrate(Cat, "4.0.0", "3.1.0")
def add_weight(attrs: dict[str, Any], additional_data: dict) -> None:
    attrs["weight"] = int(additional_data["weight"])


@migrate(Cat, "3.1.0", "3.0.0")
def change_height_weight_type(attrs: dict[str, Any], additional_data: dict[str, Any]) -> None:
    attrs["height"] = float(attrs["height"])
    attrs["weight"] = float(attrs["weight"])


# Defining these extra edges allows us to output older versions without providing additional data.
@migrate(Cat, "4.0.0", "2.0.0")
@migrate(Cat, "3.1.0", "2.0.0")
@migrate(Cat, "3.0.0", "2.0.0")
def remove_height_and_weight(attrs: dict, additional_data: dict) -> None:
    attrs.pop("height", None)
    attrs.pop("weight", None)


@migrate(Cat, "2.0.0", "1.0.0")
def remove_multilingual_sounds(attrs: dict, additional_data: dict) -> None:
    attrs.pop("sounds", None)
    attrs["sound"] = "meow"


@migrate(Cat, "4.0.0", "6.0.0")
def assert_bad_migration_never_called(attrs: dict, additional_data: dict) -> None:
    assert False


def test_previous_cat_outputs():
    # Create Cat at latest
    cat = Cat(height=3, name="furballs")

    # Customer needs an older version. As long as there is a path from the current
    # version to the desired version, _and_ any additional data that the older version
    # needs is still available this is possible.
    assert {"sound": "meow"} == cat.dump_version("1.0.0")

    assert {"sounds": ["meow", "miau"]} == cat.dump_version("2.0.0")

    assert {
        "height": 3.0,
        "sounds": ["meow", "miau"],
        "weight": 5.00,
    } == cat.dump_version("3.0.0", {"weight": 5})

    assert {
        "height": 3,
        "sounds": ["meow", "miau"],
        "weight": 5,
    } == cat.dump_version("3.1.0", {"weight": 5})

    # cat.dump_version("3.1.0")

    assert {
        "height": 3,
        "sounds": ["meow", "miau"],
    } == cat.dump_version("4.0.0")

    assert {
        "height": 3,
        "sounds": ["meow", "miau"],
        "nane": "furballs",
    } == cat.dump_version("5.0.0")

    assert {
        "height": 3,
        "sounds": ["meow", "miau"],
        "name": "furballs",
    } == cat.dump_version("5.0.1")

    assert {
        "height": 3,
        "sounds": ["meow", "miau"],
        "name": "furballs",
        "legs": 4,
    } == cat.dump_version("6.0.0")

    assert {
        "height": 3,
        "sounds": ["meow", "miau"],
        "name": "furballs",
        "legs": 4,
        "eyes": 2,
    } == cat.dump_version("7.0.0")
